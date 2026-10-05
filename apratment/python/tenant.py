import re
from flask import Blueprint, jsonify, redirect, render_template, request, session
from common import ApiError, clean_text, get_json_data, owner_api_required, parse_int, validate_phone

tenant_bp = Blueprint("tenant", __name__)

@tenant_bp.route("/tenants.html")
def tenants_page():
    if "user_id" not in session:
        return redirect("/")
    if session.get("role") not in ("admin", "owner"):
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    return render_template("tenants.html")

@tenant_bp.get("/api/tenant-users")
@owner_api_required
def tenant_users_api(cursor):
    current_tenant_id = request.args.get("tenant_id", "").strip()
    current_tenant_id = parse_int(current_tenant_id, "รหัสผู้เช่า", 0) if current_tenant_id else 0

    cursor.execute("""
        SELECT u.user_id, u.user_name, u.is_active
        FROM public."user" u
        WHERE lower(btrim(u.role)) = 'tenant'
        AND (
            (u.is_active = true AND NOT EXISTS(
                SELECT 1 FROM public.tenants t WHERE t.user_id = u.user_id
            ))
            OR EXISTS(
                SELECT 1 FROM public.tenants t
                WHERE t.user_id = u.user_id AND t.tenant_id = %s
            )
        )
        ORDER BY u.user_name
    """, (current_tenant_id,))

    return jsonify(items=cursor.fetchall())

def validate_tenant_data(data):
    payload = {
        "tenant_code": clean_text(data, "tenant_code", "รหัสผู้เช่า", 20),
        "user_id": parse_int(data.get("user_id"), "บัญชีผู้ใช้งาน", 1),
        "first_name": clean_text(data, "first_name", "ชื่อ", 100),
        "last_name": clean_text(data, "last_name", "นามสกุล", 100),
        "national_id": clean_text(data, "national_id", "เลขประจำตัวประชาชน", 20),
        "phone": clean_text(data, "phone", "เบอร์โทรศัพท์", 20),
        "email": clean_text(data, "email", "อีเมล", 150),
        "address": clean_text(data, "address", "ที่อยู่", 5000),
        "emergency_contact_name": clean_text(data, "emergency_contact_name", "ชื่อผู้ติดต่อฉุกเฉิน", 150),
        "emergency_contact_phone": clean_text(data, "emergency_contact_phone", "เบอร์ผู้ติดต่อฉุกเฉิน", 20)
    }

    validate_phone(payload["phone"], "เบอร์โทรศัพท์")
    validate_phone(payload["emergency_contact_phone"], "เบอร์ผู้ติดต่อฉุกเฉิน")

    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", payload["email"]):
        raise ApiError("รูปแบบอีเมลไม่ถูกต้อง")

    if data.get("is_active") not in ("true", "false"):
        raise ApiError("สถานะข้อมูลผู้เช่าไม่ถูกต้อง")

    payload["is_active"] = data["is_active"] == "true"
    return payload

def validate_tenant_user(cursor, user_id, current_tenant_id=0):
    cursor.execute("""
        SELECT role, is_active
        FROM public."user"
        WHERE user_id = %s
        LIMIT 1
    """, (user_id,))
    user = cursor.fetchone()

    if not user:
        raise ApiError("ไม่พบบัญชีผู้ใช้งานที่เลือก")

    if str(user["role"]).strip().lower() != "tenant":
        raise ApiError("บัญชีที่เลือกต้องเป็นสิทธิ์ผู้เช่า")

    if not user["is_active"]:
        cursor.execute("""
            SELECT 1 FROM public.tenants
            WHERE tenant_id = %s AND user_id = %s
            LIMIT 1
        """, (current_tenant_id, user_id))

        if not cursor.fetchone():
            raise ApiError("บัญชีผู้ใช้งานที่เลือกถูกปิดใช้งาน")

    cursor.execute("""
        SELECT 1 FROM public.tenants
        WHERE user_id = %s AND tenant_id <> %s
        LIMIT 1
    """, (user_id, current_tenant_id))

    if cursor.fetchone():
        raise ApiError("บัญชีนี้เชื่อมกับผู้เช่ารายอื่นแล้ว", 409)

def validate_tenant_duplicates(cursor, payload, current_tenant_id=0):
    checks = [
        ("tenant_code", payload["tenant_code"], "รหัสผู้เช่านี้มีอยู่แล้ว"),
        ("national_id", payload["national_id"], "เลขประจำตัวประชาชนนี้มีอยู่แล้ว"),
        ("email", payload["email"], "อีเมลผู้เช่านี้มีอยู่แล้ว")
    ]

    for column, value, message in checks:
        cursor.execute(f"""
            SELECT 1 FROM public.tenants
            WHERE lower(btrim({column})) = lower(%s) AND tenant_id <> %s
            LIMIT 1
        """, (value, current_tenant_id))

        if cursor.fetchone():
            raise ApiError(message, 409)

