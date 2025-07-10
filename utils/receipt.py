from escpos.printer import Usb
from datetime import datetime

def print_receipt(patient_name, amount, payment_method, status, doctor_name, notes):
    try:
        p = Usb(0x0483, 0x070b)  # Your exact printer VendorID & ProductID
        p.set(align='center', text_type='B', width=2, height=2)
        p.text("🏥 Medservise Klinikasi\n\n")

        p.set(align='left', text_type='NORMAL', width=1, height=1)
        p.text(f"F.I.O.: {patient_name or '-'}\n")
        p.text(f"Miqdor: {amount} so'm\n")
        p.text(f"To‘lov turi: {payment_method or '-'}\n")
        p.text(f"Holat: {status or '-'}\n")
        p.text(f"Shifokor: {doctor_name or '-'}\n")
        p.text(f"Izoh: {notes or '—'}\n")
        p.text(f"Sana: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")

        p.text("\n✅ Rahmat!\n")
        p.cut()
    except Exception as e:
        print("❌ Chop etishda xatolik:", e)
