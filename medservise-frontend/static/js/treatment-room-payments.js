document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    const roomList = document.getElementById("room-list");
    let currentFilter = "all";

    function loadPayments() {
        fetch("http://localhost:8000/api/v1/treatment-room-payments/", {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((res) => res.json())
            .then((data) => {
                roomList.innerHTML = "";

                data.forEach((room) => {
                    const roomDiv = document.createElement("div");
                    roomDiv.classList.add("card", "mb-3", "p-3");

                    const filteredPatients = room.patients.filter((p) => {
                        if (currentFilter === "all") return true;
                        if (currentFilter === "prepaid") return p.total_paid > p.expected;
                        if (currentFilter === "paid") return p.total_paid >= p.expected;
                        if (currentFilter === "unpaid") return p.total_paid === 0;
                        return false;
                    });

                    let patientsHTML = "";
                    filteredPatients.forEach((p) => {
                        const isPrepaid = p.total_paid > p.expected;
                        const statusStr = isPrepaid ? "OLDINDAN TO‘LANGAN" : (p.status ? p.status.toUpperCase() : "NOMA'LUM");
                        const statusColor = isPrepaid
                            ? "text-info"
                            : p.status === "paid"
                                ? "text-success"
                                : p.status === "partial"
                                    ? "text-warning"
                                    : "text-danger";

                        let paymentHistory = "<ul class='payment-history d-none'>";
                        p.payments.forEach((pay) => {
                            paymentHistory += `<li>${pay.amount} so'm (${new Date(pay.date).toLocaleString()}) — <i>${pay.status}</i><br>${pay.notes || ''}</li>`;
                        });
                        paymentHistory += "</ul>";

                        patientsHTML += `
              <div class="border rounded p-2 mb-2">
                <strong>${p.first_name} ${p.last_name}</strong>
                <p>Holati: <span class="${statusColor}">${statusStr}</span></p>
                <p>To‘langan: ${p.total_paid} so'm / ${p.expected} so'm</p>

                <button class="btn btn-outline-secondary btn-sm toggle-payment-form mb-2">▾ To‘lov qo‘shish</button>
                <button class="btn btn-outline-info btn-sm toggle-payment-history mb-2 ms-2">▾ To‘lov tarixi</button>

                <form class="payment-form d-none" data-patient-id="${p.id}">
                  <input type="number" step="0.01" placeholder="Miqdorni kiriting" class="form-control mb-1" required>
                  <select class="form-select mb-1" required>
                    <option value="paid">To‘landi</option>
                  </select>
                  <select name="payment_method" class="form-select mb-1" required>
                    <option value="cash">Naqd</option>
                    <option value="card">Karta</option>
                    <option value="insurance">Sug‘urta</option>
                    <option value="transfer">Bank o‘tkazmasi</option>
                  </select>
                  <textarea class="form-control mb-1" placeholder="Izoh (ixtiyoriy)"></textarea>
                  <button type="submit" class="btn btn-sm btn-primary">➕ To‘lovni qo‘shish</button>
                </form>

                ${paymentHistory}
              </div>
            `;
                    });

                    roomDiv.innerHTML = `
            <h5>${room.name} (Qavat ${room.floor})</h5>
            ${patientsHTML || "<p>Ushbu filtr uchun bemorlar yo‘q.</p>"}
          `;
                    roomList.appendChild(roomDiv);
                });

                attachHandlers();
            })
            .catch((err) => {
                console.error("❌ To‘lov ma'lumotlarini yuklab bo‘lmadi", err);
                roomList.innerHTML = "<p class='text-danger'>❌ To‘lov ma'lumotlarini yuklab bo‘lmadi</p>";
            });
    }

    function attachHandlers() {
        document.querySelectorAll(".toggle-payment-form").forEach((btn) => {
            btn.addEventListener("click", () => {
                const parentDiv = btn.closest("div.border");
                const form = parentDiv?.querySelector(".payment-form");
                if (form) form.classList.toggle("d-none");
            });
        });

        document.querySelectorAll(".toggle-payment-history").forEach((btn) => {
            btn.addEventListener("click", () => {
                const parentDiv = btn.closest("div.border");
                const history = parentDiv?.querySelector(".payment-history");
                if (history) history.classList.toggle("d-none");
            });
        });

        document.querySelectorAll(".payment-form").forEach((form) => {
            form.addEventListener("submit", (e) => {
                e.preventDefault();
                const patientId = form.dataset.patientId;
                const amount = parseFloat(form.querySelector("input").value);
                const status = form.querySelector("select").value;
                const notes = form.querySelector("textarea").value;
                const paymentMethod = form.querySelector("select[name='payment_method']").value;

                if (!amount || amount <= 0) {
                    alert("Iltimos, to‘g‘ri miqdorni kiriting");
                    return;
                }

                fetch("http://localhost:8000/api/v1/treatment-room-payments/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        patient: patientId,
                        amount,
                        status,
                        notes,
                        payment_method: paymentMethod,
                    }),
                })
                    .then((res) => {
                        if (!res.ok) throw new Error("To‘lovni saqlashda xatolik");
                        return res.json();
                    })
                    .then((data) => {
                        alert("✅ To‘lov muvaffaqiyatli qo‘shildi");

                        // 👇 Call backend to print
                        fetch("http://localhost:8000/api/v1/treatment-room-payments/room-print/", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                Authorization: `Bearer ${token}`,
                            },
                            body: JSON.stringify({ payment_id: data.id }),
                        })
                            .then((res) => {
                                if (!res.ok) throw new Error("❌ Kvitansiyani chop etib bo‘lmadi");
                                console.log("🖨️ Chek printerga yuborildi");
                            })
                            .catch((err) => {
                                console.error("❌ Chop etishda xatolik", err);
                            });

                        loadPayments();
                    })
                    .catch((err) => {
                        console.error("❌ To‘lovda xatolik", err);
                        alert("❌ To‘lovni qo‘shishda xatolik yuz berdi");
                    });
            });
        });
    }

    document.querySelectorAll("#payment-filter-tabs .nav-link").forEach((tab) => {
        tab.addEventListener("click", (e) => {
            e.preventDefault();
            document.querySelectorAll("#payment-filter-tabs .nav-link").forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            currentFilter = tab.dataset.filter;
            loadPayments();
        });
    });

    loadPayments();
});
