# ==================== [HOME PAGE] ====================
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6 import uic
from ui.attendance import AttendancePage
from ui.students import StudentPage
from ui.crud import CrudPage
from ui.statistics import StatisticsPage
from ui.touch_utils import PIN_PATH, PinDialog
from utils.paths import resource_path
import os


class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path('ui_QT/home.ui'), self)
        self.admin_pin = self.load_pin()

        # Kết nối sự kiện
        self.btn_shutdown.clicked.connect(self.shutdown_app)
        self.btn_att.clicked.connect(self.open_attendance)
        self.btn_list.clicked.connect(self.open_students)
        self.btn_crud.clicked.connect(self.open_crud)
        self.btn_stats.clicked.connect(self.open_stats)
        self.btn_open_pin.clicked.connect(self.toggle_pin_panel)
        self.btn_apply_pin.clicked.connect(self.apply_pin)
        self.btn_cancel_pin.clicked.connect(self.toggle_pin_panel)

    def load_pin(self):
        try:
            os.makedirs(os.path.dirname(PIN_PATH), exist_ok=True)
            if os.path.exists(PIN_PATH):
                with open(PIN_PATH, "r", encoding="utf-8") as f:
                    return f.read().strip() or "1234"
        except Exception:
            pass
        return "1234"

    def save_pin(self, pin):
        try:
            os.makedirs(os.path.dirname(PIN_PATH), exist_ok=True)
            with open(PIN_PATH, "w", encoding="utf-8") as f:
                f.write(pin)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pin_panel.isVisible():
            self.pin_panel.move((self.width() - self.pin_panel.width()) // 2, 
                               (self.height() - self.pin_panel.height()) // 2)

    def toggle_pin_panel(self):
        self.pin_panel.setVisible(not self.pin_panel.isVisible())
        if self.pin_panel.isVisible():
            self.pin_panel.raise_()
            self.pin_panel.move((self.width() - self.pin_panel.width()) // 2,
                               (self.height() - self.pin_panel.height()) // 2)

    def apply_pin(self):
        old_pin = self.old_pin_input.text().strip()
        new_pin = self.new_pin_input.text().strip()
        if old_pin != self.admin_pin:
            self.pin_status.setText("❌ Mật khẩu cũ không đúng. Vui lòng kiểm tra lại.")
            self.pin_status.setStyleSheet("color: #ffd6d6; font-size: 14px; font-weight: bold;")
            return
        if len(new_pin) < 4:
            self.pin_status.setText("❌ Mật khẩu mới phải có tối thiểu 4 ký tự.")
            self.pin_status.setStyleSheet("color: #ffd6d6; font-size: 14px; font-weight: bold;")
            return
        self.admin_pin = new_pin
        self.save_pin(new_pin)
        self.old_pin_input.clear()
        self.new_pin_input.clear()
        self.pin_status.setText("✅ Đã cập nhật PIN quản lý thành công.")
        self.pin_status.setStyleSheet("color: #98f5b1; font-size: 14px; font-weight: bold;")
        self.toggle_pin_panel()

    def require_pin(self, on_success):
        dialog = PinDialog(self, title="Khóa quản lý", subtitle="Nhập mã PIN để vào phần quản lý:")
        while True:
            result = dialog.exec()
            if result != 1:
                return
            if dialog.pin() == self.admin_pin:
                on_success()
                return
            dialog.set_error("❌ Mã PIN không đúng, vui lòng thử lại.")

    def shutdown_app(self):
        dialog = PinDialog(self, title="Tắt máy", subtitle="Nhập mã PIN để tắt ứng dụng:")
        while True:
            result = dialog.exec()
            if result != 1:
                return
            if dialog.pin() == self.admin_pin:
                self.close()
                return
            dialog.set_error("❌ Mã PIN không đúng.")

    def open_attendance(self):
        self.require_pin(lambda: self.open_page(AttendancePage, 'att'))

    def open_students(self):
        self.require_pin(lambda: self.open_page(StudentPage, 'st'))

    def open_crud(self):
        self.require_pin(lambda: self.open_page(CrudPage, 'st'))

    def open_stats(self):
        self.stats_win = StatisticsPage()
        self.stats_win.showMaximized()
    
    def open_page(self, page_class, attr_name):
        page = page_class()
        setattr(self, attr_name, page)
        page.showFullScreen()