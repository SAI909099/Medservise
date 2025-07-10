document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Please log in.");
    window.location.href = "index.html";
    return;
  }

  const doctorSelect = document.getElementById("doctor-select");
  const patientSelect = document.getElementById("patient-select");
  const roomSelect = document.getElementById("room-select");
  const assignBtn = document.getElementById("assign-btn");
  const roomGrid = document.getElementById("room-grid");

  function loadDoctors() {
    fetch("http://localhost:8000/api/v1/doctor-list/", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(doctors => {
        doctorSelect.innerHTML = '<option value="">All Doctors</option>';
        doctors.forEach(doc => {
          const opt = document.createElement("option");
          opt.value = doc.id;
          opt.textContent = doc.name;
          doctorSelect.appendChild(opt);
        });
      });
  }

  function loadPatients(doctorId = null) {
    fetch("http://localhost:8000/api/v1/patients/", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(patients => {
        const twoDaysAgo = new Date();
        twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);
        const twoDaysAgoTime = twoDaysAgo.getTime();

        let filtered = patients.filter(p => {
          const created = new Date(p.created_at).getTime();
          return created >= twoDaysAgoTime;
        });

        if (doctorId) {
          filtered = filtered.filter(p => p.patients_doctor && p.patients_doctor.id === parseInt(doctorId));
        }

        patientSelect.innerHTML = '<option disabled selected>Select Patient</option>';
        filtered.forEach(p => {
          const opt = document.createElement("option");
          opt.value = p.id;
          opt.textContent = `${p.first_name} ${p.last_name}`;
          patientSelect.appendChild(opt);
        });
      });
  }

  function loadRooms() {
    fetch("http://localhost:8000/api/v1/treatment-rooms/", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(rooms => {
        roomSelect.innerHTML = '<option disabled selected>Select Room</option>';
        roomGrid.innerHTML = "";
        const floors = {};

        rooms.forEach(room => {
          if (!floors[room.floor]) floors[room.floor] = [];
          floors[room.floor].push(room);

          const opt = document.createElement("option");
          opt.value = room.id;
          opt.textContent = `${room.name} - Qavat ${room.floor} (${room.capacity} yotoq)`;
          roomSelect.appendChild(opt);
        });

        Object.keys(floors).sort().forEach(floor => {
          const floorHeader = document.createElement("h4");
          floorHeader.textContent = `🧱 Qavat ${floor}`;
          roomGrid.appendChild(floorHeader);

          const row = document.createElement("div");
          row.className = "d-flex flex-wrap gap-3 mb-4";

          floors[floor].forEach(room => {
            const patients = room.patients || [];
            const occupancy = patients.length;
            let statusClass = "bg-success";
            let statusText = "✅ Available";

            if (occupancy === 0) {
              statusClass = "bg-success";
              statusText = "✅ Available";
            } else if (occupancy < room.capacity) {
              statusClass = "bg-warning";
              statusText = "🟡 Partially Occupied";
            } else {
              statusClass = "bg-danger";
              statusText = "🚫 Full";
            }

            const div = document.createElement("div");
            div.className = `card p-3 text-white ${statusClass}`;
            div.style.width = "250px";

            let occupancyHTML = "<ul>";
            for (let i = 0; i < room.capacity; i++) {
              const patient = patients[i];
              occupancyHTML += `<li>${patient ? patient.first_name + " " + patient.last_name : "<i>Empty</i>"}</li>`;
            }
            occupancyHTML += "</ul>";

            div.innerHTML = `
              <h5>${room.name}</h5>
              <p><strong>Floor:</strong> ${room.floor}</p>
              <p>Capacity: ${room.capacity}</p>
              ${occupancyHTML}
              <p>Status: ${statusText}</p>
            `;

            row.appendChild(div);
          });

          roomGrid.appendChild(row);
        });
      });
  }

  function assignPatient() {
    const patientId = patientSelect.value;
    const roomId = roomSelect.value;
    if (!patientId || !roomId) return alert("❗ Select both patient and room");

    fetch("http://localhost:8000/api/v1/assign-patient-to-room/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ patient_id: patientId, room_id: roomId })
    })
      .then(res => {
        if (!res.ok) throw new Error("Assignment failed");
        return res.json();
      })
      .then(() => {
        alert("✅ Patient assigned successfully");
        loadRooms();
        loadPatients(doctorSelect.value);
      });
  }

  // Event Listeners
  assignBtn.addEventListener("click", assignPatient);
  doctorSelect.addEventListener("change", () => {
    loadPatients(doctorSelect.value || null);
  });

  // Initial load
  loadDoctors();
  loadRooms();
  loadPatients();
});