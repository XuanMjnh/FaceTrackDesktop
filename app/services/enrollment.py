from pathlib import Path
import uuid
import numpy as np
from app.services.face_matcher import FaceMatcher


def read_image(path):
    import cv2
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Không đọc được ảnh. Hãy chọn JPG/PNG hợp lệ.")
    return image


class Enrollment:
    def __init__(self, db, engine, image_dir):
        self.db, self.engine, self.image_dir = db, engine, Path(image_dir)

    def inspect(self, path):
        image = read_image(path)
        faces = self.engine.detect(image)
        if len(faces) != 1:
            raise ValueError("Không tìm thấy khuôn mặt hợp lệ" if not faces else "Ảnh có nhiều khuôn mặt. Vui lòng chọn ảnh chỉ có một người.")
        face = faces[0]
        x1, y1, x2, y2 = face.bbox
        if face.confidence < 0.6 or min(x2-x1, y2-y1) < 40:
            raise ValueError("Khuôn mặt quá nhỏ hoặc chất lượng phát hiện thấp; chọn ảnh rõ hơn.")
        duplicate = FaceMatcher(self.db.gallery(), threshold=0.65, margin=0).match(face.embedding)
        return image, face.embedding, duplicate

    def save(self, name, inspected, pid=None, replace_id=None):
        import cv2
        image, embedding, _ = inspected
        created = pid is None
        if created:
            pid = self.db.add_person(name)
        directory = self.image_dir / pid
        target = directory / (str(uuid.uuid4()) + ".jpg")
        try:
            directory.mkdir(parents=True, exist_ok=True)
            ok, encoded = cv2.imencode(".jpg", image)
            if not ok:
                raise ValueError("Không thể mã hóa ảnh")
            encoded.tofile(str(target))
            old = self.db.add_reference(pid, target, embedding, replace_id)
        except Exception:
            target.unlink(missing_ok=True)
            if created:
                self.db.delete_person(pid)
            raise
        if old:
            Path(old).unlink(missing_ok=True)
        return pid
