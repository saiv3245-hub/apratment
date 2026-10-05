from flask import Blueprint, jsonify, redirect, render_template, session
from common import owner_api_required

report_bp = Blueprint("report", __name__)

@report_bp.route("/reports.html")
def reports_page():
    if "user_id" not in session:
        return redirect("/")
    if session.get("role") not in ("admin", "owner"):
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    return render_template("reports.html")

@report_bp.get("/api/reports/summary")
@owner_api_required
def report_summary(cursor):
    cursor.execute("""
        SELECT COUNT(*) AS total_rooms,
               COUNT(*) FILTER (
                   WHERE upper(btrim(status)) = 'AVAILABLE'
               ) AS available_rooms,
               COUNT(*) FILTER (
                   WHERE upper(btrim(status)) = 'OCCUPIED'
               ) AS occupied_rooms,
               COUNT(*) FILTER (
                   WHERE upper(btrim(status)) = 'MAINTENANCE'
               ) AS maintenance_rooms
        FROM public.room
    """)
    rooms = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) AS active_tenants
        FROM public.tenants
        WHERE is_active = true
    """)
    tenants = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) AS active_contracts
        FROM public.rental_contracts
        WHERE upper(btrim(contract_status)) = 'ACTIVE'
    """)
    contracts = cursor.fetchone()

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0)::text AS billed_total,
               COALESCE(SUM(amount_paid), 0)::text AS paid_total,
               COALESCE(SUM(total_amount - amount_paid), 0)::text AS outstanding_total,
               COUNT(*) FILTER (
                   WHERE upper(btrim(payment_status)) = 'UNPAID'
               ) AS unpaid_count,
               COUNT(*) FILTER (
                   WHERE upper(btrim(payment_status)) = 'PARTIAL'
               ) AS partial_count,
               COUNT(*) FILTER (
                   WHERE upper(btrim(payment_status)) = 'PAID'
               ) AS paid_count
        FROM public.invoices
    """)
    finance = cursor.fetchone()

    cursor.execute("""
        SELECT status, COUNT(*) AS count
        FROM public.maintenance_requests
        GROUP BY status
        ORDER BY status
    """)
    repairs = cursor.fetchall()

    cursor.execute("""
        SELECT to_char(billing_month, 'YYYY-MM') AS month,
               COALESCE(SUM(total_amount), 0)::text AS billed,
               COALESCE(SUM(amount_paid), 0)::text AS paid
        FROM public.invoices
        GROUP BY billing_month
        ORDER BY billing_month DESC
        LIMIT 6
    """)
    monthly = cursor.fetchall()

    return jsonify(
        rooms=rooms,
        tenants=tenants,
        contracts=contracts,
        finance=finance,
        repairs=repairs,
        monthly=monthly
    )