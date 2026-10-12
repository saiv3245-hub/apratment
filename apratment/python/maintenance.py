from flask import Blueprint, jsonify, redirect, render_template, request, session
from common import ApiError, clean_text, get_json_data, owner_api_required, parse_int

maintenance_bp = Blueprint("maintenance", __name__)
REQUEST_TYPES = {"MAINTENANCE", "ELECTRICAL", "PLUMBING", "OTHER"}
PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}
STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"}

@maintenance_bp.route("/maintenance.html")
def maintenance_page():
    if "user_id" not in session:
        return redirect("/")
    if session.get("role") not in ("admin", "owner"):
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    return render_template("maintenance.html")

def optional_int(value, label):
    value = str(value or "").strip()
    return parse_int(value, label, 1) if value else None

def validate_request(data):
    request_type = clean_text(data, "request_type", "ประเภทงาน", 30).upper()
    priority = clean_text(data, "priority", "ความเร่งด่วน", 20).upper()
    status = clean_text(data, "status", "สถานะ", 30).upper()

    if request_type not in REQUEST_TYPES:
        raise ApiError("ประเภทงานไม่ถูกต้อง")
    if priority not in PRIORITIES:
        raise ApiError("ระดับความเร่งด่วนไม่ถูกต้อง")
    if status not in STATUSES:
        raise ApiError("สถานะแจ้งซ่อมไม่ถูกต้อง")

    return {
        "request_number": clean_text(data, "request_number", "เลขที่แจ้งซ่อม", 30),
        "tenant_id": parse_int(data.get("tenant_id"), "ผู้เช่า", 1),
        "room_id": parse_int(data.get("room_id"), "ห้องพัก", 1),
        "contract_id": optional_int(data.get("contract_id"), "สัญญาเช่า"),
        "request_type": request_type,
        "title": clean_text(data, "title", "หัวข้อ", 200),
        "details": clean_text(data, "details", "รายละเอียด", 5000),
        "priority": priority,
        "status": status,
        "assigned_employee_id": optional_int(data.get("assigned_employee_id"), "พนักงาน"),
        "resolution_note": clean_text(data, "resolution_note", "ผลการดำเนินงาน", 5000, required=False)
    }

def validate_refs(cursor, data, current_request_id=0):
    cursor.execute("SELECT 1 FROM public.tenants WHERE tenant_id = %s LIMIT 1", (data["tenant_id"],))
    if not cursor.fetchone():
        raise ApiError("ไม่พบผู้เช่าที่เลือก")

    cursor.execute("SELECT 1 FROM public.room WHERE room_id = %s LIMIT 1", (data["room_id"],))
    if not cursor.fetchone():
        raise ApiError("ไม่พบห้องพักที่เลือก")

    if data["contract_id"]:
        cursor.execute("""
            SELECT 1 FROM public.rental_contracts
            WHERE contract_id = %s
              AND tenant_id = %s
              AND room_id = %s
            LIMIT 1
        """, (data["contract_id"], data["tenant_id"], data["room_id"]))
        if not cursor.fetchone():
            raise ApiError("สัญญาที่เลือกไม่ตรงกับผู้เช่าและห้องพัก")

    if data["assigned_employee_id"]:
        cursor.execute("""
            SELECT 1 FROM public.employees
            WHERE employees_id = %s
              AND upper(btrim(employment_status)) = 'ACTIVE'
            LIMIT 1
        """, (data["assigned_employee_id"],))
        if not cursor.fetchone():
            raise ApiError("ไม่พบพนักงานที่เปิดใช้งาน")

    cursor.execute("""
        SELECT 1 FROM public.maintenance_requests
        WHERE lower(btrim(request_number)) = lower(%s)
          AND request_id <> %s
        LIMIT 1
    """, (data["request_number"], current_request_id))
    if cursor.fetchone():
        raise ApiError("เลขที่แจ้งซ่อมนี้มีอยู่แล้ว", 409)

@maintenance_bp.get("/api/maintenance/options")
@owner_api_required
def maintenance_options(cursor):
    cursor.execute("""
        SELECT tenant_id, tenant_code, first_name, last_name
        FROM public.tenants
        WHERE is_active = true
        ORDER BY tenant_code
    """)
    tenants = cursor.fetchall()

    cursor.execute("SELECT room_id, room_number FROM public.room ORDER BY floor, room_number")
    rooms = cursor.fetchall()

    cursor.execute("""
        SELECT contract_id, contract_number, tenant_id, room_id
        FROM public.rental_contracts
        ORDER BY contract_id DESC
    """)
    contracts = cursor.fetchall()

    cursor.execute("""
        SELECT employees_id, employees_code, first_name, last_name
        FROM public.employees
        WHERE upper(btrim(employment_status)) = 'ACTIVE'
        ORDER BY employees_code
    """)
    employees = cursor.fetchall()

    return jsonify(
        tenants=tenants,
        rooms=rooms,
        contracts=contracts,
        employees=employees
    )

