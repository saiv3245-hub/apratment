import re
import secrets
from decimal import Decimal, InvalidOperation
from functools import wraps
import psycopg2
from flask import jsonify, request, session
from psycopg2.extras import RealDictCursor
from database import get_connection

class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status

def clean_text(data, key, label, max_length, required=True):
    value = data.get(key, "")
    if not isinstance(value, str):
        raise ApiError(f"{label}ไม่ถูกต้อง")

    value = value.strip()
    if required and not value:
        raise ApiError(f"กรุณากรอก{label}")
    if len(value) > max_length:
        raise ApiError(f"{label}ยาวเกิน {max_length} ตัวอักษร")
    return value

def parse_int(value, label, minimum=None, maximum=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{label}ต้องเป็นจำนวนเต็ม")

    if minimum is not None and number < minimum:
        raise ApiError(f"{label}ต่ำกว่าค่าที่กำหนด")
    if maximum is not None and number > maximum:
        raise ApiError(f"{label}สูงกว่าค่าที่กำหนด")
    return number

def parse_money(data, key, label):
    value = clean_text(data, key, label, 20)
    try:
        amount = Decimal(value)
    except InvalidOperation:
        raise ApiError(f"{label}ต้องเป็นตัวเลข")

    if not amount.is_finite():
        raise ApiError(f"{label}ต้องเป็นตัวเลขปกติ")
    if amount < 0 or amount > Decimal("99999999.99"):
        raise ApiError(f"{label}อยู่นอกช่วงที่รองรับ")
    if amount.as_tuple().exponent < -2:
        raise ApiError(f"{label}ใส่ทศนิยมได้ไม่เกิน 2 ตำแหน่ง")
    return amount

def validate_phone(value, label):
    digits = re.sub(r"[^0-9]", "", value)
    if not 9 <= len(digits) <= 15:
        raise ApiError(f"{label}ต้องมีตัวเลข 9–15 หลัก")

def get_json_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("รูปแบบข้อมูลไม่ถูกต้อง")
    return data

def owner_api_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(error="กรุณาเข้าสู่ระบบใหม่"), 401

        if request.method not in ("GET", "HEAD"):
            sent_token = request.headers.get("X-CSRF-Token", "")
            session_token = session.get("csrf_token", "")
            if not sent_token or not session_token or not secrets.compare_digest(sent_token, session_token):
                return jsonify(error="หน้าเว็บหมดอายุ กรุณารีเฟรชแล้วลองใหม่"), 403

        conn = None
        cursor = None

        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT role, is_active
                FROM public."user"
                WHERE user_id = %s
                LIMIT 1
            """, (session["user_id"],))
            account = cursor.fetchone()

            if not account or not account["is_active"]:
                raise ApiError("บัญชีนี้ไม่สามารถใช้งานได้", 403)

            role = str(account["role"]).strip().lower()
            if role not in ("admin", "owner"):
                raise ApiError("คุณไม่มีสิทธิ์จัดการข้อมูล", 403)

            result = function(cursor, *args, **kwargs)
            conn.commit()
            return result

        except ApiError as error:
            if conn:
                conn.rollback()
            return jsonify(error=error.message), error.status
        except psycopg2.Error as error:
            if conn:
                conn.rollback()
            print("Database error:", error)
            return jsonify(error="ทำรายการกับฐานข้อมูลไม่สำเร็จ"), 500
        except Exception as error:
            if conn:
                conn.rollback()
            print("Server error:", error)
            return jsonify(error="เกิดข้อผิดพลาดในระบบ"), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return wrapped
