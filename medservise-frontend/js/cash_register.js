class CashRegister {
  constructor() {
    this.token = localStorage.getItem("token");
    this.refresh = localStorage.getItem("refresh");
    this.apiBase = "http://localhost:8000/api/v1";

    if (!this.token) {
      alert("Please login first");
      window.location.href = "/login.html";
    } else {
      this.init();
    }
  }

  async init() {
    const daysFilter = document.getElementById("days-filter");
    if (daysFilter) {
      daysFilter.addEventListener("change", (e) => {
        this.loadRecentPatients(e.target.value);
      });
    }

    await this.loadRecentPatients(3);

    document.getElementById("cash-form")?.addEventListener("submit", (e) => this.submitPayment(e));
    document.getElementById("print-all-btn")?.addEventListener("click", () => {
      alert("Printing all receipts is not implemented yet.");
    });
  }

  logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh");
    window.location.href = "/login.html";
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
      if (!res.ok) throw new Error("Refresh token failed");
      const data = await res.json();
      localStorage.setItem("token", data.access);
      this.token = data.access;
      return data.access;
    } catch (err) {
      console.error("Refresh failed:", err);
      this.logout();
    }
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

  async loadRecentPatients(days = 3) {
    try {
      const url = `${this.apiBase}/recent-patients/`;
      const res = await this.authFetch(url);
      if (!res.ok) throw new Error("Failed to fetch patients");

      const patients = await res.json();
      const list = document.getElementById("patient-list");
      list.innerHTML = "";

      if (patients.length === 0) {
        list.innerHTML = "<li class='list-group-item'>No patients found</li>";
        return;
      }

      patients.forEach(p => {
        const li = document.createElement("li");
        li.className = "list-group-item list-group-item-action";
        li.textContent = `${p.first_name} ${p.last_name} (${p.phone})`;
        li.addEventListener("click", () => this.selectPatient(p.id));
        list.appendChild(li);
      });
    } catch (err) {
      console.error("Patient list error:", err);
      alert("Unable to load patients.");
    }
  }

  async selectPatient(patientId) {
    try {
      const res = await this.authFetch(`${this.apiBase}/cash-register/patient/${patientId}/`);
      if (!res.ok) throw new Error("Failed to fetch patient details");
      const data = await res.json();
      const { patient, balance } = data.summary;

      document.getElementById("patient").value = patientId;
      document.getElementById("patient-id-display").textContent = patientId;
      document.getElementById("patient-name").textContent = patient.name;
      document.getElementById("patient-phone").textContent = patient.phone;
      document.getElementById("balance").textContent = `$${balance.toFixed(2)}`;

      this.renderTransactions(data.transactions);
    } catch (err) {
      console.error("Patient load error:", err);
      alert("Failed to load patient info");
    }
  }

  renderTransactions(transactions) {
    const tbody = document.querySelector("#cash-register-table tbody");
    tbody.innerHTML = "";
    if (!transactions || transactions.length === 0) {
      tbody.innerHTML = "<tr><td colspan='7'>No transactions found</td></tr>";
      return;
    }

    transactions.forEach(tx => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${tx.patient_name || "—"}</td>
        <td>${tx.transaction_type}</td>
        <td>${tx.notes || "-"}</td>
        <td>$${parseFloat(tx.amount).toFixed(2)}</td>
        <td>${tx.payment_method}</td>
        <td>${new Date(tx.created_at).toLocaleString()}</td>
        <td>
          <button class="btn btn-sm btn-outline-primary" onclick="cashRegister.viewReceipt(${tx.id})">View</button>
          <button class="btn btn-sm btn-outline-success" onclick="cashRegister.printReceipt(${tx.id})">Print</button>
        </td>`;
      tbody.appendChild(row);
    });
  }

  async submitPayment(event) {
    event.preventDefault();
    const data = {
      patient: parseInt(document.getElementById("patient").value),
      transaction_type: document.getElementById("transaction_type").value,
      amount: parseFloat(document.getElementById("amount").value),
      payment_method: document.getElementById("payment_method").value,
      notes: document.getElementById("notes").value
    };

    try {
      const res = await this.authFetch(`${this.apiBase}/cash-register/`, {
        method: "POST",
        body: JSON.stringify(data)
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error?.detail || JSON.stringify(error));
      }

      alert("Payment recorded successfully!");
      document.getElementById("cash-form").reset();
      this.selectPatient(data.patient);
    } catch (err) {
      console.error("Payment error:", err);
      alert(`Error: ${err.message}`);
    }
  }

  viewReceipt(id) {
    window.open(`${this.apiBase}/cash-register/receipt/${id}/`, "_blank");
  }

  printReceipt(id) {
    const url = `${this.apiBase}/cash-register/receipt/${id}/`;
    const win = window.open(url, "_blank");
    win.onload = () => win.print();
  }
}

const cashRegister = new CashRegister();
