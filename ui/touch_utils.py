# ==================== [TOUCH INPUT CORE] ====================
import os
from PyQt6.QtWidgets import QDialog, QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QComboBox, QTimeEdit, QGroupBox
from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6.QtGui import QImage, QPixmap
from PyQt6 import uic
from utils.paths import resource_path
from camera import FaceMeshCamera
from utils.face_utils import face_file_name, save_face_encoding, landmarks_to_vector
from database import log_history
import numpy as np

PIN_PATH = resource_path("data/pin.txt")


class TouchLineEdit(QLineEdit):
    """Ô nhập liệu dùng cho màn hình chạm"""
    pass


class TouchComboBox(QComboBox):
    """Combo box dùng trên màn hình chạm"""
    pass


class InfoDialog(QDialog):
    def __init__(self, parent=None, title="Thông báo", text="", icon="ℹ️"):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(460, 220)

        self.container = QFrame(self)
        self.container.setObjectName("info_dialog_container")
        self.container.setStyleSheet("""
            QFrame#info_dialog_container {
                background-color: #071622;
                border: 2px solid #ffffff;
                border-radius: 20px;
            }
        """)
        self.container.setGeometry(0, 0, 460, 220)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel(text)
        self.text_label.setStyleSheet("color: #dce7ee; font-size: 16px;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)

        ok_btn = QPushButton("✅ ĐÓNG")
        ok_btn.setStyleSheet("background-color: #1f6f4e; color: white; font-weight: bold; padding: 12px 20px; border-radius: 10px; font-size: 16px;")
        ok_btn.clicked.connect(self.accept)

        layout.addWidget(title_label)
        layout.addWidget(self.text_label)
        layout.addWidget(ok_btn, alignment=Qt.AlignmentFlag.AlignCenter)


class ConfirmDialog(QDialog):
    def __init__(self, parent=None, title="Xác nhận", text="Bạn có chắc chắn muốn tiếp tục?"):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(460, 220)

        self.container = QFrame(self)
        self.container.setObjectName("confirm_dialog_container")
        self.container.setStyleSheet("""
            QFrame#confirm_dialog_container {
                background-color: #071622;
                border: 2px solid #ffffff;
                border-radius: 20px;
            }
        """)
        self.container.setGeometry(0, 0, 460, 220)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel(text)
        self.text_label.setStyleSheet("color: #dce7ee; font-size: 16px;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)

        btn_row = QHBoxLayout()
        yes_btn = QPushButton("✅ CÓ")
        yes_btn.setStyleSheet("background-color: #1f6f4e; color: white; font-weight: bold; padding: 12px 18px; border-radius: 10px; font-size: 16px;")
        no_btn = QPushButton("⬅ KHÔNG")
        no_btn.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 12px 18px; border-radius: 10px; font-size: 16px;")
        yes_btn.clicked.connect(self.accept)
        no_btn.clicked.connect(self.reject)
        btn_row.addWidget(yes_btn)
        btn_row.addWidget(no_btn)

        layout.addWidget(title_label)
        layout.addWidget(self.text_label)
        layout.addLayout(btn_row)


class PinDialog(QDialog):
    def __init__(self, parent=None, title="Khóa quản lý", subtitle="Nhập mã PIN để tiếp tục:"):
        super().__init__(parent)
        uic.loadUi(resource_path('ui_QT/pin_dialog.ui'), self)
        
        # Cập nhật tiêu đề và phụ đề
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
        
        # Kết nối sự kiện
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.pin_input.setFocus()

    def set_error(self, text):
        self.error_label.setText(text)

    def pin(self):
        return self.pin_input.text().strip()


class TimeRangeDialog(QDialog):
    def __init__(self, parent=None, student_id=None, student_name=None, 
                 checkin_start=None, checkin_end=None, late_end=None):
        super().__init__(parent)
        uic.loadUi(resource_path('ui_QT/time_range_dialog.ui'), self)
        
        self.student_id = student_id
        
        # Cập nhật tên học sinh
        self.name_label.setText(f"Học sinh: {student_name}" if student_name else "Chọn học sinh để thiết lập")
        
        # Thiết lập thời gian
        self.checkin_start_edit.setTime(self._parse_time(checkin_start, "06:00"))
        self.checkin_end_edit.setTime(self._parse_time(checkin_end, "07:30"))
        self.late_end_edit.setTime(self._parse_time(late_end, "08:00"))
        self.late_start_edit.setTime(self.checkin_end_edit.time())
        
        # Kết nối sự kiện
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        # Cập nhật thời gian vắng mặt khi thay đổi
        self.late_end_edit.timeChanged.connect(self._update_absent_time)
        self._update_absent_time()
        
    def _parse_time(self, value, default):
        if value:
            try:
                if isinstance(value, str):
                    if ":" in value:
                        parts = value.split(":")
                        return QTime(int(parts[0]), int(parts[1]))
                    return QTime(int(value), 0)
                return QTime(value.hour(), value.minute())
            except:
                pass
        parts = default.split(":")
        return QTime(int(parts[0]), int(parts[1]))
    
    def _update_absent_time(self):
        self.absent_time_label.setText(f"⚠️ Sau: {self.late_end_edit.time().toString('HH:mm')}")
    
    def get_checkin_start(self):
        return self.checkin_start_edit.time().toString("HH:mm")
    
    def get_checkin_end(self):
        return self.checkin_end_edit.time().toString("HH:mm")
    
    def get_late_end(self):
        return self.late_end_edit.time().toString("HH:mm")


class FaceCaptureDialog(QDialog):
    def __init__(self, student_id, student_name, parent=None):
        super().__init__(parent)
        uic.loadUi(resource_path('ui_QT/face_capture_dialog.ui'), self)
        
        self.student_id = student_id
        self.student_name = student_name
        self.capture_ready = False
        
        # Khởi tạo camera
        from camera import FaceMeshCamera
        self.cam = FaceMeshCamera()
        
        # Kết nối sự kiện
        self.btn_back.clicked.connect(self.reject)
        self.btn_capture.clicked.connect(self.capture_now)
        
        # Timer cập nhật khung hình
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(80)

    def update_frame(self):
        frame, _landmarks, face_crop = self.cam.get_frame()
        if frame is None:
            return
        self.capture_ready = face_crop is not None
        h, w, _ = frame.shape
        rgb_frame = QImage(frame.data, w, h, 3 * w, QImage.Format.Format_BGR888)
        self.cam_label.setPixmap(QPixmap.fromImage(rgb_frame).scaled(
            self.cam_label.width(), self.cam_label.height(), 
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
        ))
        if self.capture_ready:
            self.status_label.setText("📷 Đã phát hiện khuôn mặt, hãy nhấn CHỤP MẶT")
        else:
            self.status_label.setText("📷 Hãy đặt mặt vào khung camera rồi nhấn CHỤP")

    def capture_now(self):
        if not self.capture_ready:
            self.status_label.setText("⚠️ Chưa phát hiện khuôn mặt hợp lệ.")
            return
        frame, landmarks, face_crop = self.cam.get_frame()
        if frame is None or face_crop is None:
            self.status_label.setText("⚠️ Không thể chụp hình lúc này.")
            return

        from utils.face_utils import save_face_encoding, landmarks_to_vector, face_file_name
        import numpy as np
        import os
        face_dir = resource_path("data/faces")
        os.makedirs(face_dir, exist_ok=True)
        file_path = resource_path(f"data/faces/{face_file_name(self.student_id, self.student_name)}")
        saved_any = False
        for _ in range(3):
            if save_face_encoding(file_path, face_crop):
                saved_any = True
        if not saved_any:
            vec = landmarks_to_vector(landmarks) if landmarks else np.array([])
            np.save(file_path, vec)
        log_history(self.student_id, "Thêm khuôn mặt", f"Lưu khuôn mặt: {self.student_name}")
        self.timer.stop()
        self.cam.release()
        self.accept()

    def closeEvent(self, event):
        self.timer.stop()
        if self.cam is not None:
            self.cam.release()
        event.accept()