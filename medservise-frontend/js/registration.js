document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Login required.");
    location.href = "index.html";
    return;
  }

  const doctorSelect = document.getElementById("doctor_id");
  const form = document.getElementById("patient-form");
  const roomList = document.getElementById("room-list");
  const addRoomBtn = document.getElementById("add-room-btn");
  const newRoomNameInput = document.getElementById("new-room-name");

  // Load doctors
  fetch("http://localhost:8000/api/v1/doctor-list/", {
    headers: { Authorization: `Bearer ${token}` }
  })
    .then(res => res.json())
    .then(doctors => {
      doctors.forEach(doc => {
        const option = document.createElement("option");
        option.value = doc.id;
        option.textContent = `${doc.name} (${doc.specialty})`;
        doctorSelect.appendChild(option);
      });
    });

  // Load rooms
  function loadRooms() {
    fetch("http://localhost:8000/api/v1/treatment-rooms/", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(rooms => {
        roomList.innerHTML = "";
        rooms.forEach(room => {
          const div = document.createElement("div");
          div.className = `card p-2 m-2 text-white ${room.is_busy ? "bg-danger" : "bg-success"}`;
          div.style.width = "200px";
          div.innerHTML = `
            <h5>${room.name}</h5>
            <p>Status: <strong>${room.is_busy ? "Busy" : "Available"}</strong></p>
            <button class="btn btn-sm ${room.is_busy ? 'btn-warning' : 'btn-secondary'} mt-2 toggle-room-btn">
              Mark as ${room.is_busy ? "Available" : "Busy"}
            </button>
            <button class="btn btn-sm btn-danger mt-2 delete-room-btn">🗑️ Delete</button>
          `;

          // Toggle room
          div.querySelector(".toggle-room-btn").addEventListener("click", () => {
            fetch(`http://localhost:8000/api/v1/treatment-rooms/${room.id}/`, {
              method: "PATCH",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
              },
              body: JSON.stringify({ is_busy: !room.is_busy })
            })
              .then(() => loadRooms());
          });

          // Delete room
          div.querySelector(".delete-room-btn").addEventListener("click", () => {
            if (!confirm(`Delete "${room.name}"?`)) return;
            fetch(`http://localhost:8000/api/v1/treatment-rooms/${room.id}/`, {
              method: "DELETE",
              headers: { Authorization: `Bearer ${token}` }
            }).then(() => loadRooms());
          });

          roomList.appendChild(div);
        });
      });
  }

  loadRooms();

  // Add new room
  addRoomBtn.addEventListener("click", () => {
    const roomName = newRoomNameInput.value.trim();
    if (!roomName) return alert("Enter a room name.");

    fetch("http://localhost:8000/api/v1/treatment-rooms/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ name: roomName })
    })
      .then(() => {
        newRoomNameInput.value = "";
        loadRooms();
      });
  });

  // Submit patient registration form
  form.addEventListener("submit", e => {
    e.preventDefault();

    const data = {
      first_name: document.getElementById("first_name").value,
      last_name: document.getElementById("last_name").value,
      age: parseInt(document.getElementById("age").value),
      phone: document.getElementById("phone").value,
      address: document.getElementById("address").value,
      doctor_id: doctorSelect.value,
      reason: document.getElementById("reason").value
    };

    fetch("http://localhost:8000/api/v1/register-patient/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data)
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to register");
        return res.json();
      })
      .then(() => {
        alert("✅ Patient registered successfully.");
        form.reset();
      })
      .catch(err => {
        console.error("Registration failed:", err);
        alert("❌ Could not register patient.");
      });
  });
});
