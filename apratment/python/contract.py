from datetime import date
from flask import Blueprint, jsonify, redirect, render_template, request, session
from common import ApiError, clean_text, get_json_data, owner_api_required, parse_int, parse_money

contract_bp = Blueprint("contract", __name__)
CONTRACT_STATUS = {"ACTIVE", "ENDED", "CANCELLED"}

@contract_bp.route("/contracts.html")
def contracts_page():
    if "user_id" not in session:
        return redirect("/")
    if session.get("role") not in ("admin", "owner"):
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    return render_template("contracts.html")

def parse_date(value, label, required=True):
    value = str(value or "").strip()
    if not value and not required:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ApiError(f"{label}ไม่ถูกต้อง")

def validate_contract_data(data):
    start_date = parse_date(data.get("start_date"), "วันที่เริ่มสัญญา")
    end_date = parse_date(data.get("end_date"), "วันที่สิ้นสุดสัญญา", False)

    if end_date and end_date < start_date:
        raise ApiError("วันที่สิ้นสุดสัญญาต้องไม่ก่อนวันที่เริ่มสัญญา")

    status = clean_text(data, "contract_status", "สถานะสัญญา", 20).upper()
    if status not in CONTRACT_STATUS:
        raise ApiError("สถานะสัญญาไม่ถูกต้อง")

    return {
        "contract_number": clean_text(data, "contract_number", "เลขที่สัญญา", 30),
        "tenant_id": parse_int(data.get("tenant_id"), "ผู้เช่า", 1),
        "room_id": parse_int(data.get("room_id"), "ห้องพัก", 1),
        "start_date": start_date,
        "end_date": end_date,
        "monthly_rent": parse_money(data, "monthly_rent", "ค่าเช่าต่อเดือน"),
        "deposit_amount": parse_money(data, "deposit_amount", "เงินประกัน"),
        "contract_status": status,
        "note": clean_text(data, "note", "หมายเหตุ", 5000, required=False)
    }

def validate_contract(cursor, payload, current_contract_id=0):
    cursor.execute("SELECT 1 FROM public.tenants WHERE tenant_id = %s LIMIT 1", (payload["tenant_id"],))
    if not cursor.fetchone():
        raise ApiError("ไม่พบผู้เช่าที่เลือก")

    cursor.execute("SELECT status FROM public.room WHERE room_id = %s LIMIT 1", (payload["room_id"],))
    room = cursor.fetchone()
    if not room:
        raise ApiError("ไม่พบห้องพักที่เลือก")

    cursor.execute("""
        SELECT 1 FROM public.rental_contracts
        WHERE lower(btrim(contract_number)) = lower(%s)
          AND contract_id <> %s
        LIMIT 1
    """, (payload["contract_number"], current_contract_id))
    if cursor.fetchone():
        raise ApiError("เลขที่สัญญานี้มีอยู่แล้ว", 409)

    if payload["contract_status"] == "ACTIVE":
        if str(room["status"]).strip().upper() == "MAINTENANCE":
            raise ApiError("ห้องนี้อยู่ระหว่างปิดปรับปรุง")

        cursor.execute("""
            SELECT 1 FROM public.rental_contracts
            WHERE room_id = %s
              AND upper(btrim(contract_status)) = 'ACTIVE'
              AND contract_id <> %s
            LIMIT 1
        """, (payload["room_id"], current_contract_id))
        if cursor.fetchone():
            raise ApiError("ห้องนี้มีสัญญาที่กำลังใช้งานอยู่แล้ว", 409)

def update_room_status(cursor, room_id):
    cursor.execute("""
        SELECT 1 FROM public.rental_contracts
        WHERE room_id = %s
          AND upper(btrim(contract_status)) = 'ACTIVE'
        LIMIT 1
    """, (room_id,))
    occupied = cursor.fetchone() is not None

    cursor.execute("""
        UPDATE public.room
        SET status = %s
        WHERE room_id = %s
          AND upper(btrim(status)) <> 'MAINTENANCE'
    """, ("OCCUPIED" if occupied else "AVAILABLE", room_id))

@contract_bp.get("/api/contracts/options")
@owner_api_required
def contract_options(cursor):
    cursor.execute("""
        SELECT tenant_id, tenant_code, first_name, last_name
        FROM public.tenants
        WHERE is_active = true
        ORDER BY tenant_code
    """)
    tenants = cursor.fetchall()

    cursor.execute("""
        SELECT room_id, room_number, monthly_rent::text AS monthly_rent,
               deposit_amount::text AS deposit_amount, status
        FROM public.room
        ORDER BY floor, room_number
    """)
    rooms = cursor.fetchall()
    return jsonify(tenants=tenants, rooms=rooms)

