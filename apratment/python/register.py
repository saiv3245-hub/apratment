import re
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash
from database import get_connection

register_bp = Blueprint("register", __name__)

@register_bp.post("/api/register")
def register_api():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="รูปแบบข้อมูลไม่ถูกต้อง"), 400

    username = str(data.get("username", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", ""))
    confirm_password = str(data.get("confirm_password", ""))

    if not username or not full_name or not email or not phone or not password or not confirm_password:
        return jsonify(error="กรุณากรอกข้อมูลให้ครบทุกช่อง"), 400

    if len(username) < 3 or len(username) > 100 or any(char.isspace() for char in username):
        return jsonify(error="ชื่อผู้ใช้ต้องมี 3-100 ตัวอักษรและห้ามมีช่องว่าง"), 400

    if len(full_name) > 200:
        return jsonify(error="ชื่อ-นามสกุลยาวเกิน 200 ตัวอักษร"), 400

    if len(email) > 150 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return jsonify(error="รูปแบบอีเมลไม่ถูกต้อง"), 400

    if not re.fullmatch(r"\d{10}", phone):
        return jsonify(error="เบอร์โทรศัพท์ต้องเป็นตัวเลข 10 หลัก"), 400

    if len(password) < 6:
        return jsonify(error="รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร"), 400

    if len(password) > 128:
        return jsonify(error="รหัสผ่านยาวเกิน 128 ตัวอักษร"), 400

    if password != confirm_password:
        return jsonify(error="รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน"), 400

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('LOCK TABLE public."user" IN EXCLUSIVE MODE')

        cursor.execute("""
            SELECT 1
            FROM public."user"
            WHERE lower(btrim(user_name)) = lower(%s)
            LIMIT 1
        """, (username,))

        if cursor.fetchone():
            return jsonify(error="ชื่อผู้ใช้นี้ถูกใช้งานแล้ว"), 409

        cursor.execute("""
            SELECT 1
            FROM public."user"
            WHERE email IS NOT NULL
              AND lower(btrim(email)) = lower(%s)
            LIMIT 1
        """, (email,))

        if cursor.fetchone():
            return jsonify(error="อีเมลนี้ถูกใช้งานแล้ว"), 409

        cursor.execute("""
            INSERT INTO public."user"
            (user_name, password_hash, role, is_active, full_name, email, phone)
            VALUES (%s, %s, 'tenant', true, %s, %s, %s)
            RETURNING user_id
        """, (
            username,
            generate_password_hash(password),
            full_name,
            email,
            phone
        ))

        user_id = cursor.fetchone()[0]

        conn.commit()

        return jsonify(
            message="สมัครสมาชิกสำเร็จ",
            user_id=user_id
        ), 201

    except Exception as error:
        if conn:
            conn.rollback()

        print("Register error:", error)

        return jsonify(
            error="ไม่สามารถสมัครสมาชิกได้ กรุณาตรวจสอบฐานข้อมูล"
        ), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()