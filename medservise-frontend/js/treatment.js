document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Please log in first!");
    window.location.href = "index.html";
    return;
  }

  const tableBody = document.getElementById("treatment-assignments");

  // Fetch available treatment rooms and queued appointments
  Promise.all([
    fetch("http://localhost:8000/api/v1/treatment-room/", {
      headers: { "Authorization": `Bearer ${token}` }
    }).then(res => res.json()),
    fetch("http://localhost:8000/api/v1/appointment/", {
      headers: { "Authorization": `Bearer ${token}` }
    }).then(res => res.json())
  ])
  .then(([rooms, appointments]) => {
    appointments
      .filter(app => app.status === "queued")
      .forEach(app => {
        const row = document.createElement("tr");

        const select = document.createElement("select");
        select.className = "form-select";
        rooms.forEach(room => {
          const option = document.createElement("option");
          option.value = room.id;
          option.textContent = room.name || `Room ${room.id}`;
          select.appendChild(option);
        });

        const assignBtn = document.createElement("button");
        assignBtn.textContent = "Assign";
        assignBtn.className = "btn btn-primary";
        assignBtn.onclick = () => assignRoom(app.id, select.value);

        row.innerHTML = `
          <td>${app.patient.first_name} ${app.patient.last_name}</td>
          <td>${app.reason}</td>
        `;
        const tdSelect = document.createElement("td");
        const tdButton = document.createElement("td");
        tdSelect.appendChild(select);
        tdButton.appendChild(assignBtn);

        row.appendChild(tdSelect);
        row.appendChild(tdButton);
        tableBody.appendChild(row);
      });
  })
  .catch(err => {
    console.error("Error loading data:", err);
    alert("Could not load treatment data.");
  });
});

function assignRoom(appointmentId, roomId) {
  const token = localStorage.getItem("token");

  fetch("http://localhost:8000/api/v1/treatment-register/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({ appointment: appointmentId, treatment_room: roomId })
  })
    .then(res => {
      if (res.ok) {
        alert("Room assigned successfully!");
        window.location.reload();
      } else {
        alert("Failed to assign room.");
      }
    });
}
