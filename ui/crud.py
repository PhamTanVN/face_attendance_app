# ==================== [CRUD PAGE] ====================
from PyQt6.QtWidgets import (QWidget, QTableWidgetItem, QHeaderView, QDialog)
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QTimer, QEasingCurve
from PyQt6 import uic
import sqlite3
import os
from utils.paths import resource_path
from utils.face_utils import face_file_name, delete_face_files, rename_face_file
from database import log_history, load_history
from camera import FaceMeshCamera
from ui.touch_utils import (InfoDialog, ConfirmDialog, TouchLineEdit, 
                           TimeRangeDialog, FaceCaptureDialog)  
                           
DB_PATH = resource_path("data/students.db")


class CrudPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path('ui_QT/crud.ui'), self)
        
        # Kết nối sự kiện
        self.btn_back.clicked.connect(self.close)
        self.btn_add.clicked.connect(self.add_student)
        self.btn_edit.clicked.connect(self.edit_student)
        self.btn_del.clicked.connect(self.delete_student)
        self.btn_face.clicked.connect(self.save_face)
        self.btn_time.clicked.connect(self.open_time_range_dialog)
        self.search_input.textChanged.connect(self.load_students)
        self.table.cellClicked.connect(self.fill_form)
        
        # Khởi tạo
        self.load_students()
        self.load_history()
        
        # Animation cho thông báo
        self.anim = QPropertyAnimation(self.notif_panel, b"geometry")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    def show_toast(self, text):
        self.notif_label.setText(text)
        self.notif_panel.raise_()
        self.anim.setStartValue(QRect(390, -100, 400, 70))
        self.anim.setEndValue(QRect(390, 20, 400, 70))
        self.anim.start()
        QTimer.singleShot(2500, self.hide_toast)

    def hide_toast(self):
        self.anim.setStartValue(QRect(390, 20, 400, 70))
        self.anim.setEndValue(QRect(390, -100, 400, 70))
        self.anim.start()

    def show_msg(self, title, text, icon="ℹ️"):
        dialog = InfoDialog(self, title=title, text=text, icon=icon)
        dialog.exec()

    def load_students(self):
        self.table.setRowCount(0)
        search_text = self.search_input.text().strip()
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT id, name, class_name, checkin_start, checkin_end, late_end
            FROM students 
            WHERE name LIKE ?
        """, (f"%{search_text}%",)).fetchall()
        
        for r, row in enumerate(rows):
            self.table.insertRow(r)
            
            id_item = QTableWidgetItem(str(row[0]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 0, id_item)
            
            name_item = QTableWidgetItem(str(row[1]) if row[1] else "")
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(r, 1, name_item)
            
            class_item = QTableWidgetItem(str(row[2]) if row[2] else "")
            class_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, class_item)
            
            checkin_start = row[3] if row[3] else "06:00"
            checkin_end = row[4] if row[4] else "07:30"
            late_end = row[5] if row[5] else "08:00"
            
            checkin_item = QTableWidgetItem(f"{checkin_start} - {checkin_end}")
            checkin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 3, checkin_item)
            
            late_item = QTableWidgetItem(f"{checkin_end} - {late_end}")
            late_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 4, late_item)
            
            time_range_text = f"Đúng: {checkin_start}-{checkin_end}\nMuộn: {checkin_end}-{late_end}"
            time_range_item = QTableWidgetItem(time_range_text)
            time_range_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 5, time_range_item)
            
        conn.close()

    def load_history(self):
        self.history_table.setRowCount(0)
        try:
            rows = load_history(50)
            for r, (created_at, action, details) in enumerate(rows):
                self.history_table.insertRow(r)
                for c, val in enumerate((created_at, action, details)):
                    item = QTableWidgetItem(str(val) if val else "")
                    item.setForeground(Qt.GlobalColor.black)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.history_table.setItem(r, c, item)
        except Exception as e:
            print(f"Lỗi lịch sử: {e}")

    def fill_form(self, row, _column):
        self.name_input.setText(self.table.item(row, 1).text())
        self.class_input.setText(self.table.item(row, 2).text())

    def add_student(self):
        n, c = self.name_input.text().strip(), self.class_input.text().strip()
        if n and c:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute(
                "INSERT INTO students (name, class_name, checkin_start, checkin_end, late_end) VALUES (?, ?, ?, ?, ?)",
                (n, c, "06:00", "07:30", "08:00")
            )
            student_id = cursor.lastrowid
            conn.commit()
            conn.close()
            log_history(student_id, "Thêm học sinh", f"{n} - {c}")
            self.load_students()
            self.load_history()
            self.clear_inputs()
            self.show_toast("✅ THÊM HỌC SINH THÀNH CÔNG!")
        else:
            self.show_msg("Lỗi", "Vui lòng nhập Tên và Lớp!", "⚠️")

    def edit_student(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_msg("Lỗi", "Hãy chọn một học sinh trong bảng để sửa!", "⚠️")
            return
        sid = self.table.item(row, 0).text()
        old_name = self.table.item(row, 1).text()
        old_class = self.table.item(row, 2).text()
        n, c = self.name_input.text().strip(), self.class_input.text().strip()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE students SET name=?, class_name=? WHERE id=?", (n, c, sid))
        conn.commit()
        conn.close()
        rename_face_file(sid, old_name, n)
        log_history(sid, "Chỉnh sửa học sinh", f"{old_name}->{n}, {old_class}->{c}")
        self.load_students()
        self.load_history()
        self.show_toast("✅ CẬP NHẬT THÔNG TIN THÀNH CÔNG!")

    def delete_student(self):
        row = self.table.currentRow()
        if row >= 0:
            confirm = ConfirmDialog(self, title="Xác nhận", text="Bạn có chắc muốn xoá học sinh này?")
            if confirm.exec() == 1:
                sid = self.table.item(row, 0).text()
                student_name = self.table.item(row, 1).text()
                student_class = self.table.item(row, 2).text()
                delete_face_files(sid)
                conn = sqlite3.connect(DB_PATH)
                conn.execute("DELETE FROM students WHERE id=?", (sid,))
                conn.commit()
                conn.close()
                log_history(sid, "Xóa học sinh", f"{student_name} - {student_class}")
                self.load_students()
                self.load_history()
                self.clear_inputs()
                self.show_toast("🗑️ ĐÃ XOÁ HỌC SINH VÀ MẶT LIÊN QUAN!")
        else:
            self.show_msg("Lỗi", "Hãy chọn học sinh cần xoá!", "⚠️")

    def clear_inputs(self):
        self.name_input.clear()
        self.class_input.clear()

    def save_face(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_msg("Lỗi", "Bạn phải nhấn CHỌN học sinh trước!", "⚠️")
            return
        student_id = self.table.item(row, 0).text()
        student_name = self.table.item(row, 1).text()
        dialog = FaceCaptureDialog(student_id, student_name, self)
        dialog.exec()
        self.show_toast(f"✅ ĐÃ LƯU MẶT: {student_name}")

    def open_time_range_dialog(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_msg("Lỗi", "Hãy chọn một học sinh trong bảng!", "⚠️")
            return
        
        student_id = self.table.item(row, 0).text()
        student_name = self.table.item(row, 1).text()
        
        checkin_start = "06:00"
        checkin_end = "07:30"
        late_end = "08:00"
        
        checkin_item = self.table.item(row, 3)
        if checkin_item:
            parts = checkin_item.text().split(" - ")
            if len(parts) == 2:
                checkin_start = parts[0]
                checkin_end = parts[1]
        
        late_item = self.table.item(row, 4)
        if late_item:
            parts = late_item.text().split(" - ")
            if len(parts) == 2:
                late_end = parts[1]
        
        dialog = TimeRangeDialog(
            self,
            student_id=student_id,
            student_name=student_name,
            checkin_start=checkin_start,
            checkin_end=checkin_end,
            late_end=late_end
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("""
                    UPDATE students
                    SET checkin_start = ?,
                        checkin_end = ?,
                        late_end = ?
                    WHERE id = ?
                """, (
                    dialog.get_checkin_start(),
                    dialog.get_checkin_end(),
                    dialog.get_late_end(),
                    student_id
                ))
                conn.commit()
                conn.close()
                
                log_history(
                    student_id,
                    "Cập nhật khung giờ",
                    f"{student_name}: Đúng: {dialog.get_checkin_start()} - {dialog.get_checkin_end()} | Muộn: {dialog.get_checkin_end()} - {dialog.get_late_end()}"
                )
                
                self.load_students()
                self.load_history()
                self.show_toast("✓ ĐÃ CẬP NHẬT KHUNG GIỜ")
                
            except Exception as e:
                print("Lỗi cập nhật khung giờ:", e)
                self.show_msg("Lỗi", "Không thể cập nhật khung giờ.", "⚠️")