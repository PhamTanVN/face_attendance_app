# ==================== [ATTENDANCE PAGE] ====================
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QRect, QEasingCurve, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6 import uic
from camera import FaceMeshCamera
from utils.face_utils import distance, find_face_file, load_face_encodings, compare_faces, encode_face_from_image
from utils.paths import resource_path
from database import log_history
from ui.touch_utils import PIN_PATH, PinDialog
import cv2, os, numpy as np, sqlite3, time
from datetime import datetime

FACE_DIR = resource_path("data/faces")
DB_PATH = resource_path("data/students.db")


class AttendancePage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path('ui_QT/attendance.ui'), self)
        
        # Kết nối sự kiện
        self.btn_back.clicked.connect(self.confirm_close)
        
        # Khởi tạo camera và dữ liệu
        self.cam = FaceMeshCamera()
        self.known_faces = self.load_known_faces()
        
        self.last_scan_time = {}
        self.match_history = []
        self.last_confirmed_student = None
        self.last_confirmed_time = 0.0
        self.cooldown_seconds = 8.0
        self.frame_counter = 0
        self.is_showing_notif = False
        
        # Animation cho các panel
        self.guide_anim = QPropertyAnimation(self.guide_notif_panel, b"geometry")
        self.guide_anim.setDuration(600)
        self.guide_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        self.anim = QPropertyAnimation(self.notif_panel, b"geometry")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # === TỐI ƯU: Tạo QPixmap cache để tránh tạo mới mỗi frame ===
        self.current_pixmap = QPixmap()
        self.frame_width = 0
        self.frame_height = 0
        
        # Timer cập nhật khung hình
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(66)  # ~15 FPS
        
        QTimer.singleShot(500, self.show_guide_notif)

    def load_known_faces(self):
        faces = []
        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute("SELECT id, name, class_name FROM students").fetchall()
            conn.close()
            for sid, name, cname in rows:
                path = find_face_file(sid, name)
                if path and os.path.exists(path):
                    vec = load_face_encodings(path)
                    if vec is None:
                        continue
                    faces.append({"id": sid, "name": name, "class": cname, "vector": vec})
        except:
            pass
        return faces

    def show_late_notif(self, name):
        if self.is_showing_notif:
            return
        self.is_showing_notif = True
        self.notif_label.setText(f"⚠️ {name.upper()}\nĐI HỌC MUỘN!")
        self.anim.setStartValue(QRect(420, -120, 400, 100))
        self.anim.setEndValue(QRect(420, 40, 400, 100))
        self.anim.start()
        QTimer.singleShot(2500, self.hide_late_notif)

    def hide_late_notif(self):
        self.anim.setStartValue(QRect(420, 40, 400, 100))
        self.anim.setEndValue(QRect(420, -120, 400, 100))
        self.anim.start()
        self.is_showing_notif = False

    def show_guide_notif(self):
        self.guide_anim.setStartValue(QRect(420, -120, 400, 100))
        self.guide_anim.setEndValue(QRect(420, 40, 400, 100))
        self.guide_anim.start()
        QTimer.singleShot(4000, self.hide_guide_notif)

    def hide_guide_notif(self):
        self.guide_anim.setStartValue(QRect(420, 40, 400, 100))
        self.guide_anim.setEndValue(QRect(420, -120, 400, 100))
        self.guide_anim.start()

    def _should_confirm_match(self, student_id, match_distance, is_encoding_match):
        self.match_history.append((student_id, match_distance))
        if len(self.match_history) > 8:
            self.match_history.pop(0)
        recent_scores = [d for sid, d in self.match_history if sid == student_id]
        if len(recent_scores) < 3:
            return False
        avg_distance = float(np.mean(recent_scores[-3:]))
        threshold = 0.55 if is_encoding_match else 0.35
        return avg_distance <= threshold

    def update_frame(self):
        frame, landmarks, face_crop = self.cam.get_frame()
        if frame is None:
            return
        
        self.frame_counter += 1
        should_process_face = (self.frame_counter % 6) == 0
        
        # === TỐI ƯU: Vẽ text trực tiếp lên frame ===
        cv2.putText(frame, datetime.now().strftime("%H:%M:%S"), (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        
        if landmarks and should_process_face:
            current_img_encoding = None
            if face_crop is not None:
                current_img_encoding = encode_face_from_image(face_crop)
            match_s, min_dist = None, 1.0
            for s in self.known_faces:
                known_vec = s.get("vector")
                if current_img_encoding is not None and known_vec is not None:
                    d = compare_faces(current_img_encoding, known_vec)
                    if d is None:
                        d = distance(current_img_encoding, known_vec)
                else:
                    d = None
                if d is not None and d < min_dist:
                    min_dist, match_s = d, s
            if match_s and self._should_confirm_match(match_s['id'], min_dist, current_img_encoding is not None):
                sid = match_s['id']
                now = time.time()
                if self.last_confirmed_student == sid and (now - self.last_confirmed_time) < self.cooldown_seconds:
                    self.status_label.setText(f"⏳ {match_s['name'].upper()} ĐÃ ĐƯỢC ĐIỂM DANH")
                    self.status_label.setStyleSheet("color: #f39c12; font-size: 22px; font-weight: bold;")
                elif sid not in self.last_scan_time or (now - self.last_scan_time[sid] > self.cooldown_seconds):
                    self.last_scan_time[sid] = now
                    self.last_confirmed_student = sid
                    self.last_confirmed_time = now
                    msg, color, late_flag = self.save_attendance_logic(match_s)
                    self.status_label.setText(msg)
                    self.status_label.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: bold;")
                    if late_flag:
                        self.show_late_notif(match_s['name'])
                else:
                    self.status_label.setText(f"⏳ {match_s['name'].upper()} ĐÃ ĐƯỢC ĐIỂM DANH")
                    self.status_label.setStyleSheet("color: #f39c12; font-size: 22px; font-weight: bold;")
            else:
                self.status_label.setText("⚠️ KHÔNG XÁC ĐỊNH")
                self.status_label.setStyleSheet("color: #e67e22; font-size: 24px; font-weight: bold;")

        # === TỐI ƯU: Hiển thị frame với cache ===
        h, w, _ = frame.shape
        
        # Chỉ tạo QImage mới khi cần
        img = QImage(frame.data, w, h, 3 * w, QImage.Format.Format_BGR888)
        
        # Tạo pixmap và scale một lần
        pixmap = QPixmap.fromImage(img)
        
        # Scale với FastTransformation để tăng tốc
        scaled_pixmap = pixmap.scaled(
            self.cam_container.width(), 
            self.cam_container.height(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.FastTransformation
        )
        
        # Cập nhật label
        self.cam_container.setPixmap(scaled_pixmap)

    def save_attendance_logic(self, s):
        try:
            conn = sqlite3.connect(DB_PATH)
            res = conn.execute("""
                SELECT checkin_start, checkin_end, late_end 
                FROM students WHERE id=?
            """, (s['id'],)).fetchone()
            
            checkin_start = res[0] if res[0] else "06:00"
            checkin_end = res[1] if res[1] else "07:30"
            late_end = res[2] if res[2] else "08:00"
            
            time_now = datetime.now()
            time_str = time_now.strftime("%H:%M:%S")
            date_str = time_now.strftime("%d/%m/%Y")
            
            current_time = time_now.time()
            late_end_time = datetime.strptime(late_end, "%H:%M").time()
            
            if current_time > late_end_time:
                conn.close()
                return f"❌ {s['name'].upper()} - VẮNG MẶT (QUÁ GIỜ)", "#c0392b", False
            
            checkin_end_time = datetime.strptime(checkin_end, "%H:%M").time()
            is_late = 1 if current_time > checkin_end_time else 0
            
            conn.execute("""
                UPDATE students
                SET total_sessions = total_sessions + 1,
                    late_sessions = late_sessions + ?,
                    last_attendance = ?
                WHERE id = ?
            """, (is_late, f"{date_str} {time_str}", s['id']))
            conn.commit()
            conn.close()
            
            status_text = "THÀNH CÔNG" + (" (MUỘN 🔴)" if is_late else "")
            log_history(s['id'], "Quét học sinh", f"{s['name']} - {date_str} {time_str} - {'MUỘN' if is_late else 'ĐÚNG GIỜ'}")
            return f"✅ {s['name'].upper()} - {status_text}", "#27ae60", (is_late == 1)
            
        except Exception as e:
            print(f"Lỗi điểm danh: {e}")
            return "❌ LỖI DATABASE", "#c0392b", False

    def confirm_close(self):
        dialog = PinDialog(self, title="Khóa quản lý", subtitle="Nhập mã PIN để thoát quét khuôn mặt:")
        if dialog.exec() != 1:
            return
        try:
            current_pin = open(PIN_PATH, "r", encoding="utf-8").read().strip() or "1234"
        except Exception:
            current_pin = "1234"
        if dialog.pin() == current_pin:
            self.close()
        else:
            dialog.set_error("❌ Mã PIN không đúng, vui lòng thử lại.")
            dialog.exec()

    def closeEvent(self, event):
        self.timer.stop()
        if self.cam is not None:
            self.cam.release()
        event.accept()