@tenant_bp.route("/api/tenants", methods=["GET", "POST"])
@owner_api_required
def tenants_api(cursor):
    if request.method == "GET":
        search = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip()
        conditions = []
        values = []

        if search:
            conditions.append("""
                (tenant_code ILIKE %s OR concat_ws(' ', first_name, last_name) ILIKE %s
                OR phone ILIKE %s OR email ILIKE %s)
            """)
            values.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

        if status:
            if status not in ("true", "false"):
                raise ApiError("สถานะผู้เช่าไม่ถูกต้อง")
            conditions.append("is_active = %s")
            values.append(status == "true")

        where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""

        cursor.execute(f"""
            SELECT tenant_id, tenant_code, first_name, last_name, phone, email, is_active
            FROM public.tenants
            {where_sql}
            ORDER BY tenant_code, tenant_id
        """, values)

        return jsonify(items=cursor.fetchall())

    data = get_json_data()
    payload = validate_tenant_data(data)

    cursor.execute("LOCK TABLE public.tenants IN EXCLUSIVE MODE")
    validate_tenant_duplicates(cursor, payload)
    validate_tenant_user(cursor, payload["user_id"])

    cursor.execute("SELECT COALESCE(MAX(tenant_id), 0) + 1 AS next_id FROM public.tenants")
    tenant_id = cursor.fetchone()["next_id"]

    cursor.execute("""
        INSERT INTO public.tenants
        (tenant_id, tenant_code, user_id, first_name, last_name, national_id, phone, email,
         address, emergency_contact_name, emergency_contact_phone, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING tenant_id
    """, (
        tenant_id, payload["tenant_code"], payload["user_id"], payload["first_name"],
        payload["last_name"], payload["national_id"], payload["phone"], payload["email"],
        payload["address"], payload["emergency_contact_name"],
        payload["emergency_contact_phone"], payload["is_active"]
    ))

    return jsonify(message="เพิ่มผู้เช่าเรียบร้อย", tenant_id=cursor.fetchone()["tenant_id"]), 201

@tenant_bp.route("/api/tenants/<int:tenant_id>", methods=["GET", "PUT", "DELETE"])
@owner_api_required
def tenant_item_api(cursor, tenant_id):
    cursor.execute("""
        SELECT t.tenant_id, t.tenant_code, t.user_id, t.first_name, t.last_name, t.national_id,
               t.phone, t.email, t.address, t.emergency_contact_name, t.emergency_contact_phone,
               t.is_active, u.user_name
        FROM public.tenants t
        LEFT JOIN public."user" u ON u.user_id = t.user_id
        WHERE t.tenant_id = %s
        LIMIT 1
    """, (tenant_id,))
    tenant_data = cursor.fetchone()

    if not tenant_data:
        raise ApiError("ไม่พบข้อมูลผู้เช่านี้", 404)

    if request.method == "GET":
        return jsonify(item=tenant_data)

    if request.method == "DELETE":
        cursor.execute("""
            SELECT EXISTS(SELECT 1 FROM public.rental_contracts WHERE tenant_id = %s)
            OR EXISTS(SELECT 1 FROM public.maintenance_requests WHERE tenant_id = %s) AS is_used
        """, (tenant_id, tenant_id))

        if cursor.fetchone()["is_used"]:
            raise ApiError("ลบผู้เช่านี้ไม่ได้ เพราะมีประวัติสัญญาหรือแจ้งซ่อม ใช้การปิดใช้งานแทน", 409)

        cursor.execute("DELETE FROM public.tenants WHERE tenant_id = %s", (tenant_id,))
        return jsonify(message="ลบข้อมูลผู้เช่าเรียบร้อย")

    data = get_json_data()
    payload = validate_tenant_data(data)

    cursor.execute("LOCK TABLE public.tenants IN EXCLUSIVE MODE")
    validate_tenant_duplicates(cursor, payload, tenant_id)
    validate_tenant_user(cursor, payload["user_id"], tenant_id)

    cursor.execute("""
        UPDATE public.tenants
        SET tenant_code = %s, user_id = %s, first_name = %s, last_name = %s,
            national_id = %s, phone = %s, email = %s, address = %s,
            emergency_contact_name = %s, emergency_contact_phone = %s, is_active = %s
        WHERE tenant_id = %s
    """, (
        payload["tenant_code"], payload["user_id"], payload["first_name"], payload["last_name"],
        payload["national_id"], payload["phone"], payload["email"], payload["address"],
        payload["emergency_contact_name"], payload["emergency_contact_phone"],
        payload["is_active"], tenant_id
    ))

    return jsonify(message="แก้ไขข้อมูลผู้เช่าเรียบร้อย")