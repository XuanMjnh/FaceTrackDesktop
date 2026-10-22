import sys


def open_capture(source, camera=False):
    import cv2
    if camera and sys.platform == "win32":
        capture = cv2.VideoCapture(int(source), cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(int(source), cv2.CAP_MSMF)
    else:
        capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError("Không mở được camera/video. Kiểm tra quyền, thiết bị và codec.")
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
