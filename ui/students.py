# ==================== [STUDENT PAGE] ====================
from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QFileDialog
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QTimer
from PyQt6 import uic
import sqlite3
import pandas as pd
from datetime import datetime
from utils.paths import resource_path

DB_PATH = resource_path("data/students.db")


class StudentPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path('ui_QT/students.ui'), self)
        
        # Kết nối sự kiện
        self.btn_back.clicked.connect(self.close)
        self.btn_export_excel.clicked.connect(self.export_today_excel)
        self.search_input.textChanged.connect(self.load)
        
        # Animation cho thông báo
        self.anim = QPropertyAnimation(self.notif_panel, b"geometry")
        self.anim.setDuration(500)
        
        self.load()

    def show_toast(self, text):
        self.notif_label.setText(text)
        self.notif_panel.raise_()
        self.anim.setStartValue(QRect(340, -100, 400, 70))
        self.anim.setEndValue(QRect(340, 20, 400, 70))
        self.anim.start()
        QTimer.singleShot(2500, self.hide_toast)

    def hide_toast(self):
        self.anim.setStartValue(QRect(340, 20, 400, 70))
        self.anim.setEndValue(QRect(340, -100, 400, 70))
        self.anim.start()

    def get_attendance_status(self, last_attendance, checkin_start, checkin_end, late_end):
        if not last_attendance or last_attendance == "-":
            now = datetime.now()
            late_end_time = datetime.strptime(late_end, "%H:%M").time()
            if now.time() > late_end_time:
                return "Vắng mặt"
            return "Chưa điểm danh"
        
        try:
            parts = last_attendance.split(" ")
            if len(parts) >= 2:
                date_part = parts[0]
                time_part = parts[1]
                today = datetime.now().strftime("%d/%m/%Y")
                if date_part != today:
                    return "Chưa điểm danh"
                
                if ":" in time_part:
                    h, m, _ = time_part.split(":")
                    check_time = datetime.strptime(f"{h}:{m}", "%H:%M").time()
                    start = datetime.strptime(checkin_start, "%H:%M").time()
                    on_time_end = datetime.strptime(checkin_end, "%H:%M").time()
                    late_end_time = datetime.strptime(late_end, "%H:%M").time()
                    
                    if check_time >= start and check_time <= on_time_end:
                        return "Có mặt"
                    elif check_time > on_time_end and check_time <= late_end_time:
                        return "Muộn"
                    else:
                        return "Vắng mặt (quá giờ)"
        except:
            pass
        return "Vắng mặt"

    def load(self):
        try:
            txt = self.search_input.text().strip()
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute("""
                SELECT name, class_name, total_sessions, late_sessions, 
                       last_attendance, checkin_start, checkin_end, late_end
                FROM students 
                WHERE name LIKE ?
            """, (f"%{txt}%",)).fetchall()
            
            self.table.setRowCount(len(rows))
            today = datetime.now().strftime("%d/%m/%Y")
            
            for r, row in enumerate(rows):
                name = str(row[0]) if row[0] else "-"
                class_name = str(row[1]) if row[1] else "-"
                total_sessions = str(row[2]) if row[2] is not None else "0"
                late_sessions = str(row[3]) if row[3] is not None else "0"
                last_attendance = str(row[4]) if row[4] else "-"
                checkin_start = row[5] if row[5] else "06:00"
                checkin_end = row[6] if row[6] else "07:30"
                late_end = row[7] if row[7] else "08:00"
                
                self.table.setItem(r, 0, QTableWidgetItem(name))
                self.table.setItem(r, 1, QTableWidgetItem(class_name))
                self.table.setItem(r, 2, QTableWidgetItem(total_sessions))
                self.table.setItem(r, 3, QTableWidgetItem(late_sessions))
                self.table.setItem(r, 4, QTableWidgetItem(today))
                
                status = self.get_attendance_status(last_attendance, checkin_start, checkin_end, late_end)
                status_item = QTableWidgetItem(status)
                if "Có mặt" in status:
                    status_item.setBackground(Qt.GlobalColor.green)
                elif "Muộn" in status:
                    status_item.setBackground(Qt.GlobalColor.yellow)
                else:
                    status_item.setBackground(Qt.GlobalColor.red)
                self.table.setItem(r, 5, status_item)
                
            conn.close()
        except Exception as e:
            print(f"Lỗi: {e}")

    def export_today_excel(self):
        try:
            today = datetime.now()
            date_str = today.strftime("%d%m%Y")
            default_path = resource_path(f"data/diem_danh_{date_str}.xlsx")
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Lưu file điểm danh Excel", default_path, "Excel Files (*.xlsx)"
            )
            if not file_path:
                return
            
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute("""
                SELECT id, name, class_name, last_attendance,
                       checkin_start, checkin_end, late_end
                FROM students
                ORDER BY name
            """).fetchall()
            conn.close()
            
            if not rows:
                self.show_toast("⚠ KHÔNG CÓ DỮ LIỆU")
                return
            
            data = []
            for idx, row in enumerate(rows, 1):
                name = row[1] or ""
                class_name = row[2] or ""
                last_attendance = row[3] or ""
                checkin_start = row[4] if row[4] else "06:00"
                checkin_end = row[5] if row[5] else "07:30"
                late_end = row[6] if row[6] else "08:00"
                
                status = self.get_attendance_status(last_attendance, checkin_start, checkin_end, late_end)
                
                data.append({
                    "STT": idx,
                    "Họ và tên": name,
                    "Lớp": class_name,
                    "Trạng thái điểm danh": status,
                    "Thời gian điểm danh": last_attendance if last_attendance else "Chưa điểm danh",
                    "Đúng giờ (từ - đến)": f"{checkin_start} - {checkin_end}",
                    "Muộn (từ - đến)": f"{checkin_end} - {late_end}"
                })
            
            df = pd.DataFrame(data)
            
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Điểm danh', index=False)
                worksheet = writer.sheets['Điểm danh']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            self.show_toast(f"✅ ĐÃ XUẤT EXCEL: diem_danh_{date_str}.xlsx")
            
        except Exception as e:
            print("Lỗi xuất Excel:", e)
            self.show_toast("❌ LỖI XUẤT EXCEL!")