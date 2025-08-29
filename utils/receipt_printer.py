from escpos.printer import Usb
from django.conf import settings

class ReceiptPrinter:
    def __init__(self):
        # Replace these with your USB VendorID and ProductID
        self.vendor_id = 0x0483  # STMicroelectronics
        self.product_id = 0x070b
        self.interface = 0
        self.device = Usb(self.vendor_id, self.product_id, self.interface)

    def print_receipt(self, receipt_data):
        try:
            self.device.set(align='center', bold=True, width=2, height=2)
            self.device.text("Controllab\n")
            self.device.set(align='center', bold=False, width=1, height=1)
            self.device.text("NAQD TO‘LOV CHEKI \n")
            self.device.text("-------------------------------\n")

            self.device.set(align='left')
            self.device.text(f"Chek raqami: {receipt_data['receipt_number']}\n")
            self.device.text(f"Sana: {receipt_data['date']}\n")
            self.device.text(f"Bemor: {receipt_data['patient_name']}\n")
            if receipt_data.get('doctor_first_name'):
                self.device.text(f"Shifokor: {receipt_data['doctor_firstname']}\n")
            self.device.text(f"To‘lov turi: {receipt_data['transaction_type']}\n")
            self.device.text(f"Miqdori: {receipt_data['amount']:.2f} so'm\n")
            self.device.text(f"To‘lov usuli: {receipt_data['payment_method']}\n")
            if receipt_data.get('notes'):
                self.device.text(f"Izoh: {receipt_data['notes']}\n")
            # self.device.text(f"Qabul qiluvchi: {receipt_data['processed_by']}\n")
            self.device.text("-------------------------------\n")
            self.device.text("Tashrifingiz uchun rahmat!\n\n\n")
            self.device.cut()

        except Exception as e:
            print("🖨️ Chek chiqarishda xatolik:", e)