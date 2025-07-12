const turnDisplay = document.getElementById("turn-display");
const queueList = document.getElementById("queue-list");
const sound = document.getElementById("turn-sound");

let lastTurnCode = null;

function updateTurnDisplay(data) {
  const allCalls = [...(data.doctor_calls || []), ...(data.service_calls || [])];
  const queued = data.queued || [];

  // Update latest called patient
  if (allCalls.length > 0) {
    const latest = allCalls[0];
    const { turn_number, patient_name } = latest;

    if (turn_number !== lastTurnCode) {
      lastTurnCode = turn_number;

      turnDisplay.querySelector(".turn-number").textContent = turn_number;
      turnDisplay.querySelector(".doctor-name").textContent = patient_name;

      sound.play();
    }
  }

  // Show queued patients
  queueList.innerHTML = ""; // Clear previous
  queued.forEach(entry => {
    const item = document.createElement("div");
    item.className = "queue-item";
    item.textContent = `${entry.turn_number} - ${entry.patient_name}`;
    queueList.appendChild(item);
  });
}

function fetchTurn() {
  fetch("http://localhost:8000/api/v1/current-calls/")
    .then(res => res.json())
    .then(updateTurnDisplay)
    .catch(err => console.error("❌ Failed to fetch turn:", err));
}

fetchTurn();
setInterval(fetchTurn, 5000);
