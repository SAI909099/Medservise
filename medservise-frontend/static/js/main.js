document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector("form");

  // ------------------------ LOGIN FORM SUBMIT ------------------------
  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();

      const email = document.querySelector("input[name='email']").value;
      const password = document.querySelector("input[name='password']").value;

      fetch("http://localhost:8000/api/v1/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      })
        .then((response) => {
          if (!response.ok) throw new Error("Login ma'lumotlari noto‘g‘ri");
          return response.json();
        })
        .then((data) => {
          if (data.access) {
            localStorage.setItem("token", data.access);
            localStorage.setItem("access", data.access);
            localStorage.setItem("refresh", data.refresh);
            localStorage.setItem("is_admin", data.is_admin);

            alert("Tizimga muvaffaqiyatli kirildi!");

            // ✅ Redirect only based on is_admin
            if (data.is_admin === true) {
              window.location.href = "/admin-dashboard/";
            } else {
              window.location.href = "/doctor/";
            }
          } else {
            throw new Error("Access token topilmadi");
          }
        })
        .catch((error) => {
          alert("Kirishda xatolik: " + error.message);
        });
    });
  }

  // ------------------------ DOCTOR DASHBOARD LOGIC ------------------------
  if (window.location.pathname === "/doctor/") {
    const token = localStorage.getItem("token");

    if (!token) {
      alert("Avval tizimga kiring!");
      window.location.href = "/";
      return;
    }

    fetch("http://localhost:8000/api/v1/doctor/appointments/", {
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Ma'lumotlarni olishda xatolik");
        return res.json();
      })
      .then((data) => {
        const tableBody = document.querySelector("#appointments-table tbody");
        if (!tableBody) return;

        tableBody.innerHTML = "";

        data.appointments.forEach((app) => {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td>${app.patient.first_name} ${app.patient.last_name}</td>
            <td>${app.doctor?.name || 'Nomaʼlum'}</td>
            <td>${app.reason}</td>
            <td>${app.status}</td>
            <td>${new Date(app.created_at).toLocaleString()}</td>
            <td class="action-buttons">
              ${app.status === "queued"
                ? `<button class="btn btn-sm btn-success" onclick="markDone(${app.id})">Yakunlandi</button>`
                : ''}
              <button class="btn btn-sm btn-danger" onclick="deleteApp(${app.id})">Oʻchirish</button>
              <button class="btn btn-sm btn-info" onclick="viewUploads(${app.patient.id})">Fayllar</button>
            </td>
          `;
          tableBody.appendChild(row);
        });
      })
      .catch((err) => {
        console.error("Appointmentlarni olishda xatolik:", err);
        alert("Maʼlumotlarni yuklashda muammo yuz berdi.");
      });
  }
});

// ------------------------ MARK DONE ------------------------
function markDone(id) {
  const token = localStorage.getItem("token");

  fetch(`http://localhost:8000/api/v1/doctor/appointments/${id}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify({ status: "done" }),
  })
    .then((res) => {
      if (res.ok) {
        window.location.reload();
      } else {
        alert("Yakunlashda xatolik.");
      }
    });
}

// ------------------------ DELETE APPOINTMENT ------------------------
function deleteApp(id) {
  const token = localStorage.getItem("token");

  fetch(`http://localhost:8000/api/v1/doctor/appointments/${id}/`, {
    method: "DELETE",
    headers: {
      "Authorization": `Bearer ${token}`,
    },
  })
    .then((res) => {
      if (res.ok) {
        window.location.reload();
      } else {
        alert("Oʻchirishda xatolik.");
      }
    });
}

// ------------------------ VIEW PATIENT UPLOADS ------------------------
function viewUploads(patientId) {
  const token = localStorage.getItem("token");

  fetch(`http://localhost:8000/api/v1/patient-results/?patient=${patientId}`, {
    headers: {
      "Authorization": `Bearer ${token}`,
    },
  })
    .then((res) => res.json())
    .then((data) => {
      if (!data.length) {
        alert("Ushbu bemor uchun fayllar topilmadi.");
        return;
      }

      let msg = "Yuklangan fayllar:\n";
      data.forEach((result) => {
        msg += `• ${result.title} — ${new Date(result.uploaded_at).toLocaleString()}\n`;
      });

      alert(msg);
    })
    .catch((err) => {
      console.error("Fayllarni olishda xatolik:", err);
      alert("Fayllarni ko‘rsatib bo‘lmadi.");
    });
}

// ------------------------ LOGOUT FUNCTION ------------------------
function logout() {
  localStorage.clear();
  window.location.href = "/";
}
