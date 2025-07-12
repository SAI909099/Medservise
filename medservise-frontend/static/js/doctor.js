document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Avval tizimga kiring!");
    window.location.href = "index.html";
    return;
  }

  const dateFilter = document.getElementById("date-filter");
  const searchName = document.getElementById("search-name");
  const tableBody = document.querySelector("#appointments-table tbody");

  function loadAppointments(date = null, search = "") {
    fetch("http://localhost:8000/api/v1/my-appointments/", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
      .then(res => res.json())
      .then(data => {
        tableBody.innerHTML = "";
        let appointments = data.appointments;

        // Filter by date if selected
        if (date) {
          const selectedDate = new Date(date).toDateString();
          appointments = appointments.filter(app =>
            new Date(app.created_at).toDateString() === selectedDate
          );
        }

        // Filter by name if typed
        if (search.trim() !== "") {
          const lowerSearch = search.toLowerCase();
          appointments = appointments.filter(app =>
            `${app.patient.first_name} ${app.patient.last_name}`.toLowerCase().includes(lowerSearch)
          );
        }

        // Render appointments
        appointments.forEach(app => {
          const row = document.createElement("tr");
          const createdAt = new Date(app.created_at).toLocaleString();
          const fullName = `${app.patient.first_name} ${app.patient.last_name}`;
          const isQueued = app.status === "queued";

          const buttons = `
            <div class="d-flex flex-column gap-1">
              ${isQueued ? `
                <button class="btn btn-sm btn-warning" onclick="callPatient(${app.id})">📣 Chaqirish</button>
                <button class="btn btn-sm btn-success" onclick="markDone(${app.id})">✅ Bajarildi</button>
              ` : ""}
              <button class="btn btn-sm btn-info" onclick="viewInfo(${app.patient.id})">ℹ️ Maʼlumot</button>
              <button class="btn btn-sm btn-danger" onclick="confirmDelete(${app.id})">🗑️ Oʻchirish</button>
            </div>
          `;

          row.innerHTML = `
            <td>${fullName}</td>
            <td>${app.reason}</td>
            <td>${app.status}</td>
            <td>${createdAt}</td>
            <td>${buttons}</td>
          `;
          tableBody.appendChild(row);
        });
      })
      .catch(err => {
        console.error("Xatolik qabul olishda:", err);
        alert("Qabul roʻyxatini yuklab boʻlmadi.");
      });
  }

  // Bugungi sana bo'yicha filter
  document.getElementById("filter-today-btn")?.addEventListener("click", () => {
    const today = new Date().toISOString().split("T")[0];
    dateFilter.value = today;
    loadAppointments(today, searchName.value);
  });

  // Apply filter with date + name
  document.getElementById("apply-filters-btn")?.addEventListener("click", () => {
    const selectedDate = dateFilter.value;
    const nameQuery = searchName.value;
    loadAppointments(selectedDate || null, nameQuery);
  });

  // Dastlabki yuklash
  loadAppointments();
});

// ✅ Qabulni bajarilgan deb belgilash
function markDone(id) {
  const token = localStorage.getItem("token");
  fetch(`http://localhost:8000/api/v1/my-appointments/${id}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ status: "done" })
  })
    .then(res => res.json())
    .then(() => fetch(`http://localhost:8000/api/v1/clear-call/${id}/`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` }
    }))
    .then(() => window.location.reload())
    .catch(err => {
      console.error(err);
      alert("❌ Qabulni yakunlab boʻlmadi.");
    });
}

// ✅ Bemorni chaqirish
function callPatient(appointmentId) {
  const token = localStorage.getItem("token");

  fetch(`http://localhost:8000/api/v1/call-patient/${appointmentId}/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
    .then(res => {
      if (!res.ok) throw new Error("Chaqirishda xatolik");
      return res.json();
    })
    .then(() => {
      new Audio("/static/sound/beep.wav").play();
      alert("🔔 Bemor chaqirildi!");
      const btn = document.querySelector(`button[onclick="callPatient(${appointmentId})"]`);
      if (btn) {
        btn.textContent = "🔁 Qayta chaqirish";
        btn.classList.remove("btn-warning");
        btn.classList.add("btn-secondary");
      }
    })
    .catch(err => {
      console.error(err);
      alert("❌ Chaqirishda xatolik.");
    });
}

// ✅ O'chirishni tasdiqlash va bajarish
function confirmDelete(id) {
  if (confirm("Rostdan ham ushbu qabuli o‘chirmoqchimisiz?")) {
    deleteApp(id);
  }
}

// ✅ Qabulni o'chirish
function deleteApp(id) {
  const token = localStorage.getItem("token");
  fetch(`http://localhost:8000/api/v1/my-appointments/${id}/`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).then(() => window.location.reload());
}

// ✅ Bemor ma'lumotiga o'tish
function viewInfo(patientId) {
  window.location.href = `patient-detail.html?patient_id=${patientId}`;
}

// ✅ Chiqish
function logout() {
  localStorage.removeItem("token");
  window.location.href = "index.html";
}
