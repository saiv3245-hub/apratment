const tenantModal = document.getElementById("tenantModal");
const tenantForm = document.getElementById("tenantForm");
const tenantCode = document.getElementById("tenantCode");
const tenantNotice = document.getElementById("tenantNotice");
const tenantFilter = document.getElementById("tenantFilter");
const tenantFilterMessage = document.getElementById("tenantFilterMessage");
const clearTenantFilters = document.getElementById("clearTenantFilters");

if (tenantModal && tenantForm && tenantCode && tenantNotice) {
    tenantModal.addEventListener("show.bs.modal", function () {
        tenantForm.reset();
        tenantNotice.hidden = true;
        tenantNotice.textContent = "";

        const menu = document.getElementById("sidebarMenu");
        const toggle = document.getElementById("sidebarToggle");
        if (menu && toggle) {
            menu.classList.remove("active");
            menu.inert = true;
            toggle.setAttribute("aria-expanded", "false");
        }
    });

    tenantModal.addEventListener("shown.bs.modal", function () {
        tenantCode.focus();
    });

    tenantModal.addEventListener("hidden.bs.modal", function () {
        tenantForm.reset();
        tenantNotice.hidden = true;
        tenantNotice.textContent = "";
    });

    tenantForm.addEventListener("submit", function (event) {
        event.preventDefault();
        tenantNotice.hidden = true;

        tenantForm.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], textarea').forEach(function (field) {
            field.value = field.value.trim();
        });

        if (!tenantForm.reportValidity()) {
            return;
        }

        tenantNotice.textContent = "ช่องที่กรอกผ่านการตรวจเบื้องต้นแล้ว แต่ยังไม่ได้บันทึก ไม่ได้ตรวจข้อมูลซ้ำหรือยืนยันเลขประจำตัวประชาชน และยังไม่ได้เชื่อมบัญชีผู้ใช้งาน";
        tenantNotice.hidden = false;
        tenantNotice.scrollIntoView({ block: "nearest" });
    });

    tenantForm.addEventListener("input", function () {
        tenantNotice.hidden = true;
        tenantNotice.textContent = "";
    });
}

if (tenantFilter && tenantFilterMessage && clearTenantFilters) {
    tenantFilter.addEventListener("submit", function (event) {
        event.preventDefault();
        tenantFilterMessage.textContent = "ยังค้นหารายการผู้เช่าไม่ได้ เพราะยังไม่เชื่อมฐานข้อมูล";
    });

    clearTenantFilters.addEventListener("click", function () {
        tenantFilter.reset();
        tenantFilterMessage.textContent = "ล้างตัวกรองแล้ว ยังไม่มีการค้นหาจากฐานข้อมูล";
    });
}