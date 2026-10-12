const maintenanceModal = document.getElementById("maintenanceModal");
const maintenanceForm = document.getElementById("maintenanceForm");
const maintenanceRows = document.getElementById("maintenanceRows");
const maintenanceMessage = document.getElementById("maintenanceMessage");
const maintenanceNotice = document.getElementById("maintenanceNotice");
const maintenanceModalTitle = document.getElementById("maintenanceModalTitle");

let csrfToken = "";
let maintenanceItems = [];
let selectedMaintenance = null;
let editingMaintenance = null;

const modal = bootstrap.Modal.getOrCreateInstance(maintenanceModal);

async function api(url, options = {}) {
    const settings = {credentials: "same-origin", cache: "no-store", ...options};
    settings.headers = {...(options.headers || {})};

    if (settings.body) {
        settings.headers["Content-Type"] = "application/json";
        settings.headers["X-CSRF-Token"] = csrfToken;
    }

    const response = await fetch(url, settings);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) throw new Error(data.error || "ทำรายการไม่สำเร็จ");
    return data;
}

function selectMaintenance(item) {
    selectedMaintenance = item;
    document.getElementById("editMaintenance").disabled = !item;
    document.getElementById("deleteMaintenance").disabled = !item;
}

function renderMaintenance() {
    maintenanceRows.replaceChildren();

    if (!maintenanceItems.length) {
        maintenanceRows.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">ไม่พบรายการแจ้งซ่อม</td></tr>';
        return;
    }

    const priorityText = {
        LOW: "ต่ำ",
        NORMAL: "ปกติ",
        HIGH: "สูง",
        URGENT: "ด่วน"
    };

    const statusText = {
        PENDING: "รอดำเนินการ",
        IN_PROGRESS: "กำลังดำเนินการ",
        COMPLETED: "เสร็จสิ้น",
        CANCELLED: "ยกเลิก"
    };

    maintenanceItems.forEach(item => {
        const row = maintenanceRows.insertRow();
        const selectCell = row.insertCell();
        selectCell.className = "text-center";

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "selectedMaintenance";
        radio.className = "form-check-input";
        radio.addEventListener("change", () => selectMaintenance(item));
        selectCell.appendChild(radio);

        row.insertCell().textContent = item.request_number;
        row.insertCell().textContent = item.room_number;
        row.insertCell().textContent = item.tenant_name;
        row.insertCell().textContent = item.title;
        row.insertCell().textContent = priorityText[item.priority] || item.priority;
        row.insertCell().textContent = item.employee_name || "ยังไม่มอบหมาย";
        row.insertCell().textContent = statusText[item.status] || item.status;
    });
}

async function loadMaintenance(message = "") {
    selectMaintenance(null);
    const params = new URLSearchParams();

    const search = document.getElementById("searchMaintenance").value.trim();
    const status = document.getElementById("maintenanceStatusFilter").value;

    if (search) params.set("q", search);
    if (status) params.set("status", status);

    try {
        const data = await api(`/api/maintenance?${params.toString()}`);
        maintenanceItems = data.items || [];
        renderMaintenance();

        maintenanceMessage.textContent = message
            ? `${message} พบ ${maintenanceItems.length} รายการ`
            : `พบ ${maintenanceItems.length} รายการ`;
    } catch (error) {
        maintenanceMessage.textContent = error.message;
        maintenanceMessage.classList.add("text-danger");
    }
}

function fillSelect(id, firstText, items, valueKey, textFunction) {
    const select = document.getElementById(id);
    select.replaceChildren();

    const first = document.createElement("option");
    first.value = "";
    first.textContent = firstText;
    select.appendChild(first);

    items.forEach(item => {
        const option = document.createElement("option");
        option.value = item[valueKey];
        option.textContent = textFunction(item);
        select.appendChild(option);
    });
}

async function loadOptions() {
    const data = await api("/api/maintenance/options");

    fillSelect(
        "maintenanceTenant",
        "เลือกผู้เช่า",
        data.tenants,
        "tenant_id",
        item => `${item.tenant_code} - ${item.first_name} ${item.last_name}`
    );

    fillSelect(
        "maintenanceRoom",
        "เลือกห้องพัก",
        data.rooms,
        "room_id",
        item => item.room_number
    );

    fillSelect(
        "maintenanceContract",
        "ไม่ระบุสัญญา",
        data.contracts,
        "contract_id",
        item => item.contract_number
    );

    fillSelect(
        "assignedEmployee",
        "ยังไม่มอบหมาย",
        data.employees,
        "employees_id",
        item => `${item.employees_code} - ${item.first_name} ${item.last_name}`
    );
}

async function openMaintenanceForm(item = null) {
    maintenanceForm.reset();
    maintenanceNotice.hidden = true;
    editingMaintenance = item;
    maintenanceModalTitle.textContent = item ? "แก้ไขแจ้งซ่อม" : "เพิ่มแจ้งซ่อม";
    modal.show();

    try {
        await loadOptions();

        if (!item) return;

        const data = await api(`/api/maintenance/${item.request_id}`);
        editingMaintenance = data.item;

        Object.entries(editingMaintenance).forEach(([key, value]) => {
            const field = maintenanceForm.elements.namedItem(key);
            if (field) field.value = value == null ? "" : String(value);
        });
    } catch (error) {
        maintenanceNotice.className = "alert alert-danger mt-3 mb-0";
        maintenanceNotice.textContent = error.message;
        maintenanceNotice.hidden = false;
    }
}

document.getElementById("addMaintenance").addEventListener("click", () => openMaintenanceForm());

document.getElementById("editMaintenance").addEventListener("click", () => {
    if (selectedMaintenance) openMaintenanceForm(selectedMaintenance);
});

document.getElementById("deleteMaintenance").addEventListener("click", async () => {
    if (!selectedMaintenance) return;
    if (!confirm(`ยืนยันลบ ${selectedMaintenance.request_number}?`)) return;

    try {
        const data = await api(`/api/maintenance/${selectedMaintenance.request_id}`, {
            method: "DELETE",
            body: JSON.stringify({})
        });
        await loadMaintenance(data.message);
    } catch (error) {
        maintenanceMessage.textContent = error.message;
        maintenanceMessage.classList.add("text-danger");
    }
});

maintenanceForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!maintenanceForm.reportValidity()) return;

    try {
        const data = await api(
            editingMaintenance
                ? `/api/maintenance/${editingMaintenance.request_id}`
                : "/api/maintenance",
            {
                method: editingMaintenance ? "PUT" : "POST",
                body: JSON.stringify(Object.fromEntries(new FormData(maintenanceForm)))
            }
        );

        modal.hide();
        await loadMaintenance(data.message);
    } catch (error) {
        maintenanceNotice.className = "alert alert-danger mt-3 mb-0";
        maintenanceNotice.textContent = error.message;
        maintenanceNotice.hidden = false;
    }
});

document.getElementById("maintenanceFilter").addEventListener("submit", event => {
    event.preventDefault();
    loadMaintenance();
});

document.getElementById("clearMaintenanceFilters").addEventListener("click", () => {
    document.getElementById("maintenanceFilter").reset();
    loadMaintenance();
});

(async function start() {
    csrfToken = (await api("/api/csrf")).token;
    await loadMaintenance();
})();