@contract_bp.route("/api/contracts", methods=["GET", "POST"])
@owner_api_required
def contracts_api(cursor):
    if request.method == "GET":
        search = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip().upper()
        conditions = []
        values = []

        if search:
            conditions.append("""
                (c.contract_number ILIKE %s
                OR r.room_number ILIKE %s
                OR concat_ws(' ', t.first_name, t.last_name) ILIKE %s)
            """)
            values.extend([f"%{search}%"] * 3)

        if status:
            if status not in CONTRACT_STATUS:
                raise ApiError("สถานะสัญญาไม่ถูกต้อง")
            conditions.append("upper(btrim(c.contract_status)) = %s")
            values.append(status)

        where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""

        cursor.execute(f"""
            SELECT c.contract_id, c.contract_number,
                   to_char(c.start_date, 'YYYY-MM-DD') AS start_date,
                   to_char(c.end_date, 'YYYY-MM-DD') AS end_date,
                   c.monthly_rent::text AS monthly_rent,
                   c.contract_status, r.room_number,
                   concat_ws(' ', t.first_name, t.last_name) AS tenant_name
            FROM public.rental_contracts c
            JOIN public.tenants t ON t.tenant_id = c.tenant_id
            JOIN public.room r ON r.room_id = c.room_id
            {where_sql}
            ORDER BY c.contract_id DESC
        """, values)
        return jsonify(items=cursor.fetchall())

    payload = validate_contract_data(get_json_data())
    cursor.execute("LOCK TABLE public.rental_contracts IN EXCLUSIVE MODE")
    validate_contract(cursor, payload)

    cursor.execute("SELECT COALESCE(MAX(contract_id), 0) + 1 AS next_id FROM public.rental_contracts")
    contract_id = cursor.fetchone()["next_id"]

    cursor.execute("""
        INSERT INTO public.rental_contracts
        (contract_id, contract_number, tenant_id, room_id, start_date, end_date,
         monthly_rent, deposit_amount, contract_status, note, created_by, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULLIF(%s, ''), %s, LOCALTIME)
    """, (
        contract_id, payload["contract_number"], payload["tenant_id"], payload["room_id"],
        payload["start_date"], payload["end_date"], payload["monthly_rent"],
        payload["deposit_amount"], payload["contract_status"], payload["note"],
        session["user_id"]
    ))

    update_room_status(cursor, payload["room_id"])
    return jsonify(message="เพิ่มสัญญาเช่าเรียบร้อย", contract_id=contract_id), 201

@contract_bp.route("/api/contracts/<int:contract_id>", methods=["GET", "PUT", "DELETE"])
@owner_api_required
def contract_item(cursor, contract_id):
    cursor.execute("""
        SELECT contract_id, contract_number, tenant_id, room_id,
               to_char(start_date, 'YYYY-MM-DD') AS start_date,
               to_char(end_date, 'YYYY-MM-DD') AS end_date,
               monthly_rent::text AS monthly_rent,
               deposit_amount::text AS deposit_amount,
               contract_status, note
        FROM public.rental_contracts
        WHERE contract_id = %s
        LIMIT 1
    """, (contract_id,))
    old = cursor.fetchone()

    if not old:
        raise ApiError("ไม่พบสัญญาเช่านี้", 404)

    if request.method == "GET":
        return jsonify(item=old)

    old_room_id = old["room_id"]

    if request.method == "DELETE":
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM public.invoices WHERE contract_id = %s
            ) OR EXISTS(
                SELECT 1 FROM public.maintenance_requests WHERE contract_id = %s
            ) AS is_used
        """, (contract_id, contract_id))
        if cursor.fetchone()["is_used"]:
            raise ApiError("ลบสัญญานี้ไม่ได้ เพราะมีบิลหรือประวัติแจ้งซ่อม", 409)

        cursor.execute("DELETE FROM public.rental_contracts WHERE contract_id = %s", (contract_id,))
        update_room_status(cursor, old_room_id)
        return jsonify(message="ลบสัญญาเช่าเรียบร้อย")

    payload = validate_contract_data(get_json_data())
    cursor.execute("LOCK TABLE public.rental_contracts IN EXCLUSIVE MODE")
    validate_contract(cursor, payload, contract_id)

    cursor.execute("""
        UPDATE public.rental_contracts
        SET contract_number = %s, tenant_id = %s, room_id = %s,
            start_date = %s, end_date = %s, monthly_rent = %s,
            deposit_amount = %s, contract_status = %s,
            note = NULLIF(%s, '')
        WHERE contract_id = %s
    """, (
        payload["contract_number"], payload["tenant_id"], payload["room_id"],
        payload["start_date"], payload["end_date"], payload["monthly_rent"],
        payload["deposit_amount"], payload["contract_status"], payload["note"],
        contract_id
    ))

    update_room_status(cursor, old_room_id)
    if payload["room_id"] != old_room_id:
        update_room_status(cursor, payload["room_id"])

    return jsonify(message="แก้ไขสัญญาเช่าเรียบร้อย")