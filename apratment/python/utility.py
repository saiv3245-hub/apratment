from datetime import date
from decimal import Decimal
from flask import Blueprint, jsonify, redirect, render_template, request, session
from common import ApiError, clean_text, get_json_data, owner_api_required, parse_int, parse_money

utility_bp = Blueprint("utility", __name__)

@utility_bp.route("/utilities.html")
def utilities_page():
    if "user_id" not in session:
        return redirect("/")
    if session.get("role") not in ("admin", "owner"):
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    return render_template("utilities.html")

def parse_date(value, label):
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError:
        raise ApiError(f"{label}ไม่ถูกต้อง")

def validate_invoice(data):
    billing_month = parse_date(data.get("billing_month"), "เดือนที่เรียกเก็บ").replace(day=1)
    due_date = parse_date(data.get("due_date"), "วันครบกำหนด")

    result = {
        "invoice_number": clean_text(data, "invoice_number", "เลขที่บิล", 30),
        "contract_id": parse_int(data.get("contract_id"), "สัญญาเช่า", 1),
        "billing_month": billing_month,
        "due_date": due_date,
        "rent_amount": parse_money(data, "rent_amount", "ค่าเช่า"),
        "water_previous": parse_money(data, "water_previous", "มิเตอร์น้ำครั้งก่อน"),
        "water_current": parse_money(data, "water_current", "มิเตอร์น้ำปัจจุบัน"),
        "water_rate": parse_money(data, "water_rate", "ค่าน้ำต่อหน่วย"),
        "electric_previous": parse_money(data, "electric_previous", "มิเตอร์ไฟครั้งก่อน"),
        "electric_current": parse_money(data, "electric_current", "มิเตอร์ไฟปัจจุบัน"),
        "electric_rate": parse_money(data, "electric_rate", "ค่าไฟต่อหน่วย"),
        "other_amount": parse_money(data, "other_amount", "ค่าใช้จ่ายอื่น"),
        "note": clean_text(data, "note", "หมายเหตุ", 5000, required=False)
    }

    if result["water_current"] < result["water_previous"]:
        raise ApiError("มิเตอร์น้ำปัจจุบันต้องไม่น้อยกว่ามิเตอร์ครั้งก่อน")
    if result["electric_current"] < result["electric_previous"]:
        raise ApiError("มิเตอร์ไฟปัจจุบันต้องไม่น้อยกว่ามิเตอร์ครั้งก่อน")

    result["water_units"] = result["water_current"] - result["water_previous"]
    result["water_amount"] = result["water_units"] * result["water_rate"]
    result["electric_units"] = result["electric_current"] - result["electric_previous"]
    result["electric_amount"] = result["electric_units"] * result["electric_rate"]
    result["total_amount"] = (
        result["rent_amount"]
        + result["water_amount"]
        + result["electric_amount"]
        + result["other_amount"]
    )
    return result

def validate_invoice_duplicate(cursor, data, current_invoice_id=0):
    cursor.execute("""
        SELECT 1 FROM public.invoices
        WHERE lower(btrim(invoice_number)) = lower(%s)
          AND invoice_id <> %s
        LIMIT 1
    """, (data["invoice_number"], current_invoice_id))
    if cursor.fetchone():
        raise ApiError("เลขที่บิลนี้มีอยู่แล้ว", 409)

    cursor.execute("""
        SELECT 1 FROM public.invoices
        WHERE contract_id = %s
          AND billing_month = %s
          AND invoice_id <> %s
        LIMIT 1
    """, (data["contract_id"], data["billing_month"], current_invoice_id))
    if cursor.fetchone():
        raise ApiError("สัญญานี้มีบิลของเดือนที่เลือกแล้ว", 409)

@utility_bp.get("/api/utilities/contracts")
@owner_api_required
def utility_contracts(cursor):
    cursor.execute("""
        SELECT c.contract_id, c.contract_number,
               c.monthly_rent::text AS monthly_rent,
               c.contract_status, r.room_number,
               concat_ws(' ', t.first_name, t.last_name) AS tenant_name
        FROM public.rental_contracts c
        JOIN public.room r ON r.room_id = c.room_id
        JOIN public.tenants t ON t.tenant_id = c.tenant_id
        ORDER BY c.contract_id DESC
    """)
    return jsonify(items=cursor.fetchall())

