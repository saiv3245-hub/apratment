const reportMessage = document.getElementById("reportMessage");

async function api(url) {
    const response = await fetch(url, {
        credentials: "same-origin",
        cache: "no-store"
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || "โหลดรายงานไม่สำเร็จ");
    }
    return data;
}

function money(value) {
    return Number(value || 0).toLocaleString("th-TH", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

(async function loadReport() {
    try {
        const data = await api("/api/reports/summary");

        document.getElementById("reportRooms").textContent = data.rooms.total_rooms;
        document.getElementById("reportTenants").textContent = data.tenants.active_tenants;
        document.getElementById("reportContracts").textContent = data.contracts.active_contracts;
        document.getElementById("reportOutstanding").textContent =
            `${money(data.finance.outstanding_total)} บาท`;

        document.getElementById("roomSummaryRows").innerHTML = `
            <tr>
                <td>ห้องว่าง</td>
                <td class="text-end">${data.rooms.available_rooms}</td>
            </tr>
            <tr>
                <td>มีผู้เช่า</td>
                <td class="text-end">${data.rooms.occupied_rooms}</td>
            </tr>
            <tr>
                <td>ปิดปรับปรุง</td>
                <td class="text-end">${data.rooms.maintenance_rooms}</td>
            </tr>
        `;

        document.getElementById("financeSummaryRows").innerHTML = `
            <tr>
                <td>ยอดเรียกเก็บทั้งหมด</td>
                <td class="text-end">${money(data.finance.billed_total)} บาท</td>
            </tr>
            <tr>
                <td>รับชำระแล้ว</td>
                <td class="text-end">${money(data.finance.paid_total)} บาท</td>
            </tr>
            <tr>
                <td>ยอดค้าง</td>
                <td class="text-end">${money(data.finance.outstanding_total)} บาท</td>
            </tr>
            <tr>
                <td>ยังไม่ชำระ</td>
                <td class="text-end">${data.finance.unpaid_count}</td>
            </tr>
            <tr>
                <td>ชำระบางส่วน</td>
                <td class="text-end">${data.finance.partial_count}</td>
            </tr>
            <tr>
                <td>ชำระแล้ว</td>
                <td class="text-end">${data.finance.paid_count}</td>
            </tr>
        `;

        const repairRows = document.getElementById("repairSummaryRows");
        repairRows.replaceChildren();

        if (!data.repairs.length) {
            repairRows.innerHTML =
                '<tr><td colspan="2" class="text-center text-muted">ไม่มีข้อมูล</td></tr>';
        } else {
            const statusText = {
                PENDING: "รอดำเนินการ",
                IN_PROGRESS: "กำลังดำเนินการ",
                COMPLETED: "เสร็จสิ้น",
                CANCELLED: "ยกเลิก"
            };

            data.repairs.forEach(item => {
                const row = repairRows.insertRow();
                row.insertCell().textContent = statusText[item.status] || item.status;

                const count = row.insertCell();
                count.className = "text-end";
                count.textContent = item.count;
            });
        }

        const monthlyRows = document.getElementById("monthlySummaryRows");
        monthlyRows.replaceChildren();

        if (!data.monthly.length) {
            monthlyRows.innerHTML =
                '<tr><td colspan="3" class="text-center text-muted">ไม่มีข้อมูล</td></tr>';
        } else {
            data.monthly.forEach(item => {
                const row = monthlyRows.insertRow();
                row.insertCell().textContent = item.month;

                const billed = row.insertCell();
                billed.className = "text-end";
                billed.textContent = `${money(item.billed)} บาท`;

                const paid = row.insertCell();
                paid.className = "text-end";
                paid.textContent = `${money(item.paid)} บาท`;
            });
        }

        reportMessage.textContent = "อัปเดตรายงานจากฐานข้อมูลเรียบร้อย";
    } catch (error) {
        reportMessage.textContent = error.message;
        reportMessage.classList.add("text-danger");
    }
})();