document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");

  if (!token) {
    alert("You must log in first!");
    window.location.href = "index.html";
    return;
  }

  fetch("http://localhost:8000/api/v1/my-appointments/", {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  })
    .then(res => res.json())
    .then(data => {
      const tableBody = document.querySelector("#appointments-table tbody");
      tableBody.innerHTML = "";

      data.appointments.forEach(app => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${app.patient.first_name} ${app.patient.last_name}</td>
          <td>${app.reason}</td>
          <td>${app.status}</td>
          <td>${new Date(app.created_at).toLocaleString()}</td>
          <td>
            ${app.status === "queued"
              ? `
                <select class="form-select form-select-sm room-dropdown" data-app-id="${app.id}">
                  <option disabled selected>Select Room</option>
                </select>
                <button class="btn btn-sm btn-primary assign-btn" data-app-id="${app.id}">Assign</button>
                <button class="btn btn-sm btn-success" onclick="markDone(${app.id})">Done</button>`
              : ''}
            <button class="btn btn-sm btn-info" onclick="viewInfo(${app.patient.id})">Info</button>
            <button class="btn btn-sm btn-danger" onclick="deleteApp(${app.id})">Delete</button>
          </td>
        `;
        tableBody.appendChild(row);
      });

      // ✅ Populate available rooms for dropdown
      fetch("http://localhost:8000/api/v1/treatment-rooms/", {
        headers: { "Authorization": `Bearer ${token}` }
      })
        .then(res => res.json())
        .then(rooms => {
          document.querySelectorAll(".room-dropdown").forEach(select => {
            rooms.forEach(room => {
              if (!room.is_busy) {
                const option = document.createElement("option");
                option.value = room.id;
                option.textContent = `Room ${room.id}`;
                select.appendChild(option);
              }
            });
          });
        });

      // ✅ Assign room to appointment
      document.querySelectorAll(".assign-btn").forEach(button => {
        button.addEventListener("click", () => {
          const appId = button.getAttribute("data-app-id");
          const select = document.querySelector(`.room-dropdown[data-app-id="${appId}"]`);
          const roomId = select.value;

          if (!roomId) {
            alert("Please select a room.");
            return;
          }

          fetch("http://localhost:8000/api/v1/assign-room/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ appointment_id: appId, room_id: roomId })
          })
            .then(res => res.json())
            .then(() => window.location.reload())
            .catch(err => alert("Assignment failed"));
        });
      });
    })
    .catch(err => {
      console.error("Error loading appointments:", err);
      alert("Could not load appointments.");
    });

  // ✅ Toggle room visibility
  const viewRoomsBtn = document.getElementById("view-rooms-btn");
  if (viewRoomsBtn) {
    viewRoomsBtn.addEventListener("click", function () {
      fetch("http://localhost:8000/api/v1/treatment-rooms/", {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      })
        .then(res => res.json())
        .then(data => {
          const roomList = document.getElementById("room-list");
          roomList.innerHTML = "";

          data.forEach(room => {
            const card = document.createElement("div");
            card.className = `card p-3 m-2 ${room.is_busy ? 'bg-danger text-white' : 'bg-success text-white'}`;
            card.style.width = '200px';
            card.innerHTML = `
              <h5>Room ${room.id}</h5>
              <p>Status: ${room.is_busy ? "Busy" : "Available"}</p>
            `;
            roomList.appendChild(card);
          });

          document.getElementById("treatment-rooms").style.display = "block";
        })
        .catch(err => {
          console.error("Room fetch error:", err);
          alert("Could not load treatment rooms.");
        });
    });
  }
});

// ✅ Done button logic
function markDone(id) {
  const token = localStorage.getItem("token");
  fetch(`http://localhost:8000/api/v1/my-appointments/${id}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({ status: "done" })
  }).then(() => window.location.reload());
}

// ✅ Delete button logic
function deleteApp(id) {
  const token = localStorage.getItem("token");
  fetch(`http://localhost:8000/api/v1/my-appointments/${id}/`, {
    method: "DELETE",
    headers: {
      "Authorization": `Bearer ${token}`
    }
  }).then(() => window.location.reload());
}

// ✅ Info button logic → redirect to patient-detail.html with ID
function viewInfo(patientId) {
  window.location.href = `patient-detail.html?patient_id=${patientId}`;
}

// ✅ Logout
function logout() {
  localStorage.removeItem("token");
  window.location.href = "index.html";
}
