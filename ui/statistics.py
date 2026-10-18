# ==================== [STATISTICS PAGE] ====================
import sqlite3
from PyQt6.QtWidgets import QWidget
from PyQt6 import uic
import pyqtgraph as pg
from utils.paths import resource_path

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOptions(antialias=True)

DB_PATH = resource_path("data/students.db")


class StatisticsPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path('ui_QT/statistics.ui'), self)
        
        # Kết nối sự kiện
        self.class_combo.currentIndexChanged.connect(self.load_chart_by_class)
        
        # Khởi tạo biểu đồ
        self.chart_all = pg.PlotWidget()
        self.chart_all.setBackground('#ffffff')
        self.chart_all.showGrid(x=False, y=True, alpha=0.3)
        self.chart_all.getAxis('bottom').setPen('k')
        self.chart_all.getAxis('bottom').setTextPen('k')
        self.chart_all.getAxis('left').setPen('k')
        self.chart_all.getAxis('left').setTextPen('k')
        
        self.chart_class = pg.PlotWidget()
        self.chart_class.setBackground('#ffffff')
        self.chart_class.showGrid(x=False, y=True, alpha=0.3)
        self.chart_class.getAxis('bottom').setPen('k')
        self.chart_class.getAxis('bottom').setTextPen('k')
        self.chart_class.getAxis('left').setPen('k')
        self.chart_class.getAxis('left').setTextPen('k')
        
        # Thêm các biểu đồ vào layout
        self.tab_all_school.layout().addWidget(self.chart_all)
        self.tab_by_class.layout().addWidget(self.chart_class)
        
        # Tải dữ liệu
        self.load_chart_all_school()
        self.update_class_list()

    def load_chart_all_school(self):
        self.chart_all.clear()
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT class_name, SUM(late_sessions) FROM students WHERE class_name IS NOT NULL AND class_name != '' GROUP BY class_name")
            data = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"Lỗi DB toàn trường: {e}")
            data = []

        if not data:
            classes = ["Chưa có dữ liệu"]
            late_counts = [0]
        else:
            classes = [str(row[0]) for row in data]
            late_counts = [int(row[1]) if row[1] is not None else 0 for row in data]

        x = list(range(len(classes)))
        bg = pg.BarGraphItem(x=x, height=late_counts, width=0.4, brush='#065279', pen=pg.mkPen('#ffffff', width=2))
        self.chart_all.addItem(bg)

        x_axis = self.chart_all.getAxis('bottom')
        x_axis.setTicks([[(i, name) for i, name in enumerate(classes)]])
        self.chart_all.setXRange(-0.5, max(5.5, len(classes) - 0.5))
        max_y = max(late_counts) if late_counts else 0
        self.chart_all.setYRange(0, max_y + 5 if max_y > 0 else 10)

    def update_class_list(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT class_name FROM students WHERE class_name IS NOT NULL AND class_name != ''")
            classes = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            self.class_combo.clear()
            if classes:
                self.class_combo.addItems(classes)
            else:
                self.class_combo.addItem("Trống")
        except Exception as e:
            print(f"Lỗi tải danh sách lớp: {e}")

    def load_chart_by_class(self):
        self.chart_class.clear()
        current_class = self.class_combo.currentText()
        if not current_class or current_class == "Trống":
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name, late_sessions FROM students WHERE class_name = ? ORDER BY late_sessions DESC", (current_class,))
            data = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"Lỗi tải học sinh: {e}")
            data = []

        if not data:
            return

        students = [row[0] for row in data]
        late_counts = [int(row[1]) for row in data]

        x = list(range(len(students)))
        bg = pg.BarGraphItem(x=x, height=late_counts, width=0.4, brush='#086ca1', pen=pg.mkPen('#ffffff', width=2))
        self.chart_class.addItem(bg)

        x_axis = self.chart_class.getAxis('bottom')
        x_axis.setTicks([[(i, name) for i, name in enumerate(students)]])
        self.chart_class.setXRange(-0.5, max(7.5, len(students) - 0.5))
        max_y = max(late_counts) if late_counts else 0
        self.chart_class.setYRange(0, max_y + 2 if max_y > 0 else 10)