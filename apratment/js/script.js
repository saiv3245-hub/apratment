const togglePassword = document.getElementById("togglePassword");
const password = document.getElementById("password");
const passwordIcon = document.getElementById("passwordIcon");
const loginMessage = document.getElementById("loginMessage");

if (togglePassword && password && passwordIcon) {

    togglePassword.addEventListener("click", function () {

        if (password.type === "password") {

            password.type = "text";

            passwordIcon.classList.remove("bi-eye");

            passwordIcon.classList.add("bi-eye-slash");

        } else {

            password.type = "password";

            passwordIcon.classList.remove("bi-eye-slash");

            passwordIcon.classList.add("bi-eye");

        }

    });

}


const params = new URLSearchParams(window.location.search);

const error = params.get("error");


if (loginMessage && error) {

    if (error === "invalid") {

        loginMessage.textContent =
            "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง";

    } else if (error === "inactive") {

        loginMessage.textContent =
            "บัญชีผู้ใช้นี้ถูกปิดใช้งาน";

    } else if (error === "role") {

        loginMessage.textContent =
            "ไม่พบสิทธิ์การใช้งานของผู้ใช้";

    } else if (error === "database") {

        loginMessage.textContent =
            "ไม่สามารถเชื่อมต่อฐานข้อมูลได้";

    }

    loginMessage.classList.remove("d-none");
}