import re
from datetime import date
from flask import Blueprint, jsonify, redirect, render_template, request, session
from common import ApiError, clean_text, get_json_data, owner_api_required, parse_int, validate_phone

employee_bp = Blueprint("employee_manage", __name__)
EMPLOYEE_STATUS = {"ACTIVE", "INACTIVE"}

@employee_bp.route("/employees.html")
def employees_page():
    if "user_id" not in session:
        return redirect("/")
    if session.get("role") not in ("admin", "owner"):
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    return render_template("employees.html")

def validate_hire_date(value):
    value = str(value or "").strip()
    if not value:
        return ""
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ApiError("วันที่เริ่มงานไม่ถูกต้อง")
    return value

def validate_employee_data(data):
    email = clean_text(data, "email", "อีเมล", 150, required=False)
    payload = {
        "employees_code": clean_text(data, "employees_code", "รหัสพนักงาน", 20),
        "user_id": parse_int(data.get("user_id"), "บัญชีผู้ใช้งาน", 1),
        "first_name": clean_text(data, "first_name", "ชื่อ", 100),
        "last_name": clean_text(data, "last_name", "นามสกุล", 100),
        "phone": clean_text(data, "phone", "เบอร์โทรศัพท์", 20),
        "email": email,
        "position": clean_text(data, "position", "ตำแหน่ง", 100),
        "duty_description": clean_text(data, "duty_description", "รายละเอียดหน้าที่", 5000, required=False),
        "hire_date": validate_hire_date(data.get("hire_date")),
        "employment_status": clean_text(data, "employment_status", "สถานะพนักงาน", 20).upper()
    }
    validate_phone(payload["phone"], "เบอร์โทรศัพท์")
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ApiError("รูปแบบอีเมลไม่ถูกต้อง")
    if payload["employment_status"] not in EMPLOYEE_STATUS:
        raise ApiError("สถานะพนักงานไม่ถูกต้อง")
    return payload

def validate_employee_user(cursor, user_id, current_employee_id=0):
    cursor.execute("""
        SELECT role, is_active
        FROM public."user"
        WHERE user_id = %s
        LIMIT 1
    """, (user_id,))
    user = cursor.fetchone()
    if not user:
        raise ApiError("ไม่พบบัญชีผู้ใช้งานที่เลือก")
    if str(user["role"]).strip().lower() != "employee":
        raise ApiError("บัญชีที่เลือกต้องเป็นสิทธิ์พนักงาน")
    if not user["is_active"]:
        raise ApiError("บัญชีผู้ใช้งานนี้ถูกปิดใช้งาน")
    cursor.execute("""
        SELECT 1
        FROM public.employees
        WHERE user_id = %s AND employees_id <> %s
        LIMIT 1
    """, (user_id, current_employee_id))
    if cursor.fetchone():
        raise ApiError("บัญชีนี้เชื่อมกับพนักงานรายอื่นแล้ว", 409)

def validate_employee_code(cursor, employees_code, current_employee_id=0):
    cursor.execute("""
        SELECT 1
        FROM public.employees
        WHERE lower(btrim(employees_code)) = lower(%s)
          AND employees_id <> %s
        LIMIT 1
    """, (employees_code, current_employee_id))
    if cursor.fetchone():
        raise ApiError("รหัสพนักงานนี้มีอยู่แล้ว", 409)

@employee_bp.get("/api/employee-users")
@owner_api_required
def employee_users_api(cursor):
    current_id = request.args.get("employee_id", "").strip()
    current_id = parse_int(current_id, "รหัสพนักงาน", 0) if current_id else 0
    cursor.execute("""
        SELECT u.user_id, u.user_name
        FROM public."user" u
        WHERE lower(btrim(u.role)) = 'employee'
          AND (
              (u.is_active = true AND NOT EXISTS(
                  SELECT 1 FROM public.employees e
                  WHERE e.user_id = u.user_id
              ))
              OR EXISTS(
                  SELECT 1 FROM public.employees e
                  WHERE e.user_id = u.user_id
                    AND e.employees_id = %s
              )
          )
        ORDER BY u.user_name
    """, (current_id,))
    return jsonify(items=cursor.fetchall())

