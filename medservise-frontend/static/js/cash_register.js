class CashRegister {
    constructor() {
        this.token = localStorage.getItem("token");
        this.refresh = localStorage.getItem("refresh");
        this.apiBase = "http://89.39.95.150/api/v1";

        if (!this.token) {
            alert("Iltimos, avval tizimga kiring");
            window.location.href = "/login.html";
        } else {
            this.init();
        }
    }

    async init() {
        document.getElementById("days-filter")?.addEventListener("change", (e) => {
            this.loadRecentPatients(e.target.value);
        });

        await this.loadServices();
        await this.loadRecentPatients(3);

        document.getElementById("cash-form")?.addEventListener("submit", (e) => this.submitPayment(e));
        document.getElementById("transaction_type")?.addEventListener("change", (e) => this.toggleServiceSelect(e.target.value));
    }

    formatAmount(amount) {
        return Number(amount).toLocaleString("uz-UZ").replace(/,/g, ".");
    }

    formatCurrency(amount) {
        return `${parseFloat(amount).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ".")} so'm`;
    }

    async loadServices() {
        try {
            const res = await this.authFetch(`${this.apiBase}/services/`);
            if (!res.ok) throw new Error("Xizmatlar roʻyxatini yuklab boʻlmadi");
            const services = await res.json();

            const serviceButtons = document.getElementById("service-buttons");
            serviceButtons.innerHTML = "";

            services.forEach(service => {
                const btn = document.createElement("button");
                btn.className = "btn btn-outline-primary btn-sm";
                btn.textContent = `${service.name} (${this.formatAmount(service.price)} so'm)`;
                btn.dataset.id = service.id;
                btn.dataset.price = service.price;

                btn.addEventListener("click", () => {
                    btn.classList.toggle("btn-primary");
                    btn.classList.toggle("btn-outline-primary");
                    this.updateAmountFromServices();
                });

                serviceButtons.appendChild(btn);
            });
        } catch (err) {
            console.error("Xizmatlar yuklashda xatolik:", err);
        }
    }

    updateAmountFromServices() {
        const selectedButtons = Array.from(document.querySelectorAll("#service-buttons .btn.btn-primary"));
        const total = selectedButtons.reduce((sum, btn) => sum + parseFloat(btn.dataset.price), 0);
        document.getElementById("amount").value = total.toFixed(2);
    }

    toggleServiceSelect(type) {
        const container = document.getElementById("multi-service-container");
        container.style.display = type === "service" ? "block" : "none";
    }

    async authFetch(url, options = {}) {
        options.headers = options.headers || {};
        options.headers["Content-Type"] = "application/json";
        options.headers["Authorization"] = `Bearer ${this.token}`;

        let res = await fetch(url, options);
        if (res.status === 401) {
            const newToken = await this.refreshToken();
            if (newToken) {
                options.headers["Authorization"] = `Bearer ${newToken}`;
                res = await fetch(url, options);
            }
        }
        return res;
    }

    async refreshToken() {
        if (!this.refresh) {
            this.logout();
            return null;
        }
        try {
            const res = await fetch(`${this.apiBase}/token/refresh/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh: this.refresh })
            });
            const data = await res.json();
            localStorage.setItem("token", data.access);
            this.token = data.access;
            return data.access;
        } catch {
            this.logout();
        }
    }

    logout() {
        localStorage.removeItem("token");
        localStorage.removeItem("refresh");
        window.location.href = "/login.html";
    }

    async loadRecentPatients(days = 3) {
        try {
            const res = await this.authFetch(`${this.apiBase}/recent-patients/?days=${days}`);
            const patients = await res.json();

            const list = document.getElementById("patient-list");
            list.innerHTML = "";

            patients.forEach(p => {
                if (!p || !p.first_name || !p.last_name || !p.phone) return;

                const info = p.patients_doctor?.user
                    ? `Shifokor: ${p.patients_doctor.user.first_name} ${p.patients_doctor.user.last_name}`
                    : p.patients_service
                        ? `Xizmat: ${p.patients_service.name}`
                        : "Biriktirilmagan";

                const li = document.createElement("li");
                li.className = "list-group-item list-group-item-action";
                li.innerHTML = `<strong>${p.first_name} ${p.last_name}</strong> (${p.phone})<br><small class="text-muted">${info}</small>`;
                li.addEventListener("click", () => this.selectPatient(p.id));
                list.appendChild(li);
            });

        } catch (err) {
            console.error("❌ Bemorlar ro'yxatini yuklashda xatolik:", err);
        }
    }

    async selectPatient(patientId) {
        try {
            const res = await this.authFetch(`${this.apiBase}/cash-register/patient/${patientId}/`);
            const data = await res.json();

            const { patient, balance, total_paid } = data.summary || {};
            if (!patient) throw new Error("Bemor ma'lumotlari xato");

            document.getElementById("patient").value = patientId;
            document.getElementById("patient-id-display").textContent = patientId;
            document.getElementById("patient-name").textContent = patient.name;
            document.getElementById("patient-phone").textContent = patient.phone;
            document.getElementById("balance").textContent = `${this.formatAmount(balance || 0)} so'm`;
            document.getElementById("total-paid").textContent = `${this.formatAmount(total_paid || 0)} so'm`;

            document.getElementById("assigned-doctor").textContent = patient.patients_doctor?.user
                ? `${patient.patients_doctor.user.first_name} ${patient.patients_doctor.user.last_name}`
                : "—";

            document.getElementById("assigned-service").textContent = patient.patients_service
                ? `${patient.patients_service.name} (${this.formatAmount(patient.patients_service.price)} so'm)`
                : "—";

            const txType = patient.patients_doctor ? "consultation" : "service";
            document.getElementById("transaction_type").value = txType;
            this.toggleServiceSelect(txType);

            const amountField = document.getElementById("amount");
            amountField.value = parseFloat(txType === "consultation" ? balance || 0 : patient.patients_service?.price || 0).toFixed(2);
            amountField.readOnly = true;

            this.renderTransactions(data.transactions);
        } catch (err) {
            console.error("❌ Bemorni yuklashda xatolik:", err);
            alert("❌ Bemor tafsilotlarini yuklab bo‘lmadi.");
        }
    }

    renderTransactions(transactions) {
        const typeMap = {
            consultation: "Konsultatsiya",
            treatment: "Davolash",
            service: "Xizmat",
            room: "Xona",
            other: "Boshqa"
        };

        const methodMap = {
            cash: "Naqd",
            card: "Karta",
            insurance: "Sug‘urta",
            transfer: "Bank"
        };

        const tbody = document.querySelector("#cash-register-table tbody");
        tbody.innerHTML = "";
        if (!transactions || transactions.length === 0) {
            tbody.innerHTML = "<tr><td colspan='7'>Hech qanday to‘lovlar topilmadi</td></tr>";
            return;
        }

        transactions.forEach(tx => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${tx.patient_name || "—"}</td>
                <td>${typeMap[tx.transaction_type] || tx.transaction_type}</td>
                <td>${tx.notes || "-"}</td>
                <td>${this.formatAmount(tx.amount)} so'm</td>
                <td>${methodMap[tx.payment_method] || tx.payment_method}</td>
                <td>${new Date(tx.created_at).toLocaleString()}</td>
            `;
            tbody.appendChild(row);
        });
    }

    async submitPayment(event) {
        event.preventDefault();

        const selectedServices = Array.from(document.querySelectorAll("#service-buttons .btn.btn-primary"))
            .map(btn => parseInt(btn.dataset.id));

        const data = {
            patient: parseInt(document.getElementById("patient").value),
            transaction_type: document.getElementById("transaction_type").value,
            amount: parseFloat(document.getElementById("amount").value),
            payment_method: document.getElementById("payment_method").value,
            notes: document.getElementById("notes").value
        };

        if (data.transaction_type === "service") {
            data.service_ids = selectedServices;
        }

        try {
            const res = await this.authFetch(`${this.apiBase}/cash-register/`, {
                method: "POST",
                body: JSON.stringify(data)
            });
            if (!res.ok) throw new Error("To‘lov muvaffaqiyatsiz");

            const result = await res.json();
            alert("✅ To‘lov muvaffiyatli bajarildi!");
            document.getElementById("cash-form").reset();

            this.selectPatient(data.patient);
            this.printReceipt(result.id);
        } catch (err) {
            console.error("❌ To‘lov xatosi:", err);
            alert("❌ To‘lovni yozib bo‘lmadi");
        }
    }



    
    async printReceipt(id) {
        try {
            const res = await this.authFetch(`${this.apiBase}/cash-register/receipt/${id}/`);
            if (!res.ok) throw new Error("Failed to fetch receipt");
            const data = await res.json();
    
            const lines = [];
            lines.push("NEURO PULS KLINIKASI");
            lines.push("-----------------------------");
            lines.push(`Chek raqami: ${data.receipt_number}`);
            lines.push(`Sana      : ${data.date}`);
            lines.push(`Bemor     : ${data.patient_name}`);
            lines.push(`Turi      : ${data.transaction_type}`);
            lines.push(`Miqdori   : ${this.formatCurrency(data.amount)}`);
            lines.push(`Usul      : ${data.payment_method}`);
            lines.push(`Qabulchi  : ${data.processed_by}`);
            if (data.notes) lines.push(`Izoh      : ${data.notes}`);
            lines.push("-----------------------------");
            lines.push("Rahmat! Kuningiz yaxshi otsin!");
    
            const qzReceiptText = lines.join("\n") + "\n\n\n\n\n\n\n\n\n\n";
            const browserReceiptText = lines.join("\n\n").trim();
    
            // Generate QR code base64
            let qrImageData = null;
            try {
                const qrContent = `${window.location.origin}/cash-register/receipt/${id}/`;
                const qrDataURL = await QRCode.toDataURL(qrContent); // base64 image
                qrImageData = qrDataURL.split(",")[1]; // remove "data:image/png;base64,"
            } catch (qrErr) {
                console.warn("QR Code generation failed:", qrErr);
            }
    
            if (typeof qz !== "undefined" && qz.websocket) {
                try {
                    await qz.websocket.connect();
                    const config = qz.configs.create("XP-58C");
    
                    const dataToPrint = [
                        {
                            type: 'raw',
                            format: 'plain',
                            data: qzReceiptText
                        }
                    ];
    
                    if (qrImageData) {
                        dataToPrint.push({
                            type: 'image',
                            format: 'base64',
                            data: qrImageData
                        });
                    }
    
                    await qz.print(config, dataToPrint);
                    console.log("✅ Receipt printed via QZ Tray");
                    await qz.websocket.disconnect();
                } catch (qzErr) {
                    console.error("❌ QZ Tray Print Error:", qzErr);
                    const encodedReceipt = encodeURIComponent(browserReceiptText);
                    window.location.href = `/static/print_receipt.html?receipt=${encodedReceipt}`;
                }
            } else {
                console.warn("⚠️ QZ Tray not available, using browser print fallback");
                const encodedReceipt = encodeURIComponent(browserReceiptText);
                window.location.href = `/static/print_receipt.html?receipt=${encodedReceipt}`;
            }
        } catch (err) {
            console.error("❌ Print Error:", err.message);
            alert(`❌ Print failed: ${err.message}`);
        }
    }



}

const cashRegister = new CashRegister();
