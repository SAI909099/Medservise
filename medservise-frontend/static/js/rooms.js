document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");

  function loadRooms() {
    fetch("http://localhost:8000/api/v1/treatment-rooms/", {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    })
      .then(res => res.json())
      .then(data => {
        const list = document.getElementById("room-list");
        list.innerHTML = "";
        data.forEach(room => {
          const div = document.createElement("div");
          div.className = `card m-2 p-3 ${room.is_busy ? 'bg-danger text-white' : 'bg-success text-white'}`;
          div.style.width = '200px';
          div.innerHTML = `
            <h5>${room.name}</h5>
            <p>Capacity: ${room.capacity}</p>
            <p>Status: ${room.is_busy ? "Busy" : "Available"}</p>
          `;
          list.appendChild(div);
        });
      });
  }

  document.getElementById("add-room-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const name = document.getElementById("room-name").value;
    const capacity = document.getElementById("room-capacity").value;

    fetch("http://localhost:8000/api/v1/treatment-rooms/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ name, capacity })
    })
      .then(() => {
        loadRooms();
        e.target.reset();
      });
  });

  loadRooms();
});
