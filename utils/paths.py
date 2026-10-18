import os
import sys

def resource_path(relative_path):
    """ Lấy đường dẫn tuyệt đối đến tài nguyên, hoạt động cho cả .py và .exe """
    if getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS'):
        # Nếu là file .exe (Nuitka / PyInstaller)
        # sys.executable là đường dẫn đến file main.exe
        base_path = os.path.dirname(sys.executable)
    else:
        # Nếu đang chạy code .py trong VSC
        # Lấy thư mục gốc (lùi ra 1 cấp từ folder utils)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    return os.path.join(base_path, relative_path)