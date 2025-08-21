document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    const refresh = localStorage.getItem("refresh");
    const roomList = document.getElementById("room-list");
    let currentFilter = "all";
    const apiBase = "http://89.39.95.150/api/v1";

    if (!token) {
        console.error("No token found in localStorage");
        alert("Iltimos, avval tizimga kiring");
        window.location.href = "/login.html";
        return;
    }

    // Token refresh function
    async function refreshToken() {
        if (!refresh) {
            console.error("No refresh token found in localStorage");
            alert("Iltimos, qayta tizimga kiring");
            window.location.href = "/login.html";
            return null;
        }
        try {
            const res = await fetch(`${apiBase}/token/refresh/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh })
            });
            if (!res.ok) throw new Error(`Tokenni yangilashda xatolik: ${res.status}`);
            const data = await res.json();
            localStorage.setItem("token", data.access);
            console.log("Token refreshed successfully");
            return data.access;
        } catch (err) {
            console.error("Token refresh failed:", err);
            alert("Iltimos, qayta tizimga kiring");
            window.location.href = "/login.html";
            return null;
        }
    }

    // Authenticated fetch with token refresh
    async function authFetch(url, options = {}) {
        options.headers = options.headers || {};
        options.headers["Content-Type"] = "application/json";
        options.headers["Authorization"] = `Bearer ${token}`;

        console.log("Making request to:", url, "with headers:", options.headers); // Debug
        let res = await fetch(url, options);
        if (res.status === 401) {
            console.warn("Received 401, attempting to refresh token");
            const newToken = await refreshToken();
            if (newToken) {
                options.headers["Authorization"] = `Bearer ${newToken}`;
                res = await fetch(url, options);
            }
        }
        return res;
    }

    function formatCurrency(amount) {
        return `${parseFloat(amount).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ".")} so'm`;
    }

    async function fetchPatientData(patientId) {
        try {
            const res = await authFetch(`${apiBase}/patients/${patientId}/`);
            if (!res.ok) throw new Error(`Failed to fetch patient: ${res.status}`);
            const data = await res.json();
            return {
                patient_name: `${data.first_name || ''} ${data.last_name || ''}`.trim() || 'Unknown',
                doctor_name: data.patients_doctor ? `${data.patients_doctor.first_name} ${data.patients_doctor.last_name}`.trim() : 'Unknown'
            };
        } catch (err) {
            console.error("Failed to fetch patient data:", err);
            return { patient_name: 'Unknown', doctor_name: 'Unknown' };
        }
    }

    function loadPayments() {
        authFetch(`${apiBase}/treatment-room-payments/`)
            .then((res) => {
                if (!res.ok) throw new Error(`Failed to load payments: ${res.status}`);
                return res.json();
            })
            .then((data) => {
                console.log('Payments Data:', data); // Debug
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
                            paymentHistory += `<li>${formatCurrency(pay.amount)} (${new Date(pay.date).toLocaleString()}) — <i>${pay.status}</i><br>${pay.notes || ''}</li>`;
                        });
                        paymentHistory += "</ul>";

                        patientsHTML += `
                            <div class="border rounded p-2 mb-2" data-patient-id="${p.id}" data-patient-name="${p.first_name} ${p.last_name}">
                                <strong>${p.first_name} ${p.last_name}</strong>
                                <p>Holati: <span class="${statusColor}">${statusStr}</span></p>
                                <p>To‘langan: ${formatCurrency(p.total_paid)} / ${formatCurrency(p.expected)}</p>

                                <button class="btn btn-outline-secondary btn-sm toggle-payment-form mb-2">▾ To‘lov qo‘shish</button>
                                <button class="btn btn-outline-info btn-sm toggle-payment-history mb-2 ms-2">▾ To‘lov tarixi</button>

                                <form class="payment-form d-none" data-patient-id="${p.id}">
                                    <input type="number" step="0.01" placeholder="Miqdorni kiriting" class="form-control mb-1" required>
                                    <select class="form-select mb-1" required>
                                        <option value="paid">To‘landi</option>
                                        <option value="partial">Qisman</option>
                                        <option value="unpaid">To‘lanmagan</option>
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
                        <h5>${room.name} (Blok ${room.floor})</h5>
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
            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                const patientId = form.dataset.patientId;
                const amount = parseFloat(form.querySelector("input").value);
                const status = form.querySelector("select").value;
                const paymentMethod = form.querySelector("select[name='payment_method']").value;
                const notes = form.querySelector("textarea").value;
                const patientName = form.closest("div.border").dataset.patientName || 'Unknown';

                if (!amount || amount <= 0) {
                    alert("Iltimos, to‘g‘ri miqdorni kiriting");
                    return;
                }

                try {
                    const res = await authFetch(`${apiBase}/treatment-room-payments/`, {
                        method: "POST",
                        body: JSON.stringify({
                            patient: patientId,
                            amount,
                            status,
                            payment_method: paymentMethod,
                            notes,
                            transaction_type: "treatment"
                        }),
                    });
                    if (!res.ok) throw new Error(`To‘lovni saqlashda xatolik: ${res.status}`);
                    const data = await res.json();
                    console.log('Payment Creation Response:', data); // Debug

                    alert("✅ To‘lov muvaffaqiyatli qo‘shildi");

                    // Fetch processed_by from user info
                    let processedBy = 'System';
                    try {
                        const userRes = await authFetch(`${apiBase}/user-profile/`);
                        if (userRes.ok) {
                            const userData = await userRes.json();
                            processedBy = userData.full_name || userData.email || 'System';
                        }
                    } catch (err) {
                        console.error("Failed to fetch user profile:", err);
                    }

                    // Fetch patient and doctor data
                    const { patient_name } = await fetchPatientData(patientId);

            	    const decodedPatientName = `'${decodeURIComponent(patient_name || 'Unknown')}'`;


            	    const receiptDate = new Date(data.date || new Date()).toLocaleString('uz-UZ', {
                	timeZone: 'Asia/Tashkent',
                	year: 'numeric',
                	month: '2-digit',
                	day: '2-digit',
                	hour: '2-digit',
                	minute: '2-digit'
            	    });


                    // Open receipt popup with token and payment data
                    const url = new URL(`/static/treatment_room_receipt_popup/receipt.html`, window.location.origin);
                    url.searchParams.set('payment_id', data.id);
                    url.searchParams.set('token', encodeURIComponent(localStorage.getItem("token") || ''));
		    url.searchParams.set('patient_name', decodedPatientName);
                    url.searchParams.set('amount', amount);
                    url.searchParams.set('status', status);
                    url.searchParams.set('payment_method', paymentMethod);
                    url.searchParams.set('notes', notes);
	            url.searchParams.set('date', receiptDate);
		    url.searchParams.set('processed_by', processedBy);


                    console.log('Opening receipt popup with URL:', url.toString()); // Debug
                    const printPopup = window.open(url, "_blank", "width=400,height=600");
                    if (!printPopup) {
                        alert("❌ Popup bloklangan. Iltimos, brauzeringizda popupga ruxsat bering.");
                    } else {
                        printPopup.focus();
                    }

                    loadPayments();
                } catch (err) {
                    console.error("❌ To‘lovda xatolik", err);
                    alert(`❌ To‘lovni qo‘shishda xatolik yuz berdi: ${err.message}`);
                }
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
