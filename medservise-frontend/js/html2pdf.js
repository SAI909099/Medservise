const downloadBtn = document.getElementById("download-pdf");
if (downloadBtn) {
  downloadBtn.addEventListener("click", () => {
    const el = document.createElement("div");
    el.innerHTML = `
      <h3>📄 Tranzaksiya Hisoboti</h3>
      <table border="1" cellspacing="0" cellpadding="4">
        <thead>
          <tr>
            <th>ID</th><th>Shaxs</th><th>Turi</th><th>Izoh</th><th>Summa</th><th>Usul</th><th>Vaqt</th>
          </tr>
        </thead>
        <tbody>
          ${cachedTransactions.map(tx => `
            <tr>
              <td>${tx.id}</td>
              <td>${tx.patient_name || tx.created_by || "—"}</td>
              <td>${tx.source === "outcome" ? "Xarajat" : translateType(tx.transaction_type)}</td>
              <td>${tx.notes || tx.title || "—"}</td>
              <td>${tx.amount.toLocaleString("uz-UZ")} so'm</td>
              <td>${translateMethod(tx.payment_method)}</td>
              <td>${new Date(tx.created_at).toLocaleString("uz-UZ")}</td>
            </tr>`).join("")}
        </tbody>
      </table>
    `;

    const opt = {
      margin:       0.5,
      filename:     'hisobot.pdf',
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2 },
      jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' }
    };

    html2pdf().from(el).set(opt).save();
  });
}
