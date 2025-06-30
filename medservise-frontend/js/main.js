// ------------------------ LOGIN FORM SUBMIT ------------------------
document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector("form");

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();

      const email = document.querySelector("input[name='email']").value;
      const password = document.querySelector("input[name='password']").value;

      fetch("http://localhost:8000/api/v1/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email,
          password: password,
        }),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Invalid credentials");
          }
          return response.json();
        })
        .then((data) => {
          if (data.access) {
            localStorage.setItem("token", data.access);       // Access token
            localStorage.setItem("access", data.access);      // Store separately
            localStorage.setItem("refresh", data.refresh);    // Refresh token
            alert("Login successful!");
            window.location.href = "doctor.html";             // ✅ redirect to doctor dashboard
          } else {
            throw new Error("No access token returned");
          }
        })
        .catch((error) => {
          alert("Login failed: " + error.message);
        });
    });
  }

  // ------------------------ DOCTOR DASHBOARD LOGIC ------------------------
  if (window.location.pathname.includes("doctor.html")) {
    const token = localStorage.getItem("token");

    if (!token) {
      alert("You must log in first!");
      window.location.href = "index.html";
      return;
    }

    fetch("http://localhost:8000/api/v1/doctor/appointments/", {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    })
      .then(res => res.json())
      .then(data => {
        const tableBody = document.querySelector("#appointments-table tbody");
        tableBody.innerHTML = ""; // Clear table before inserting

        data.appointments.forEach(app => {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td>${app.patient.first_name} ${app.patient.last_name}</td>
            <td>${app.doctor?.name || 'No Doctor'}</td>
            <td>${app.reason}</td>
            <td>${app.status}</td>
            <td>${new Date(app.created_at).toLocaleString()}</td>
            <td>
              ${app.status === "queued"
                ? `<button class="btn btn-sm btn-success" onclick="markDone(${app.id})">Done</button>`
                : ''}
              <button class="btn btn-sm btn-danger" onclick="deleteApp(${app.id})">Delete</button>
              <button class="btn btn-sm btn-info" onclick="viewUploads(${app.patient.id})">Uploads</button>
            </td>
          `;
          tableBody.appendChild(row);
        });
      })
      .catch(err => {
        console.error("Failed to fetch appointments:", err);
        alert("Error loading appointments");
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
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({ status: "done" })
  })
    .then(res => {
      if (res.ok) {
        window.location.reload();
      } else {
        alert("Failed to update appointment.");
      }
    });
}

// ------------------------ DELETE APPOINTMENT ------------------------
function deleteApp(id) {
  const token = localStorage.getItem("token");

  fetch(`http://localhost:8000/api/v1/doctor/appointments/${id}/`, {
    method: "DELETE",
    headers: {
      "Authorization": `Bearer ${token}`
    }
  })
    .then(res => {
      if (res.ok) {
        window.location.reload();
      } else {
        alert("Failed to delete appointment.");
      }
    });
}

// ------------------------ VIEW PATIENT UPLOADS ------------------------
function viewUploads(patientId) {
  const token = localStorage.getItem("token");

  fetch(`http://localhost:8000/api/v1/patient-results/?patient=${patientId}`, {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  })
    .then(res => res.json())
    .then(data => {
      if (!data.length) {
        alert("No uploads found for this patient.");
        return;
      }

      let msg = "Uploaded Results:\n";
      data.forEach(result => {
        msg += `• ${result.title} — ${new Date(result.uploaded_at).toLocaleString()}\n`;
      });

      alert(msg);
    })
    .catch(err => {
      console.error("Failed to fetch uploads:", err);
      alert("Could not fetch patient uploads.");
    });
}

// ------------------------ LOGOUT FUNCTION ------------------------
function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
  window.location.href = "index.html";
}

