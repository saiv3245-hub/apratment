from decimal import Decimal, InvalidOperation
from flask import Blueprint, jsonify, redirect, render_template, request, session
from common import ApiError, clean_text, get_json_data, owner_api_required

payment_bp = Blueprint("payment", __name__)
PAYMENT_STATUS = {"UNPAID", "PARTIAL", "PAID"}

@payment_bp.route("/payments.html")
def payments_page():
    if "user_id" not in session:
        return redirect("/")
    if session.get("role") not in ("admin", "owner"):
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    return render_template("payments.html")

def parse_amount(value):
    try:
        amount = Decimal(str(value or "").strip())
    except InvalidOperation:
        raise ApiError("ยอดที่ชำระต้องเป็นตัวเลข")
    if amount < 0:
        raise ApiError("ยอดที่ชำระต้องไม่น้อยกว่า 0")
    return amount

@payment_bp.get("/api/payments")
@owner_api_required
def payments_api(cursor):
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip().upper()
    conditions = []
    values = []

    if search:
        conditions.append("""
            (i.invoice_number ILIKE %s
            OR r.room_number ILIKE %s
            OR concat_ws(' ', t.first_name, t.last_name) ILIKE %s)
        """)
        values.extend([f"%{search}%"] * 3)

    if status:
        if status not in PAYMENT_STATUS:
            raise ApiError("สถานะการชำระเงินไม่ถูกต้อง")
        conditions.append("upper(btrim(i.payment_status)) = %s")
        values.append(status)

    where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""

    cursor.execute(f"""
        SELECT i.invoice_id, i.invoice_number,
               i.total_amount::text AS total_amount,
               i.amount_paid::text AS amount_paid,
               i.payment_status, i.payment_method,
               r.room_number,
               concat_ws(' ', t.first_name, t.last_name) AS tenant_name
        FROM public.invoices i
        JOIN public.rental_contracts c ON c.contract_id = i.contract_id
        JOIN public.room r ON r.room_id = c.room_id
        JOIN public.tenants t ON t.tenant_id = c.tenant_id
        {where_sql}
        ORDER BY i.invoice_id DESC
    """, values)

    return jsonify(items=cursor.fetchall())

@payment_bp.route("/api/payments/<int:invoice_id>", methods=["GET", "PUT"])
@owner_api_required
def payment_item(cursor, invoice_id):
    cursor.execute("""
        SELECT i.invoice_id, i.invoice_number,
               i.total_amount::text AS total_amount,
               i.amount_paid::text AS amount_paid,
               i.payment_status, i.payment_method,
               i.receipt_number, i.note,
               r.room_number,
               concat_ws(' ', t.first_name, t.last_name) AS tenant_name
        FROM public.invoices i
        JOIN public.rental_contracts c ON c.contract_id = i.contract_id
        JOIN public.room r ON r.room_id = c.room_id
        JOIN public.tenants t ON t.tenant_id = c.tenant_id
        WHERE i.invoice_id = %s
        LIMIT 1
    """, (invoice_id,))
    invoice = cursor.fetchone()

    if not invoice:
        raise ApiError("ไม่พบบิลนี้", 404)

    if request.method == "GET":
        return jsonify(item=invoice)

    data = get_json_data()
    amount_paid = parse_amount(data.get("amount_paid"))
    total_amount = Decimal(str(invoice["total_amount"]))
    method = clean_text(data, "payment_method", "วิธีชำระเงิน", 50, required=False)
    receipt = clean_text(data, "receipt_number", "เลขที่ใบเสร็จ", 30, required=False)
    note = clean_text(data, "note", "หมายเหตุ", 5000, required=False)

    if amount_paid > total_amount:
        raise ApiError("ยอดที่ชำระมากกว่ายอดรวมไม่ได้")
    if amount_paid > 0 and not method:
        raise ApiError("กรุณาเลือกวิธีชำระเงิน")

    if amount_paid == total_amount and amount_paid > 0:
        status = "PAID"
    elif amount_paid > 0:
        status = "PARTIAL"
    else:
        status = "UNPAID"

    cursor.execute("""
        UPDATE public.invoices
        SET amount_paid = %s, payment_status = %s,
            payment_method = NULLIF(%s, ''),
            paid_at = CASE WHEN %s > 0 THEN LOCALTIME ELSE NULL END,
            receipt_number = NULLIF(%s, ''),
            note = NULLIF(%s, '')
        WHERE invoice_id = %s
    """, (
        amount_paid, status, method, amount_paid,
        receipt, note, invoice_id
    ))

    return jsonify(message="บันทึกการชำระเงินเรียบร้อย")