@maintenance_bp.route("/api/maintenance", methods=["GET", "POST"])
@owner_api_required
def maintenance_api(cursor):
    if request.method == "GET":
        search = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip().upper()
        conditions = []
        values = []

        if search:
            conditions.append("""
                (m.request_number ILIKE %s
                OR m.title ILIKE %s
                OR r.room_number ILIKE %s
                OR concat_ws(' ', t.first_name, t.last_name) ILIKE %s)
            """)
            values.extend([f"%{search}%"] * 4)

        if status:
            if status not in STATUSES:
                raise ApiError("สถานะแจ้งซ่อมไม่ถูกต้อง")
            conditions.append("upper(btrim(m.status)) = %s")
            values.append(status)

        where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""

        cursor.execute(f"""
            SELECT m.request_id, m.request_number, m.title, m.priority,
                   m.status, r.room_number,
                   concat_ws(' ', t.first_name, t.last_name) AS tenant_name,
                   concat_ws(' ', e.first_name, e.last_name) AS employee_name
            FROM public.maintenance_requests m
            JOIN public.tenants t ON t.tenant_id = m.tenant_id
            JOIN public.room r ON r.room_id = m.room_id
            LEFT JOIN public.employees e ON e.employees_id = m.assigned_employee_id
            {where_sql}
            ORDER BY m.request_id DESC
        """, values)
        return jsonify(items=cursor.fetchall())

    data = validate_request(get_json_data())
    cursor.execute("LOCK TABLE public.maintenance_requests IN EXCLUSIVE MODE")
    validate_refs(cursor, data)

    cursor.execute("SELECT COALESCE(MAX(request_id), 0) + 1 AS next_id FROM public.maintenance_requests")
    request_id = cursor.fetchone()["next_id"]

    cursor.execute("""
        INSERT INTO public.maintenance_requests
        (request_id, request_number, tenant_id, room_id, contract_id,
         request_type, title, details, priority, status,
         assigned_employee_id, assigned_at, completed_at, resolution_note)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                CASE WHEN %s IS NOT NULL THEN LOCALTIME ELSE NULL END,
                CASE WHEN %s = 'COMPLETED' THEN LOCALTIME ELSE NULL END,
                NULLIF(%s, ''))
    """, (
        request_id, data["request_number"], data["tenant_id"], data["room_id"],
        data["contract_id"], data["request_type"], data["title"], data["details"],
        data["priority"], data["status"], data["assigned_employee_id"],
        data["assigned_employee_id"], data["status"], data["resolution_note"]
    ))
    return jsonify(message="เพิ่มรายการแจ้งซ่อมเรียบร้อย", request_id=request_id), 201

@maintenance_bp.route("/api/maintenance/<int:request_id>", methods=["GET", "PUT", "DELETE"])
@owner_api_required
def maintenance_item(cursor, request_id):
    cursor.execute("""
        SELECT request_id, request_number, tenant_id, room_id, contract_id,
               request_type, title, details, priority, status,
               assigned_employee_id, resolution_note
        FROM public.maintenance_requests
        WHERE request_id = %s
        LIMIT 1
    """, (request_id,))
    item = cursor.fetchone()

    if not item:
        raise ApiError("ไม่พบรายการแจ้งซ่อมนี้", 404)

    if request.method == "GET":
        return jsonify(item=item)

    if request.method == "DELETE":
        cursor.execute("DELETE FROM public.maintenance_requests WHERE request_id = %s", (request_id,))
        return jsonify(message="ลบรายการแจ้งซ่อมเรียบร้อย")

    data = validate_request(get_json_data())
    validate_refs(cursor, data, request_id)

    cursor.execute("""
        UPDATE public.maintenance_requests
        SET request_number = %s, tenant_id = %s, room_id = %s,
            contract_id = %s, request_type = %s, title = %s,
            details = %s, priority = %s, status = %s,
            assigned_employee_id = %s,
            assigned_at = CASE
                WHEN %s IS NOT NULL AND assigned_at IS NULL THEN LOCALTIME
                WHEN %s IS NULL THEN NULL
                ELSE assigned_at
            END,
            completed_at = CASE
                WHEN %s = 'COMPLETED' THEN COALESCE(completed_at, LOCALTIME)
                ELSE NULL
            END,
            resolution_note = NULLIF(%s, '')
        WHERE request_id = %s
    """, (
        data["request_number"], data["tenant_id"], data["room_id"],
        data["contract_id"], data["request_type"], data["title"],
        data["details"], data["priority"], data["status"],
        data["assigned_employee_id"], data["assigned_employee_id"],
        data["assigned_employee_id"], data["status"],
        data["resolution_note"], request_id
    ))
    return jsonify(message="แก้ไขรายการแจ้งซ่อมเรียบร้อย")