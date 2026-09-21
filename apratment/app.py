import os
from flask import Flask, render_template, request, redirect, session, send_from_directory
from database import get_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=BASE_DIR)

app.secret_key = "apartment-secret-key"


@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "css"),
        filename
    )


@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "js"),
        filename
    )


@app.route("/image/<path:filename>")
def image_files(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "image"),
        filename
    )


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = None
        cursor = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                '''
                SELECT
                    user_id,
                    user_name,
                    password_hash,
                    role,
                    is_active
                FROM public."user"
                WHERE user_name = %s
                LIMIT 1
                ''',
                (username,)
            )

            user = cursor.fetchone()

            if user is None:
                return redirect("/?error=invalid")

            if not user[4]:
                return redirect("/?error=inactive")

            if user[2] != password:
                return redirect("/?error=invalid")

            role = str(user[3]).strip().lower()

            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = role

            if role == "admin" or role == "owner":
                return redirect("/owner")

            if role == "employee":
                return redirect("/employee")

            if role == "tenant":
                return redirect("/tenant")

            session.clear()

            return redirect("/?error=role")

        except Exception as e:

            print("Database error:", e)

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


@app.route("/owner")
@app.route("/owner.html")
def owner():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") not in ["admin", "owner"]:
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403

    return render_template("owner.html")


@app.route("/room.html")
def room():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") not in ["admin", "owner"]:
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403

    return render_template("room.html")


@app.route("/tenants.html")
def tenants():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") not in ["admin", "owner"]:
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403

    return render_template("tenants.html")


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


if __name__ == "__main__":
    app.run(debug=True)