@utility_bp.route("/api/utilities", methods=["GET", "POST"])
@owner_api_required
def utilities_api(cursor):
    if request.method == "GET":
        search = request.args.get("q", "").strip()
        values = []
        where_sql = ""

        if search:
            where_sql = """
                WHERE i.invoice_number ILIKE %s
                   OR r.room_number ILIKE %s
                   OR concat_ws(' ', t.first_name, t.last_name) ILIKE %s
            """
            values = [f"%{search}%"] * 3

        cursor.execute(f"""
            SELECT i.invoice_id, i.invoice_number,
                   to_char(i.billing_month, 'YYYY-MM-DD') AS billing_month,
                   i.rent_amount::text AS rent_amount,
                   i.water_amount::text AS water_amount,
                   i.electric_amount::text AS electric_amount,
                   i.total_amount::text AS total_amount,
                   i.payment_status, r.room_number,
                   concat_ws(' ', t.first_name, t.last_name) AS tenant_name
            FROM public.invoices i
            JOIN public.rental_contracts c ON c.contract_id = i.contract_id
            JOIN public.room r ON r.room_id = c.room_id
            JOIN public.tenants t ON t.tenant_id = c.tenant_id
            {where_sql}
            ORDER BY i.billing_month DESC, i.invoice_id DESC
        """, values)
        return jsonify(items=cursor.fetchall())

    data = validate_invoice(get_json_data())
    cursor.execute("LOCK TABLE public.invoices IN EXCLUSIVE MODE")
    validate_invoice_duplicate(cursor, data)

    cursor.execute("SELECT COALESCE(MAX(invoice_id), 0) + 1 AS next_id FROM public.invoices")
    invoice_id = cursor.fetchone()["next_id"]

    cursor.execute("""
        INSERT INTO public.invoices
        (invoice_id, invoice_number, contract_id, billing_month,
         rent_amount, water_previous, water_current, water_units,
         water_rate, water_amount, electric_previous, electric_current,
         electric_units, electric_rate, electric_amount, other_amount,
         total_amount, due_date, amount_paid, payment_status, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, 0, 'UNPAID', NULLIF(%s, ''))
    """, (
        invoice_id, data["invoice_number"], data["contract_id"], data["billing_month"],
        data["rent_amount"], data["water_previous"], data["water_current"],
        data["water_units"], data["water_rate"], data["water_amount"],
        data["electric_previous"], data["electric_current"], data["electric_units"],
        data["electric_rate"], data["electric_amount"], data["other_amount"],
        data["total_amount"], data["due_date"], data["note"]
    ))
    return jsonify(message="เพิ่มบิลเรียบร้อย", invoice_id=invoice_id), 201

@utility_bp.route("/api/utilities/<int:invoice_id>", methods=["GET", "PUT", "DELETE"])
@owner_api_required
def utility_item(cursor, invoice_id):
    cursor.execute("""
        SELECT invoice_id, invoice_number, contract_id,
               to_char(billing_month, 'YYYY-MM-DD') AS billing_month,
               rent_amount::text AS rent_amount,
               water_previous::text AS water_previous,
               water_current::text AS water_current,
               water_rate::text AS water_rate,
               electric_previous::text AS electric_previous,
               electric_current::text AS electric_current,
               electric_rate::text AS electric_rate,
               other_amount::text AS other_amount,
               total_amount::text AS total_amount,
               amount_paid::text AS amount_paid,
               to_char(due_date, 'YYYY-MM-DD') AS due_date,
               note
        FROM public.invoices
        WHERE invoice_id = %s
        LIMIT 1
    """, (invoice_id,))
    invoice = cursor.fetchone()

    if not invoice:
        raise ApiError("ไม่พบบิลนี้", 404)

    if request.method == "GET":
        return jsonify(item=invoice)

    if request.method == "DELETE":
        if Decimal(str(invoice["amount_paid"])) > 0:
            raise ApiError("ลบบิลที่มีการชำระเงินแล้วไม่ได้", 409)
        cursor.execute("DELETE FROM public.invoices WHERE invoice_id = %s", (invoice_id,))
        return jsonify(message="ลบบิลเรียบร้อย")

    data = validate_invoice(get_json_data())
    amount_paid = Decimal(str(invoice["amount_paid"]))

    if amount_paid > data["total_amount"]:
        raise ApiError("ยอดรวมใหม่ต่ำกว่ายอดที่ชำระไปแล้ว")

    if amount_paid == data["total_amount"] and amount_paid > 0:
        status = "PAID"
    elif amount_paid > 0:
        status = "PARTIAL"
    else:
        status = "UNPAID"

    validate_invoice_duplicate(cursor, data, invoice_id)

    cursor.execute("""
        UPDATE public.invoices
        SET invoice_number = %s, contract_id = %s, billing_month = %s,
            rent_amount = %s, water_previous = %s, water_current = %s,
            water_units = %s, water_rate = %s, water_amount = %s,
            electric_previous = %s, electric_current = %s,
            electric_units = %s, electric_rate = %s, electric_amount = %s,
            other_amount = %s, total_amount = %s, due_date = %s,
            payment_status = %s, note = NULLIF(%s, '')
        WHERE invoice_id = %s
    """, (
        data["invoice_number"], data["contract_id"], data["billing_month"],
        data["rent_amount"], data["water_previous"], data["water_current"],
        data["water_units"], data["water_rate"], data["water_amount"],
        data["electric_previous"], data["electric_current"],
        data["electric_units"], data["electric_rate"], data["electric_amount"],
        data["other_amount"], data["total_amount"], data["due_date"],
        status, data["note"], invoice_id
    ))
    return jsonify(message="แก้ไขบิลเรียบร้อย")