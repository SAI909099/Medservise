const BASE_API = "http://89.39.95.150/api/v1/";
const token = localStorage.getItem("token");

function formatNumber(num) {
  return parseInt(num).toLocaleString("uz-UZ") + " so'm";
}

function fetchDashboardData(start = '', end = '') {
  const url = new URL("incomes/", BASE_API);
  if (start && end) {
    url.searchParams.append("start_date", start);
    url.searchParams.append("end_date", end);
  }

  fetch(url, {
    headers: { Authorization: `Bearer ${token}` }
  })
    .then(res => {
      if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
      return res.json();
    })
    .then(data => {
      renderSummary(data);
      renderServiceIncome(data.service_income);
      renderRoomIncome(data.room_income);

      const transUrl = new URL("recent-transactions/", BASE_API);
      if (start && end) {
        transUrl.searchParams.append("start_date", start);
        transUrl.searchParams.append("end_date", end);
      }

      return fetch(transUrl, {
        headers: { Authorization: `Bearer ${token}` }
      });
    })
    .then(res => {
      if (!res.ok) throw new Error(`Transactions fetch failed: ${res.status}`);
      return res.json();
    })
    .then(renderTransactions)
    .catch(err => {
      console.error("❌ Error fetching data:", err);
      const table = document.getElementById("transaction-table");
      if (table) {
        table.innerHTML = `<tr><td colspan="7" class="text-center">Xatolik yuz berdi: ${err.message}</td></tr>`;
      }
    });
}

function renderSummary(data) {
  document.getElementById("total-income").innerText = formatNumber(data.total_income || 0);
  document.getElementById("total-outcome").innerText = formatNumber(data.total_outcome || 0);
  document.getElementById("balance").innerText = formatNumber((data.total_income || 0) - (data.total_outcome || 0));

  const methodsList = document.getElementById("income-methods");
  methodsList.innerHTML = "";
  (data.incomes_by_method || []).forEach(item => {
    const li = document.createElement("li");
    li.className = "list-group-item d-flex justify-content-between";
    li.innerHTML = `<strong>${translateMethod(item.payment_method)}</strong><span>${formatNumber(item.total)}</span>`;
    methodsList.appendChild(li);
  });
}

function renderServiceIncome(data) {
  const ul = document.getElementById("service-income-list");
  ul.innerHTML = "";
  (data || []).forEach(d => {
    const li = document.createElement("li");
    li.className = "list-group-item d-flex justify-content-between";
    li.innerHTML = `<strong>${d.name}</strong> <span>${formatNumber(d.amount)}</span>`;
    ul.appendChild(li);
  });
}

function renderRoomIncome(amount) {
  document.getElementById("room-income").innerText = formatNumber(amount || 0);
}

function renderTransactions(data) {
  const table = document.getElementById("transaction-table");
  if (!table) return;

  table.innerHTML = "";

  if (data.length === 0) {
    table.innerHTML = `<tr><td colspan="7" class="text-center">Hech qanday to‘lovlar topilmadi.</td></tr>`;
    return;
  }

  data.slice(0, 50).forEach(tx => {
    const transactionTypeUz = translateType(tx.transaction_type);
    const person = tx.patient_name || "—";
    const method = translateMethod(tx.payment_method);
    const services = tx.services?.length > 0 ? tx.services.join(", ") : tx.notes || "—";
    const amount = formatNumber(tx.amount);
    const dateTime = new Date(tx.created_at).toLocaleString("uz-UZ");

    const row = `
      <tr class="${tx.transaction_type === 'outcome' ? 'table-danger' : 'table-success'}">
        <td>${tx.id}</td>
        <td>${person}</td>
        <td>${transactionTypeUz}</td>
        <td>${method}</td>
        <td>${services}</td>
        <td>${amount}</td>
        <td>${dateTime}</td>
      </tr>
    `;
    table.innerHTML += row;
  });
}

function translateType(type) {
  return {
    consultation: "Konsultatsiya",
    treatment: "Davolash",
    service: "Xizmat",
    room: "Xona",
    other: "Boshqa",
    outcome: "Xarajat",
    income: "Daromad"
  }[type] || type;
}

function translateMethod(method) {
  return {
    cash: "Naqd",
    card: "Karta",
    transfer: "O‘tkazma",
    insurance: "Sug‘urta"
  }[method] || method;
}

// Outcome form submit
const outcomeForm = document.getElementById("outcome-form");
if (outcomeForm) {
  outcomeForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const title = document.getElementById("outcome-title").value.trim();
    const category = document.getElementById("outcome-category").value;
    const amount = parseFloat(document.getElementById("outcome-amount").value);
    const method = document.getElementById("outcome-method").value;
    const notes = document.getElementById("outcome-notes").value.trim();

    if (!title || !category || !amount || !method) {
      alert("❗ Iltimos, barcha maydonlarni to‘ldiring.");
      return;
    }

    fetch(`${BASE_API}accountant/outcomes/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ title, category, amount, payment_method: method, notes })
    })
      .then(res => {
        if (!res.ok) {
          return res.json().then(data => {
            throw new Error(data.detail || "Xatolik");
          });
        }
        return res.json();
      })
      .then(() => {
        alert("✅ Xarajat saqlandi");
        outcomeForm.reset();
        bootstrap.Modal.getInstance(document.getElementById("outcomeModal")).hide();
        fetchDashboardData();
      })
      .catch(err => {
        console.error("❌ Xarajatni saqlab bo‘lmadi:", err);
        alert(`❌ Xarajatni saqlab bo‘lmadi: ${err.message}`);
      });
  });
}

// Filter form submit
const filterForm = document.getElementById("filter-form");
if (filterForm) {
  filterForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const start = document.getElementById("start-date").value;
    const end = document.getElementById("end-date").value;
    fetchDashboardData(start, end);
  });
}

// Initial load
fetchDashboardData();
