import sys


def open_capture(source, camera=False):
    import cv2
    if camera and sys.platform == "win32":
        capture = cv2.VideoCapture()
        for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
            candidate = cv2.VideoCapture(int(source), backend)
            if not candidate.isOpened():
                candidate.release()
                continue
            candidate.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            ready = False
            for _ in range(3):
                ok, frame = candidate.read()
                if ok and frame is not None:
                    capture.release()
                    capture = candidate
                    ready = True
                    break
            if ready:
                break
            candidate.release()
    else:
        capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError("Không mở được camera/video. Kiểm tra thiết bị, quyền truy cập hoặc codec.")
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture


def discover_cameras(limit=8):
    found = []
    for index in range(limit):
        try:
            cap = open_capture(index, camera=True)
            ok, _ = cap.read()
            cap.release()
            if ok:
                found.append(index)
        except RuntimeError:
            continue
    return found
