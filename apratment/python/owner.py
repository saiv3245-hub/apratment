from flask import Blueprint, jsonify, redirect, render_template, session
from common import owner_api_required

owner_bp = Blueprint("owner", __name__)

@owner_bp.route("/owner")
@owner_bp.route("/owner.html")
def owner_page():
    if "user_id" not in session:
        return redirect("/")
    if session.get("role") not in ("admin", "owner"):
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    return render_template("owner.html")

@owner_bp.get("/api/owner/dashboard")
@owner_api_required
def owner_dashboard(cursor):
    cursor.execute("""
        SELECT COUNT(*) AS total_rooms,
               COUNT(*) FILTER (WHERE upper(btrim(status)) = 'AVAILABLE') AS available_rooms
        FROM public.room
    """)
    room_summary = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) AS active_tenants FROM public.tenants WHERE is_active = true")
    tenant_summary = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) AS overdue_bills
        FROM public.invoices
        WHERE due_date < CURRENT_DATE
          AND COALESCE(amount_paid, 0) < COALESCE(total_amount, 0)
          AND upper(btrim(payment_status)) <> 'PAID'
    """)
    invoice_summary = cursor.fetchone()

    cursor.execute("""
        SELECT i.invoice_id, r.room_number, concat_ws(' ', t.first_name, t.last_name) AS tenant_name,
               i.total_amount::text AS total_amount, i.payment_status
        FROM public.invoices i
        JOIN public.rental_contracts c ON c.contract_id = i.contract_id
        JOIN public.room r ON r.room_id = c.room_id
        JOIN public.tenants t ON t.tenant_id = c.tenant_id
        ORDER BY i.billing_month DESC, i.invoice_id DESC
        LIMIT 5
    """)
    invoices = cursor.fetchall()

    cursor.execute("""
        SELECT m.request_id, m.request_number, r.room_number, m.title, m.priority, m.status
        FROM public.maintenance_requests m
        JOIN public.room r ON r.room_id = m.room_id
        WHERE upper(btrim(m.status)) NOT IN ('COMPLETED', 'CANCELLED')
        ORDER BY CASE upper(btrim(m.priority))
            WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 WHEN 'LOW' THEN 4 ELSE 5
        END, m.request_id DESC
        LIMIT 5
    """)
    repairs = cursor.fetchall()

    return jsonify(
        total_rooms=room_summary["total_rooms"],
        available_rooms=room_summary["available_rooms"],
        active_tenants=tenant_summary["active_tenants"],
        overdue_bills=invoice_summary["overdue_bills"],
        invoices=invoices,
        repairs=repairs
    )