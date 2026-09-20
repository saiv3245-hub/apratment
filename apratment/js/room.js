const roomModal = document.getElementById("roomModal");
const roomForm = document.getElementById("roomForm");
const roomNumber = document.getElementById("roomNumber");
const roomType = document.getElementById("roomType");
const roomNotice = document.getElementById("roomNotice");

const roomFilter = document.getElementById("roomFilter");
const filterMessage = document.getElementById("filterMessage");
const clearFilters = document.getElementById("clearFilters");

if (roomModal && roomForm && roomNumber && roomType && roomNotice) {
    roomModal.addEventListener("show.bs.modal", function () {
        roomForm.reset();
        roomNotice.hidden = true;
        roomNotice.textContent = "";

        const sidebarMenu = document.getElementById("sidebarMenu");
        const sidebarToggle = document.getElementById("sidebarToggle");

        if (sidebarMenu && sidebarToggle) {
            sidebarMenu.classList.remove("active");
            sidebarMenu.inert = true;
            sidebarToggle.setAttribute("aria-expanded", "false");
        }
    });

    roomModal.addEventListener("shown.bs.modal", function () {
        roomNumber.focus();
    });

    roomForm.addEventListener("submit", function (event) {
        event.preventDefault();

        roomNotice.hidden = true;
        roomNumber.value = roomNumber.value.trim();
        roomType.value = roomType.value.trim();

        if (!roomForm.reportValidity()) {
            return;
        }

        roomNotice.textContent = "รูปแบบข้อมูลเบื้องต้นผ่านแล้ว แต่ยังไม่ได้บันทึกหรือเช็กหมายเลขห้องซ้ำ เพราะยังไม่เชื่อมฐานข้อมูล";
        roomNotice.hidden = false;
    });

    roomForm.addEventListener("input", function () {
        roomNotice.hidden = true;
        roomNotice.textContent = "";
    });
}

if (roomFilter && filterMessage && clearFilters) {
    roomFilter.addEventListener("submit", function (event) {
        event.preventDefault();

        filterMessage.textContent = "ยังค้นหารายการไม่ได้ เพราะยังไม่เชื่อมฐานข้อมูล";
    });

    clearFilters.addEventListener("click", function () {
        roomFilter.reset();
        filterMessage.textContent = "ล้างตัวกรองแล้ว ยังไม่มีการค้นหาจากฐานข้อมูล";
    });
}