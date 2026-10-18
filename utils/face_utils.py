import glob
import os
import re
import unicodedata
import cv2
import numpy as np
from utils.paths import resource_path

try:
    import face_recognition
except BaseException:
    face_recognition = None

# FACE VECTOR MODULE: tạo encoding và so sánh khuôn mặt bằng vector

def sanitize_filename(value):
    normalized = unicodedata.normalize('NFKD', value)
    stripped = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    cleaned = re.sub(r'[^A-Za-z0-9 _-]', '', stripped)
    cleaned = cleaned.strip().replace(' ', '_')
    cleaned = re.sub(r'[_-]+', '_', cleaned)
    return cleaned or 'unknown'


def face_file_name(student_id, student_name):
    safe_name = sanitize_filename(student_name or '')
    return f"student_{student_id}_{safe_name}.npy"


def find_face_file(student_id, student_name=None):
    face_dir = resource_path('data/faces')
    patterns = []
    if student_name:
        patterns.append(os.path.join(face_dir, face_file_name(student_id, student_name)))
    patterns.append(os.path.join(face_dir, f'student_{student_id}_*.npy'))
    patterns.append(os.path.join(face_dir, f'student_{student_id}.npy'))

    for pattern in patterns:
        for path in glob.glob(pattern):
            if os.path.exists(path):
                return path
    return None


def delete_face_files(student_id):
    face_dir = resource_path('data/faces')
    patterns = [
        os.path.join(face_dir, f'student_{student_id}_*.npy'),
        os.path.join(face_dir, f'student_{student_id}.npy')
    ]
    deleted = []
    for pattern in patterns:
        for path in glob.glob(pattern):
            try:
                os.remove(path)
                deleted.append(path)
            except OSError:
                pass
    return deleted


def rename_face_file(student_id, old_name, new_name):
    old_path = find_face_file(student_id, old_name)
    if not old_path:
        old_path = find_face_file(student_id)
    if not old_path:
        return None

    face_dir = resource_path('data/faces')
    os.makedirs(face_dir, exist_ok=True)
    new_path = os.path.join(face_dir, face_file_name(student_id, new_name))
    if os.path.abspath(old_path) == os.path.abspath(new_path):
        return new_path
    try:
        os.replace(old_path, new_path)
        return new_path
    except OSError:
        return None


def landmarks_to_vector(face_landmarks):
    vector = []
    for lm in face_landmarks.landmark:
        vector.extend([lm.x, lm.y, lm.z])
    return np.array(vector)


def _normalize_encodings(encodings):
    if encodings is None:
        return None
    arr = np.asarray(encodings, dtype=np.float32)
    if arr.ndim == 1:
        if arr.size == 0:
            return None
        return arr.reshape(1, -1)
    if arr.ndim != 2:
        return None
    return arr


def face_distance(v1, v2):
    if v1 is None or v2 is None:
        return 1.0
    if isinstance(v1, (list, tuple, np.ndarray)) and isinstance(v2, (list, tuple, np.ndarray)):
        try:
            a = np.asarray(v1, dtype=np.float32).reshape(-1)
            b = np.asarray(v2, dtype=np.float32).reshape(-1)
            if a.size == 0 or b.size == 0:
                return 1.0
            common = min(a.size, b.size)
            a = a[:common]
            b = b[:common]
            return float(np.linalg.norm(a - b))
        except Exception:
            return 1.0
    return 1.0


def distance(v1, v2):
    return face_distance(v1, v2)


def _fallback_face_descriptor(image):
    if image is None:
        return None
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.astype(np.uint8)

        gray = cv2.equalizeHist(gray)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        resized = cv2.resize(gray, (48, 48), interpolation=cv2.INTER_AREA)

        flat = resized.astype(np.float32).reshape(-1)
        flat_norm = flat / (np.linalg.norm(flat) + 1e-6)

        hist = cv2.calcHist([gray], [0], None, [32], [0, 256]).flatten().astype(np.float32)
        hist = hist / (hist.sum() + 1e-6)

        vector = np.concatenate([flat_norm, hist])
        vector = vector / (np.linalg.norm(vector) + 1e-6)
        return vector.astype(np.float32)
    except Exception:
        return None


def encode_face_from_image(image):
    # Trích xuất vector khuôn mặt từ ảnh crop để dùng cho nhận diện
    if image is None:
        return None
    try:
        if face_recognition is not None:
            if len(image.shape) != 3:
                return None
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(rgb, number_of_times_to_upsample=1, model="hog")
            if boxes:
                encodings = face_recognition.face_encodings(rgb, boxes, num_jitters=1)
                if encodings:
                    return np.asarray(encodings[0], dtype=np.float32)
        return _fallback_face_descriptor(image)
    except Exception:
        return _fallback_face_descriptor(image)


def compare_faces(unknown_encoding, known_encoding):
    unknown = _normalize_encodings(unknown_encoding)
    known = _normalize_encodings(known_encoding)
    if unknown is None or known is None:
        return None
    try:
        common = min(unknown.shape[1], known.shape[1])
        unknown = unknown[:, :common]
        known = known[:, :common]
        distances = np.linalg.norm(known - unknown, axis=1)
        if distances.size == 0:
            return None
        if distances.size > 1:
            ordered = np.sort(distances)
            return float(np.mean(ordered[: min(3, ordered.size)]))
        return float(distances[0])
    except Exception:
        return None


def save_face_encoding(path, image):
    encoding = encode_face_from_image(image)
    if encoding is None:
        return False

    encoding = np.asarray(encoding, dtype=np.float32).reshape(1, -1)
    existing = load_face_encodings(path)
    if existing is None:
        encodings = encoding
    else:
        target_size = max(existing.shape[1], encoding.shape[1])
        existing_pad = existing
        if existing.shape[1] < target_size:
            existing_pad = np.pad(existing, ((0, 0), (0, target_size - existing.shape[1])), mode='constant')
        encoding_pad = encoding
        if encoding.shape[1] < target_size:
            encoding_pad = np.pad(encoding, ((0, 0), (0, target_size - encoding.shape[1])), mode='constant')
        encodings = np.vstack([existing_pad, encoding_pad])

    np.save(path, encodings.astype(np.float32))
    return True


def load_face_encodings(path):
    if not os.path.exists(path):
        return None
    try:
        return _normalize_encodings(np.load(path, allow_pickle=True))
    except Exception:
        return None


def load_face_encoding(path):
    return load_face_encodings(path)