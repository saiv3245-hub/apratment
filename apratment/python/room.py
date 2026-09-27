from flask import Blueprint, jsonify, redirect, render_template, request, session
from common import ApiError, clean_text, get_json_data, owner_api_required, parse_int, parse_money

room_bp = Blueprint("room", __name__)
ROOM_STATUS = {"AVAILABLE", "OCCUPIED", "MAINTENANCE"}

@room_bp.route("/room.html")
def room_page():
    if "user_id" not in session:
        return redirect("/")
    if session.get("role") not in ("admin", "owner"):
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    return render_template("room.html")

@room_bp.route("/api/rooms", methods=["GET", "POST"])
@owner_api_required
def rooms_api(cursor):
    if request.method == "GET":
        search = request.args.get("q", "").strip()
        floor = request.args.get("floor", "").strip()
        status = request.args.get("status", "").strip()
        conditions = []
        values = []

        if search:
            conditions.append("(room_number ILIKE %s OR room_type ILIKE %s)")
            values.extend([f"%{search}%", f"%{search}%"])

        if floor:
            conditions.append("floor = %s")
            values.append(parse_int(floor, "ชั้น", 1, 999))

        if status:
            if status not in ROOM_STATUS:
                raise ApiError("สถานะห้องไม่ถูกต้อง")
            conditions.append("status = %s")
            values.append(status)

        where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""

        cursor.execute(f"""
            SELECT room_id, room_number, floor, room_type, monthly_rent::text, deposit_amount::text,
                   status, COALESCE(description, '') AS description
            FROM public.room
            {where_sql}
            ORDER BY floor, room_number, room_id
        """, values)

        return jsonify(items=cursor.fetchall())

    data = get_json_data()
    room_number = clean_text(data, "room_number", "หมายเลขห้อง", 20)
    floor = parse_int(data.get("floor"), "ชั้น", 1, 999)
    room_type = clean_text(data, "room_type", "ประเภทห้อง", 50)
    monthly_rent = parse_money(data, "monthly_rent", "ค่าเช่าต่อเดือน")
    deposit_amount = parse_money(data, "deposit_amount", "เงินประกัน")
    status = clean_text(data, "status", "สถานะห้อง", 20)
    description = clean_text(data, "description", "รายละเอียดเพิ่มเติม", 5000, False)

    if status not in ROOM_STATUS:
        raise ApiError("สถานะห้องไม่ถูกต้อง")

    cursor.execute("LOCK TABLE public.room IN EXCLUSIVE MODE")
    cursor.execute("""
        SELECT 1 FROM public.room
        WHERE lower(btrim(room_number)) = lower(%s)
        LIMIT 1
    """, (room_number,))

    if cursor.fetchone():
        raise ApiError("หมายเลขห้องนี้มีอยู่แล้ว", 409)

    cursor.execute("SELECT COALESCE(MAX(room_id), 0) + 1 AS next_id FROM public.room")
    room_id = cursor.fetchone()["next_id"]

    cursor.execute("""
        INSERT INTO public.room
        (room_id, room_number, floor, room_type, monthly_rent, deposit_amount, status, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING room_id
    """, (room_id, room_number, floor, room_type, monthly_rent, deposit_amount, status, description or None))

    return jsonify(message="เพิ่มห้องพักเรียบร้อย", room_id=cursor.fetchone()["room_id"]), 201

@room_bp.route("/api/rooms/<int:room_id>", methods=["PUT", "DELETE"])
@owner_api_required
def room_item_api(cursor, room_id):
    cursor.execute("LOCK TABLE public.room IN SHARE ROW EXCLUSIVE MODE")
    cursor.execute("SELECT room_id FROM public.room WHERE room_id = %s FOR UPDATE", (room_id,))

    if not cursor.fetchone():
        raise ApiError("ไม่พบห้องพักนี้", 404)

    if request.method == "DELETE":
        cursor.execute("""
            SELECT EXISTS(SELECT 1 FROM public.rental_contracts WHERE room_id = %s)
            OR EXISTS(SELECT 1 FROM public.maintenance_requests WHERE room_id = %s) AS is_used
        """, (room_id, room_id))

        if cursor.fetchone()["is_used"]:
            raise ApiError("ลบห้องนี้ไม่ได้ เพราะมีประวัติสัญญาหรือแจ้งซ่อม", 409)

        cursor.execute("DELETE FROM public.room WHERE room_id = %s", (room_id,))
        return jsonify(message="ลบห้องพักเรียบร้อย")

    data = get_json_data()
    room_number = clean_text(data, "room_number", "หมายเลขห้อง", 20)
    floor = parse_int(data.get("floor"), "ชั้น", 1, 999)
    room_type = clean_text(data, "room_type", "ประเภทห้อง", 50)
    monthly_rent = parse_money(data, "monthly_rent", "ค่าเช่าต่อเดือน")
    deposit_amount = parse_money(data, "deposit_amount", "เงินประกัน")
    status = clean_text(data, "status", "สถานะห้อง", 20)
    description = clean_text(data, "description", "รายละเอียดเพิ่มเติม", 5000, False)

    if status not in ROOM_STATUS:
        raise ApiError("สถานะห้องไม่ถูกต้อง")

    cursor.execute("""
        SELECT 1 FROM public.room
        WHERE lower(btrim(room_number)) = lower(%s) AND room_id <> %s
        LIMIT 1
    """, (room_number, room_id))

    if cursor.fetchone():
        raise ApiError("หมายเลขห้องนี้มีอยู่แล้ว", 409)

    if status != "OCCUPIED":
        cursor.execute("""
            SELECT 1 FROM public.rental_contracts
            WHERE room_id = %s AND upper(btrim(contract_status)) = 'ACTIVE'
            LIMIT 1
        """, (room_id,))

        if cursor.fetchone():
            raise ApiError("ห้องนี้มีสัญญาเช่าที่กำลังใช้งานอยู่ จึงเปลี่ยนสถานะไม่ได้", 409)

    cursor.execute("""
        UPDATE public.room
        SET room_number = %s, floor = %s, room_type = %s, monthly_rent = %s,
            deposit_amount = %s, status = %s, description = %s
        WHERE room_id = %s
    """, (room_number, floor, room_type, monthly_rent, deposit_amount, status, description or None, room_id))

    return jsonify(message="แก้ไขข้อมูลห้องพักเรียบร้อย")