import cv2
import numpy as np
import os
import shutil
import tempfile
import uuid
from utils.paths import resource_path

try:
    import face_recognition
except Exception:
    face_recognition = None

# CAMERA MODULE: khởi tạo camera và phát hiện khuôn mặt bằng face_recognition (ưu tiên), fallback sang Haar Cascade nếu thư viện không có

def _make_ascii_copy(src_path: str) -> str:
    if all(ord(ch) < 128 for ch in src_path):
        return src_path

    target_path = os.path.join(tempfile.gettempdir(), f"cv2_cascade_{uuid.uuid4().hex}.xml")
    shutil.copyfile(src_path, target_path)
    return target_path


def _load_cascade(cascade_name: str):
    candidates = [
        resource_path(os.path.join("data", cascade_name)),
        os.path.join(cv2.data.haarcascades, cascade_name)
    ]

    for path in candidates:
        if not path or not os.path.exists(path):
            continue

        safe_path = _make_ascii_copy(path)
        classifier = cv2.CascadeClassifier(safe_path)
        if not classifier.empty():
            return classifier

    raise RuntimeError(f"Failed to load cascade classifier: {cascade_name}")


class FaceMeshCamera:
    # Class chính dùng để mở camera, phát hiện khuôn mặt và trả về khung hình + crop mặt
    def __init__(self):
        self.cap = None
        self.camera_ready = False
        self.face_cascade = None
        self.frame_counter = 0
        self.detect_interval = 3
        self.cached_face_rect = None
        self.frames_without_face = 0
        self.cached_landmarks = None
        self._open_camera()
        if face_recognition is None:
            self.face_cascade = _load_cascade('haarcascade_frontalface_default.xml')

    def _open_camera(self):
        candidates = [
            (0, cv2.CAP_DSHOW),
            (0, cv2.CAP_MSMF),
            (0, cv2.CAP_ANY),
            (1, cv2.CAP_DSHOW),
            (1, cv2.CAP_MSMF),
            (1, cv2.CAP_ANY),
        ]

        for index, backend in candidates:
            try:
                cap = cv2.VideoCapture(index, backend)
            except Exception:
                continue

            if cap is None or not cap.isOpened():
                continue

            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FPS, 15)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap = cap
            self.camera_ready = True
            return

        self.cap = cv2.VideoCapture(0)
        self.camera_ready = self.cap.isOpened()
        if self.camera_ready:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 15)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
    def get_landmarks_from_face(self, frame, face_rect):
        """Trích xuất các mốc khuôn mặt (góc và điểm chính) từ hình chữ nhật khuôn mặt đã phát hiện"""
        x, y, w, h = face_rect
        # Tạo các mốc giả lập tại góc hình chữ nhật và các điểm chính
        landmarks_data = type('obj', (object,), {
            'landmark': []
        })()
        
        # Tạo 468 mốc (khớp với định dạng MediaPipe FaceMesh)
        # Hiện tại dùng các mốc đơn giản dựa trên hình chữ nhật khuôn mặt
        center_x, center_y = x + w // 2, y + h // 2
        
        # Tạo các mốc phân bố trên toàn bộ khuôn mặt
        landmarks_list = []
        for i in range(468):
            # Phân bố các mốc trên vùng khuôn mặt
            lm_x = x + (i % 30) * (w / 30)
            lm_y = y + (i // 30) * (h / 16)
            lm_z = 0.0
            
            lm_obj = type('obj', (object,), {
                'x': (lm_x / frame.shape[1]),  # Chuẩn hóa
                'y': (lm_y / frame.shape[0]),
                'z': lm_z
            })()
            landmarks_list.append(lm_obj)
        
        landmarks_data.landmark = landmarks_list
        return landmarks_data

    def get_frame(self):
        # Lấy khung hình từ camera, phát hiện khuôn mặt, rồi trả về frame + landmarks + face_crop
        if self.cap is None or not self.cap.isOpened():
            return None, None, None

        ret, frame = self.cap.read()
        if not ret:
            return None, None, None

        frame = cv2.flip(frame, 1)
        self.frame_counter += 1
        landmarks = None
        face_crop = None

        should_detect = self.cached_face_rect is None or self.frame_counter % self.detect_interval == 0
        face_rect = self.cached_face_rect
        if should_detect:
            detection_scale = 0.5
            small_frame = cv2.resize(frame, None, fx=detection_scale, fy=detection_scale,
                                     interpolation=cv2.INTER_AREA)
            detected_rect = None
            if face_recognition is not None:
                rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                boxes = face_recognition.face_locations(rgb, number_of_times_to_upsample=0, model="hog")
                if boxes:
                    top, right, bottom, left = max(boxes, key=lambda b: (b[2] - b[0]) * (b[1] - b[3]))
                    detected_rect = (int(left / detection_scale), int(top / detection_scale),
                                     int((right - left) / detection_scale), int((bottom - top) / detection_scale))

            if detected_rect is None and self.face_cascade is not None:
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(45, 45))
                if len(faces) > 0:
                    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                    detected_rect = (int(x / detection_scale), int(y / detection_scale),
                                     int(w / detection_scale), int(h / detection_scale))

            if detected_rect is not None:
                if detected_rect != self.cached_face_rect:
                    self.cached_landmarks = None
                self.cached_face_rect = detected_rect
                self.frames_without_face = 0
            else:
                self.frames_without_face += 1
                if self.frames_without_face >= 2:
                    self.cached_face_rect = None
                    self.cached_landmarks = None
            face_rect = self.cached_face_rect

        if face_rect is not None:
            x, y, w, h = face_rect
            padding = int(0.15 * max(w, h))
            x0 = max(0, x - padding)
            y0 = max(0, y - padding)
            x1 = min(frame.shape[1], x + w + padding)
            y1 = min(frame.shape[0], y + h + padding)
            face_crop = frame[y0:y1, x0:x1]
            if face_crop.size:
                face_crop = cv2.resize(face_crop, (224, 224))

            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
            if self.cached_landmarks is None:
                self.cached_landmarks = self.get_landmarks_from_face(frame, face_rect)
            landmarks = self.cached_landmarks

        return frame, landmarks, face_crop

    def release(self):
        self.cap.release()