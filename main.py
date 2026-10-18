import sys
from PyQt6.QtWidgets import QApplication
from ui import HomePage  # Import từ ui package
from database import init_db

# ENTRY POINT: khởi động database trước khi mở giao diện chính
print("Ứng dụng đang khởi động...")
if __name__ == "__main__":
    if not init_db():
        sys.exit(1)

    app = QApplication(sys.argv)
    window = HomePage()
    window.showFullScreen()
    sys.exit(app.exec())