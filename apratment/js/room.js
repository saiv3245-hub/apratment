const roomModal = document.getElementById("roomModal");
const roomForm = document.getElementById("roomForm");
const roomRows = document.getElementById("roomRows");
const roomFilter = document.getElementById("roomFilter");
const filterMessage = document.getElementById("filterMessage");
const clearFilters = document.getElementById("clearFilters");
const addRoom = document.getElementById("addRoom");
const editRoom = document.getElementById("editRoom");
const deleteRoom = document.getElementById("deleteRoom");
const roomNotice = document.getElementById("roomNotice");
const roomModalTitle = document.getElementById("roomModalTitle");
const roomFormHelp = document.getElementById("roomFormHelp");
const saveRoom = document.querySelector('[type="submit"][form="roomForm"]');

let csrfToken = "";
let roomList = [];
let selectedRoom = null;
let editingRoom = null;

const modal = bootstrap.Modal.getOrCreateInstance(roomModal);

addRoom.removeAttribute("data-bs-toggle");
addRoom.removeAttribute("data-bs-target");

async function api(url, options = {}) {
    const settings = {
        credentials: "same-origin",
        cache: "no-store",
        ...options
    };

    settings.headers = {...(options.headers || {})};

    if (settings.body) {
        settings.headers["Content-Type"] = "application/json";
        settings.headers["X-CSRF-Token"] = csrfToken;
    }

    const response = await fetch(url, settings);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || "ทำรายการไม่สำเร็จ");
    }

    return data;
}

function showMessage(text, error = false) {
    filterMessage.textContent = text;
    filterMessage.classList.toggle("text-danger", error);
}

function setSelected(room) {
    selectedRoom = room;
    editRoom.disabled = !room;
    deleteRoom.disabled = !room;
}

function renderRooms() {
    roomRows.replaceChildren();

    if (roomList.length === 0) {
        const row = roomRows.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 7;
        cell.className = "text-center text-muted py-4";
        cell.textContent = "ไม่พบข้อมูลห้องพัก";
        return;
    }

    const statusText = {
        AVAILABLE: "ว่าง",
        OCCUPIED: "มีผู้เช่า",
        MAINTENANCE: "ปิดปรับปรุง"
    };

    const statusClass = {
        AVAILABLE: "text-bg-success",
        OCCUPIED: "text-bg-secondary",
        MAINTENANCE: "text-bg-warning"
    };

    roomList.forEach(room => {
        const row = roomRows.insertRow();

        const selectCell = row.insertCell();
        selectCell.className = "text-center";

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "selectedRoom";
        radio.className = "form-check-input";
        radio.addEventListener("change", () => setSelected(room));
        selectCell.appendChild(radio);

        row.insertCell().textContent = room.room_number;
        row.insertCell().textContent = room.floor;
        row.insertCell().textContent = room.room_type;

        const rentCell = row.insertCell();
        rentCell.className = "text-end";
        rentCell.textContent = Number(room.monthly_rent).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });

        const depositCell = row.insertCell();
        depositCell.className = "text-end";
        depositCell.textContent = Number(room.deposit_amount).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });

        const statusCell = row.insertCell();
        const badge = document.createElement("span");
        badge.className = `badge ${statusClass[room.status] || "text-bg-secondary"}`;
        badge.textContent = statusText[room.status] || room.status;
        statusCell.appendChild(badge);
    });
}

async function loadRooms(message = "") {
    setSelected(null);
    showMessage("กำลังโหลดข้อมูลห้องพัก...");

    const params = new URLSearchParams();
    const search = document.getElementById("searchRoom").value.trim();
    const floor = document.getElementById("floorFilter").value.trim();
    const status = document.getElementById("statusFilter").value;

    if (search) params.set("q", search);
    if (floor) params.set("floor", floor);
    if (status) params.set("status", status);

    try {
        const data = await api(`/api/rooms?${params.toString()}`);
        roomList = data.items || [];
        renderRooms();

        if (message) {
            showMessage(`${message} พบ ${roomList.length} รายการ`);
        } else {
            showMessage(`พบ ${roomList.length} รายการ`);
        }
    } catch (error) {
        roomList = [];
        renderRooms();
        showMessage(error.message, true);
    }
}

function openRoomForm(room = null) {
    roomForm.reset();
    roomNotice.hidden = true;
    roomNotice.textContent = "";
    editingRoom = room;

    roomModalTitle.textContent = room ? "แก้ไขห้องพัก" : "เพิ่มห้องพัก";
    roomFormHelp.textContent = "กรอกข้อมูลแล้วกดบันทึกเพื่อบันทึกลงฐานข้อมูล";

    if (room) {
        document.getElementById("roomId").value = room.room_id;
        document.getElementById("roomNumber").value = room.room_number;
        document.getElementById("roomFloor").value = room.floor;
        document.getElementById("roomType").value = room.room_type;
        document.getElementById("roomStatus").value = room.status;
        document.getElementById("monthlyRent").value = room.monthly_rent;
        document.getElementById("depositAmount").value = room.deposit_amount;
        document.getElementById("roomDescription").value = room.description || "";
    }

    modal.show();
}

addRoom.addEventListener("click", () => openRoomForm());

editRoom.addEventListener("click", function () {
    if (selectedRoom) {
        openRoomForm(selectedRoom);
    }
});

deleteRoom.addEventListener("click", async function () {
    if (!selectedRoom) return;

    if (!confirm(`ยืนยันลบห้อง ${selectedRoom.room_number}?`)) {
        return;
    }

    try {
        const data = await api(`/api/rooms/${selectedRoom.room_id}`, {
            method: "DELETE",
            body: JSON.stringify({})
        });

        await loadRooms(data.message);
    } catch (error) {
        showMessage(error.message, true);
    }
});

roomForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (!roomForm.reportValidity()) {
        return;
    }

    const body = Object.fromEntries(new FormData(roomForm));
    roomNotice.hidden = true;
    saveRoom.disabled = true;

    try {
        const data = await api(
            editingRoom ? `/api/rooms/${editingRoom.room_id}` : "/api/rooms",
            {
                method: editingRoom ? "PUT" : "POST",
                body: JSON.stringify(body)
            }
        );

        modal.hide();
        await loadRooms(data.message);
    } catch (error) {
        roomNotice.className = "alert alert-danger mt-3 mb-0";
        roomNotice.textContent = error.message;
        roomNotice.hidden = false;
    } finally {
        saveRoom.disabled = false;
    }
});

roomFilter.addEventListener("submit", function (event) {
    event.preventDefault();
    loadRooms();
});

clearFilters.addEventListener("click", function () {
    roomFilter.reset();
    loadRooms();
});

async function start() {
    try {
        const data = await api("/api/csrf");
        csrfToken = data.token;
        await loadRooms();
    } catch (error) {
        showMessage(error.message, true);
    }
}

start();