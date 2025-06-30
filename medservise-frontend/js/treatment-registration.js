document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        alert("Please log in.");
        window.location.href = "index.html";
        return;
    }

    const patientSelect = document.getElementById("patient-select");
    const roomSelect = document.getElementById("room-select");
    const assignBtn = document.getElementById("assign-btn");
    const roomGrid = document.getElementById("room-grid");

    // Load recent patients (last 2 days)
    function loadPatients() {
        fetch("http://localhost:8000/api/v1/recent-patients/", {
            headers: { Authorization: `Bearer ${token}` }
        })
            .then(res => res.json())
            .then(patients => {
                patientSelect.innerHTML = '<option disabled selected>Select Patient</option>';
                patients.forEach(p => {
                    const opt = document.createElement("option");
                    opt.value = p.id;
                    opt.textContent = `${p.first_name} ${p.last_name}`;
                    patientSelect.appendChild(opt);
                });
            })
            .catch(err => console.error("❌ Failed to load patients", err));
    }

    // Load and display rooms grouped by floor
    function loadRooms() {
        fetch("http://localhost:8000/api/v1/treatment-rooms/", {
            headers: { Authorization: `Bearer ${token}` }
        })
            .then(res => res.json())
            .then(rooms => {
                roomSelect.innerHTML = '<option disabled selected>Select Room</option>';
                roomGrid.innerHTML = "";

                // Group rooms by floor
                const floors = {};
                rooms.forEach(room => {
                    if (!floors[room.floor]) {
                        floors[room.floor] = [];
                    }
                    floors[room.floor].push(room);

                    // Add to dropdown
                    const opt = document.createElement("option");
                    opt.value = room.id;
                    opt.textContent = `${room.name} - Floor ${room.floor} (${room.capacity} beds)`;
                    roomSelect.appendChild(opt);
                });

                // Render cards grouped by floor
                Object.keys(floors).sort().forEach(floor => {
                    const floorHeader = document.createElement("h4");
                    floorHeader.textContent = `🧱 Floor ${floor}`;
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
            })
            .catch(err => console.error("❌ Failed to load rooms", err));
    }

    // Assign patient to room
    assignBtn.addEventListener("click", () => {
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
                patientSelect.selectedIndex = 0;
                roomSelect.selectedIndex = 0;
            })
            .catch(err => {
                console.error("❌ Error assigning patient:", err);
                alert("Assignment failed");
            });
    });

    // Initial load
    loadPatients();
    loadRooms();
});