@employee_bp.route("/api/employees", methods=["GET", "POST"])
@owner_api_required
def employees_api(cursor):
    if request.method == "GET":
        search = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip().upper()
        conditions = []
        values = []

        if search:
            conditions.append("""
                (e.employees_code ILIKE %s
                OR concat_ws(' ', e.first_name, e.last_name) ILIKE %s
                OR e.phone ILIKE %s
                OR e.position ILIKE %s)
            """)
            values.extend([f"%{search}%"] * 4)

        if status:
            if status not in EMPLOYEE_STATUS:
                raise ApiError("สถานะพนักงานไม่ถูกต้อง")
            conditions.append("upper(btrim(e.employment_status)) = %s")
            values.append(status)

        where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""

        cursor.execute(f"""
            SELECT e.employees_id, e.employees_code, e.first_name, e.last_name,
                   e.phone, e.email, e.position, e.employment_status, u.user_name
            FROM public.employees e
            LEFT JOIN public."user" u ON u.user_id = e.user_id
            {where_sql}
            ORDER BY e.employees_code, e.employees_id
        """, values)
        return jsonify(items=cursor.fetchall())

    payload = validate_employee_data(get_json_data())
    cursor.execute("LOCK TABLE public.employees IN EXCLUSIVE MODE")
    validate_employee_code(cursor, payload["employees_code"])
    validate_employee_user(cursor, payload["user_id"])
    cursor.execute("SELECT COALESCE(MAX(employees_id), 0) + 1 AS next_id FROM public.employees")
    employee_id = cursor.fetchone()["next_id"]

    cursor.execute("""
        INSERT INTO public.employees
        (employees_id, employees_code, user_id, first_name, last_name, phone,
         email, position, duty_description, hire_date, employment_status)
        VALUES (%s, %s, %s, %s, %s, %s, NULLIF(%s, ''), %s,
                NULLIF(%s, ''), NULLIF(%s, '')::date, %s)
    """, (
        employee_id, payload["employees_code"], payload["user_id"],
        payload["first_name"], payload["last_name"], payload["phone"],
        payload["email"], payload["position"], payload["duty_description"],
        payload["hire_date"], payload["employment_status"]
    ))
    return jsonify(message="เพิ่มพนักงานเรียบร้อย", employees_id=employee_id), 201

@employee_bp.route("/api/employees/<int:employee_id>", methods=["GET", "PUT", "DELETE"])
@owner_api_required
def employee_item_api(cursor, employee_id):
    cursor.execute("""
        SELECT e.employees_id, e.employees_code, e.user_id, e.first_name,
               e.last_name, e.phone, e.email, e.position, e.duty_description,
               to_char(e.hire_date, 'YYYY-MM-DD') AS hire_date,
               e.employment_status
        FROM public.employees e
        WHERE e.employees_id = %s
        LIMIT 1
    """, (employee_id,))
    employee = cursor.fetchone()

    if not employee:
        raise ApiError("ไม่พบข้อมูลพนักงานนี้", 404)

    if request.method == "GET":
        return jsonify(item=employee)

    if request.method == "DELETE":
        cursor.execute("""
            SELECT 1
            FROM public.maintenance_requests
            WHERE assigned_employee_id = %s
            LIMIT 1
        """, (employee_id,))
        if cursor.fetchone():
            raise ApiError("ลบพนักงานนี้ไม่ได้ เพราะมีประวัติรับงานแจ้งซ่อม ใช้การปิดใช้งานแทน", 409)
        cursor.execute("DELETE FROM public.employees WHERE employees_id = %s", (employee_id,))
        return jsonify(message="ลบพนักงานเรียบร้อย")

    payload = validate_employee_data(get_json_data())
    cursor.execute("LOCK TABLE public.employees IN EXCLUSIVE MODE")
    validate_employee_code(cursor, payload["employees_code"], employee_id)
    validate_employee_user(cursor, payload["user_id"], employee_id)

    cursor.execute("""
        UPDATE public.employees
        SET employees_code = %s, user_id = %s, first_name = %s,
            last_name = %s, phone = %s, email = NULLIF(%s, ''),
            position = %s, duty_description = NULLIF(%s, ''),
            hire_date = NULLIF(%s, '')::date, employment_status = %s
        WHERE employees_id = %s
    """, (
        payload["employees_code"], payload["user_id"], payload["first_name"],
        payload["last_name"], payload["phone"], payload["email"],
        payload["position"], payload["duty_description"], payload["hire_date"],
        payload["employment_status"], employee_id
    ))
    return jsonify(message="แก้ไขข้อมูลพนักงานเรียบร้อย")