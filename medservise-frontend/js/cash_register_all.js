// ======================= LOGOUT FUNCTION =======================
function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("refresh");
  window.location.href = "/login.html"; // Redirect to login page
}

// ======================= REFRESH TOKEN FUNCTION =======================
async function refreshToken() {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) {
    logout();
    return null;
  }

  try {
    const res = await fetch("/api/v1/token/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh })
    });

    if (!res.ok) throw new Error("Refresh token failed");
    const data = await res.json();
    localStorage.setItem("token", data.access); // Save new access token
    return data.access;
  } catch (err) {
    console.error("Refresh failed:", err);
    logout();
  }
}

// ======================= AUTHENTICATED FETCH WRAPPER =======================
async function authFetch(url, options = {}) {
  let token = localStorage.getItem("token");
  options.headers = options.headers || {};
  options.headers["Content-Type"] = "application/json";

  if (token) {
    options.headers["Authorization"] = `Bearer ${token}`;
  }

  let res = await fetch(url, options);

  // If token expired, try refresh
  if (res.status === 401) {
    token = await refreshToken();
    if (token) {
      options.headers["Authorization"] = `Bearer ${token}`;
      res = await fetch(url, options);
    }
  }

  return res;
}

// ======================= PAGE LOADER =======================
document.addEventListener("DOMContentLoaded", () => {
  if (!localStorage.getItem("token")) {
    alert("Please login first");
    window.location.href = "/login.html";
    return;
  }

  loadAllPatients();
  document.getElementById("cash-form").addEventListener("submit", submitPayment);
});

// ======================= LOAD ALL PATIENTS =======================
async function loadAllPatients() {
  try {
    const res = await authFetch("/api/v1/patients/");
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
      li.addEventListener("click", () => selectPatient(p.id));
      list.appendChild(li);
    });
  } catch (err) {
    console.error("Patient list error:", err);
    alert("Unable to load patients.");
  }
}

// ======================= SELECT PATIENT =======================
async function selectPatient(patientId) {
  try {
    const res = await authFetch(`/api/v1/cash-register/patient/${patientId}/`);
    if (!res.ok) throw new Error("Failed to fetch patient details");
    const data = await res.json();

    const { patient, balance } = data.summary;

    document.getElementById("patient-section").classList.remove("d-none");
    document.getElementById("patient").value = patientId;
    document.getElementById("patient-id-display").textContent = patientId;
    document.getElementById("patient-name").textContent = patient.name;
    document.getElementById("patient-phone").textContent = patient.phone;
    document.getElementById("balance").textContent = `$${balance.toFixed(2)}`;

    renderTransactions(data.transactions);
  } catch (err) {
    console.error("Patient load error:", err);
    alert("Failed to load patient info");
  }
}

// ======================= RENDER TRANSACTIONS =======================
function renderTransactions(transactions) {
  const tbody = document.querySelector("#cash-register-table tbody");
  tbody.innerHTML = "";

  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = "<tr><td colspan='6'>No transactions found</td></tr>";
    return;
  }

  transactions.forEach(tx => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${tx.patient_name || "—"}</td>
      <td>${tx.transaction_type}</td>
      <td>$${parseFloat(tx.amount).toFixed(2)}</td>
      <td>${tx.payment_method}</td>
      <td>${tx.notes || "-"}</td>
      <td>${new Date(tx.created_at).toLocaleString()}</td>
    `;
    tbody.appendChild(row);
  });
}

// ======================= SUBMIT PAYMENT =======================
async function submitPayment(event) {
  event.preventDefault();

  const data = {
    patient: document.getElementById("patient").value,
    transaction_type: document.getElementById("transaction_type").value,
    amount: parseFloat(document.getElementById("amount").value),
    payment_method: document.getElementById("payment_method").value,
    notes: document.getElementById("notes").value
  };

  try {
    const res = await authFetch("/api/v1/cash-register/", {
      method: "POST",
      body: JSON.stringify(data)
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Payment failed");
    }

    alert("Payment recorded successfully!");
    document.getElementById("cash-form").reset();
    selectPatient(data.patient); // reload details
  } catch (err) {
    console.error("Payment error:", err);
    alert(`Error: ${err.message}`);
  }
}
