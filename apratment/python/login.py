import os
import secrets
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_connection
from owner import owner_bp
from room import room_bp
from tenant import tenant_bp
from employee import employee_bp
from contract import contract_bp
from utility import utility_bp
from payment import payment_bp
from maintenance import maintenance_bp
from report import report_bp
from register import register_bp

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, template_folder=ROOT_DIR)
app.secret_key = "apartment-secret-key"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

app.register_blueprint(owner_bp)
app.register_blueprint(room_bp)
app.register_blueprint(tenant_bp)
app.register_blueprint(employee_bp)
app.register_blueprint(contract_bp)
app.register_blueprint(utility_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(maintenance_bp)
app.register_blueprint(report_bp)
app.register_blueprint(register_bp)

@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(os.path.join(ROOT_DIR, "css"), filename)

@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(os.path.join(ROOT_DIR, "js"), filename)

@app.route("/image/<path:filename>")
def image_files(filename):
    return send_from_directory(os.path.join(ROOT_DIR, "image"), filename)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            return redirect("/?error=invalid")

        conn = None
        cursor = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id, user_name, password_hash, role, is_active
                FROM public."user"
                WHERE lower(btrim(user_name)) = lower(%s)
                LIMIT 1
            """, (username,))

            user = cursor.fetchone()

            if user is None:
                return redirect("/?error=invalid")

            if not user[4]:
                return redirect("/?error=inactive")

            stored_password = str(user[2])
            is_hash = stored_password.startswith(("scrypt:", "pbkdf2:"))

            password_ok = (
                check_password_hash(stored_password, password)
                if is_hash
                else stored_password == password
            )

            if not password_ok:
                return redirect("/?error=invalid")

            role = str(user[3]).strip().lower()

            if role not in ("admin", "owner", "employee", "tenant"):
                return redirect("/?error=role")

            if not is_hash:
                cursor.execute("""
                    UPDATE public."user"
                    SET password_hash = %s
                    WHERE user_id = %s
                """, (
                    generate_password_hash(password),
                    user[0]
                ))

            cursor.execute("""
                UPDATE public."user"
                SET last_login = LOCALTIME
                WHERE user_id = %s
            """, (user[0],))

            conn.commit()

            session.clear()
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = role
            session["csrf_token"] = secrets.token_urlsafe(32)

            if role in ("admin", "owner"):
                return redirect("/owner")

            if role == "employee":
                return redirect("/employee")

            return redirect("/tenant")

        except Exception as error:
            if conn:
                conn.rollback()

            print("Database error:", error)

            return redirect("/?error=database")

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()

    return render_template("login.html")

@app.route("/login.html")
def login_html():
    session.clear()
    return redirect("/")

@app.route("/register.html")
def register():
    return render_template("register.html")

@app.route("/employee")
def employee():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "employee":
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403

    return "หน้าพนักงาน"

@app.route("/tenant")
def tenant():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "tenant":
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403

    return "หน้าผู้เช่า"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.get("/api/csrf")
def csrf_token():
    if "user_id" not in session:
        return jsonify(error="กรุณาเข้าสู่ระบบใหม่"), 401

    if session.get("role") not in ("admin", "owner"):
        return jsonify(error="คุณไม่มีสิทธิ์จัดการข้อมูล"), 403

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)

    return jsonify(token=session["csrf_token"])

if __name__ == "__main__":
    app.run(debug=True)