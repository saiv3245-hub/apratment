const employeeModal = document.getElementById("employeeModal");
const employeeForm = document.getElementById("employeeForm");
const employeeRows = document.getElementById("employeeRows");
const employeeMessage = document.getElementById("employeeMessage");
const employeeNotice = document.getElementById("employeeNotice");
const employeeUser = document.getElementById("employeeUser");
const employeeModalTitle = document.getElementById("employeeModalTitle");
const addEmployee = document.getElementById("addEmployee");
const editEmployee = document.getElementById("editEmployee");
const deleteEmployee = document.getElementById("deleteEmployee");

let csrfToken = "";
let employees = [];
let selectedEmployee = null;
let editingEmployee = null;

const modal = bootstrap.Modal.getOrCreateInstance(employeeModal);

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

function selectEmployee(employee) {
    selectedEmployee = employee;
    editEmployee.disabled = !employee;
    deleteEmployee.disabled = !employee;
}

function renderEmployees() {
    employeeRows.replaceChildren();

    if (employees.length === 0) {
        const row = employeeRows.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 7;
        cell.className = "text-center text-muted py-4";
        cell.textContent = "ไม่พบข้อมูลพนักงาน";
        return;
    }

    employees.forEach(employee => {
        const row = employeeRows.insertRow();
        const selectCell = row.insertCell();
        selectCell.className = "text-center";

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "selectedEmployee";
        radio.className = "form-check-input";
        radio.addEventListener("change", () => selectEmployee(employee));
        selectCell.appendChild(radio);

        row.insertCell().textContent = employee.employees_code;
        row.insertCell().textContent = `${employee.first_name} ${employee.last_name}`;
        row.insertCell().textContent = employee.position;
        row.insertCell().textContent = employee.phone;
        row.insertCell().textContent = employee.user_name || "—";

        const statusCell = row.insertCell();
        const badge = document.createElement("span");
        badge.className = employee.employment_status === "ACTIVE"
            ? "badge text-bg-success"
            : "badge text-bg-secondary";
        badge.textContent = employee.employment_status === "ACTIVE"
            ? "ทำงาน"
            : "ไม่ใช้งาน";
        statusCell.appendChild(badge);
    });
}

async function loadEmployees(message = "") {
    selectEmployee(null);
    employeeMessage.textContent = "กำลังโหลดข้อมูล...";
    employeeMessage.classList.remove("text-danger");

    const params = new URLSearchParams();
    const search = document.getElementById("searchEmployee").value.trim();
    const status = document.getElementById("employeeStatusFilter").value;

    if (search) params.set("q", search);
    if (status) params.set("status", status);

    try {
        const data = await api(`/api/employees?${params.toString()}`);
        employees = data.items || [];
        renderEmployees();
        employeeMessage.textContent = message
            ? `${message} พบ ${employees.length} รายการ`
            : `พบ ${employees.length} รายการ`;
    } catch (error) {
        employees = [];
        renderEmployees();
        employeeMessage.textContent = error.message;
        employeeMessage.classList.add("text-danger");
    }
}

async function loadEmployeeUsers(employeeId = 0, currentUserId = "") {
    employeeUser.disabled = true;
    employeeUser.innerHTML = '<option value="">กำลังโหลดบัญชี...</option>';

    const data = await api(`/api/employee-users?employee_id=${employeeId}`);

    employeeUser.replaceChildren();
    const first = document.createElement("option");
    first.value = "";
    first.textContent = "เลือกบัญชีผู้ใช้งาน";
    employeeUser.appendChild(first);

    data.items.forEach(user => {
        const option = document.createElement("option");
        option.value = user.user_id;
        option.textContent = user.user_name;
        employeeUser.appendChild(option);
    });

    if (currentUserId) {
        employeeUser.value = String(currentUserId);
    }

    if (employeeUser.options.length === 1) {
        first.textContent = "ไม่มีบัญชีพนักงานที่ยังไม่ได้เชื่อม";
        employeeUser.disabled = true;
    } else {
        employeeUser.disabled = false;
    }
}

async function openEmployeeForm(employee = null) {
    employeeForm.reset();
    employeeNotice.hidden = true;
    editingEmployee = employee;
    employeeModalTitle.textContent = employee ? "แก้ไขพนักงาน" : "เพิ่มพนักงาน";
    modal.show();

    try {
        if (!employee) {
            await loadEmployeeUsers();
            return;
        }

        const data = await api(`/api/employees/${employee.employees_id}`);
        editingEmployee = data.item;
        await loadEmployeeUsers(editingEmployee.employees_id, editingEmployee.user_id);

        Object.entries(editingEmployee).forEach(([key, value]) => {
            const field = employeeForm.elements.namedItem(key);
            if (field) field.value = value == null ? "" : String(value);
        });
    } catch (error) {
        employeeNotice.className = "alert alert-danger mt-3 mb-0";
        employeeNotice.textContent = error.message;
        employeeNotice.hidden = false;
    }
}

addEmployee.addEventListener("click", () => openEmployeeForm());

editEmployee.addEventListener("click", () => {
    if (selectedEmployee) openEmployeeForm(selectedEmployee);
});

deleteEmployee.addEventListener("click", async () => {
    if (!selectedEmployee) return;
    if (!confirm(`ยืนยันลบพนักงาน ${selectedEmployee.employees_code}?`)) return;

    try {
        const data = await api(`/api/employees/${selectedEmployee.employees_id}`, {
            method: "DELETE",
            body: JSON.stringify({})
        });
        await loadEmployees(data.message);
    } catch (error) {
        employeeMessage.textContent = error.message;
        employeeMessage.classList.add("text-danger");
    }
});

employeeForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!employeeForm.reportValidity()) return;

    if (employeeUser.disabled || !employeeUser.value) {
        employeeNotice.className = "alert alert-danger mt-3 mb-0";
        employeeNotice.textContent = "กรุณาเลือกบัญชีผู้ใช้งาน";
        employeeNotice.hidden = false;
        return;
    }

    try {
        const data = await api(
            editingEmployee
                ? `/api/employees/${editingEmployee.employees_id}`
                : "/api/employees",
            {
                method: editingEmployee ? "PUT" : "POST",
                body: JSON.stringify(Object.fromEntries(new FormData(employeeForm)))
            }
        );

        modal.hide();
        await loadEmployees(data.message);
    } catch (error) {
        employeeNotice.className = "alert alert-danger mt-3 mb-0";
        employeeNotice.textContent = error.message;
        employeeNotice.hidden = false;
    }
});

document.getElementById("employeeFilter").addEventListener("submit", event => {
    event.preventDefault();
    loadEmployees();
});

document.getElementById("clearEmployeeFilters").addEventListener("click", () => {
    document.getElementById("employeeFilter").reset();
    loadEmployees();
});

(async function start() {
    try {
        csrfToken = (await api("/api/csrf")).token;
        await loadEmployees();
    } catch (error) {
        employeeMessage.textContent = error.message;
        employeeMessage.classList.add("text-danger");
    }
})();