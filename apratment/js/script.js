function setupPasswordToggle(buttonId, inputId, iconId) {
    const button = document.getElementById(buttonId);
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);

    if (!button || !input || !icon) return;

    button.addEventListener("click", function () {
        const isPassword = input.type === "password";

        input.type = isPassword ? "text" : "password";

        icon.classList.toggle("bi-eye", !isPassword);
        icon.classList.toggle("bi-eye-slash", isPassword);
    });
}

setupPasswordToggle(
    "togglePassword",
    "password",
    "passwordIcon"
);

setupPasswordToggle(
    "toggleRegisterPassword",
    "password",
    "registerPasswordIcon"
);

setupPasswordToggle(
    "toggleConfirmPassword",
    "confirmPassword",
    "confirmPasswordIcon"
);

const params = new URLSearchParams(window.location.search);

const loginMessage = document.getElementById("loginMessage");

const error = params.get("error");
const registered = params.get("registered");

if (loginMessage && registered === "1") {
    loginMessage.textContent =
        "สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ";

    loginMessage.classList.remove(
        "d-none",
        "alert-danger"
    );

    loginMessage.classList.add("alert-success");

} else if (loginMessage && error) {
    const messages = {
        invalid: "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
        inactive: "บัญชีผู้ใช้นี้ถูกปิดใช้งาน",
        role: "ไม่พบสิทธิ์การใช้งานของผู้ใช้",
        database: "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"
    };

    loginMessage.textContent =
        messages[error] ||
        "เกิดข้อผิดพลาดในการเข้าสู่ระบบ";

    loginMessage.classList.remove(
        "d-none",
        "alert-success"
    );

    loginMessage.classList.add("alert-danger");
}

const registerForm =
    document.getElementById("registerForm");

const registerMessage =
    document.getElementById("registerMessage");

if (registerForm && registerMessage) {
    registerForm.addEventListener(
        "submit",
        async function (event) {
            event.preventDefault();

            if (!registerForm.reportValidity()) {
                return;
            }

            const formData =
                new FormData(registerForm);

            const payload = {
                username:
                    String(
                        formData.get("username") || ""
                    ).trim(),

                full_name:
                    String(
                        formData.get("full_name") || ""
                    ).trim(),

                email:
                    String(
                        formData.get("email") || ""
                    ).trim(),

                phone:
                    String(
                        formData.get("phone") || ""
                    ).trim(),

                password:
                    String(
                        formData.get("password") || ""
                    ),

                confirm_password:
                    String(
                        formData.get("confirm_password") || ""
                    )
            };

            if (
                payload.password !==
                payload.confirm_password
            ) {
                registerMessage.textContent =
                    "รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน";

                registerMessage.className =
                    "alert alert-danger";

                return;
            }

            const submitButton =
                registerForm.querySelector(
                    'button[type="submit"]'
                );

            submitButton.disabled = true;

            registerMessage.textContent =
                "กำลังสร้างบัญชี...";

            registerMessage.className =
                "alert alert-info";

            try {
                const response =
                    await fetch(
                        "/api/register",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify(payload)
                        }
                    );

                const data =
                    await response
                        .json()
                        .catch(() => ({}));

                if (!response.ok) {
                    throw new Error(
                        data.error ||
                        "สมัครสมาชิกไม่สำเร็จ"
                    );
                }

                window.location.href =
                    "/?registered=1";

            } catch (error) {
                registerMessage.textContent =
                    error.message;

                registerMessage.className =
                    "alert alert-danger";

            } finally {
                submitButton.disabled = false;
            }
        }
    );
}