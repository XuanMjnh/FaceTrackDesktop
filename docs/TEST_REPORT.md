# Báo cáo kiểm thử

Ngày thực hiện: **21/10/2026**. Gói nguồn đã được kiểm tra trong Linux x64,
Python **3.12.14**; máy đích theo yêu cầu là Windows 10/11 + Python 3.11 x64.
Không đồng nhất kết quả kiểm thử Linux với chứng nhận hoạt động trên Windows.

## Kết quả tự động

**43 passed in 4.83s**, không có bài skipped hoặc failed ở lần chạy cuối ghi nhận
trước khi lập báo cáo. Bộ kiểm thử dùng pytest **8.3.5**, NumPy **1.26.4**,
OpenCV **4.10.0**, PySide6 **6.8.3**, Qt `offscreen`. Các phiên bản thư viện này
khớp các pin tương ứng trong requirements.

Lệnh chạy tại môi trường kiểm thử (các dependency kiểm thử nằm ở thư mục riêng):

```bash
PYTHONPATH=../.test-deps PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen \
python -m pytest -q --tb=short --basetemp=../qa-final --junitxml=../qa-final.xml
```

Tại Windows sau setup, chạy `.venv-cpu\Scripts\python -m pytest -q`.

| Phạm vi | Kết quả đã kiểm tra |
|---|---|
| Matcher/tracker | Vector chuẩn hóa, nhiều ảnh, unknown, hai người điểm sát nhau, vector lỗi, hai xác nhận, loại hồ sơ ngừng |
| Enrollment | Lưu ảnh/embedding, cảnh báo trùng, thay ảnh, từ chối 0/nhiều mặt; detector được thay bằng đối tượng có kiểm soát |
| Session | 15 phút liên tục một row, che khuất ngắn, trở lại sau timeout, checkout đúng, nhiều người, đồng hồ lùi |
| Persistence | SQLite thật, xóa lịch sử giữ người/embedding, xóa người giữ snapshot, khôi phục phiên open sau gián đoạn |
| Video intervals | Replay lui/tới, khoảng rời nhau, nguồn khác nhau, gộp bắc cầu, pause theo media clock |
| Timestamp/source | POS_MSEC và fallback frame/FPS, FPS lỗi, hash ổn định khi đổi tên, lọc nguồn/timeline |
| CSV | UTF-8 BOM, tiếng Việt, đúng 4 cột, nhiều phiên, video source/timeline, giờ camera, vô hiệu công thức |
| Pipeline | File AVI tổng hợp qua VideoWriter/VideoCapture thật; preview không log, pause, seek, 2x, log/replay, flush EOF |
| Race condition | Inference cũ bị giữ bằng Event; seek tăng epoch; khi thả kết quả cũ không được publish hoặc ghi lịch sử |
| Engine adapter | Giả lập provider: CPU được chọn đúng, CUDA lỗi chuyển CPU, model cache; model thiếu không khởi tạo auto-download |
| GUI | Khởi tạo cửa sổ, mở đủ 5 trang, xử lý event, đóng bất đồng bộ và kết thúc worker sạch |

Ngoài ra: `compileall` thành công; toàn bộ file `.py` parse với grammar Python 3.11.
Đã mở ảnh render GUI để kiểm tra bố cục trang Cài đặt và tiếng Việt. Ảnh kiểm tra
nội bộ không được đưa vào gói bàn giao.

Một lỗi sai số placeholder SQL lúc lưu phiên đã được bộ test phát hiện và sửa.
Bộ test cuối nêu trên chạy sau bản sửa đó, cập nhật shutdown/sắp xếp thời gian và trường hợp backend trả timestamp 0 ở frame sau frame đầu.

## Chưa thực hiện trong môi trường này

- Nhận diện thực tế bằng trọng số InsightFace trên CPU; chưa tải mô hình và chưa
  đo false accept/false reject trên khuôn mặt thật. Tests embedding/detector tổng
  hợp kiểm tra logic ứng dụng, không chứng minh chất lượng mô hình.
- Camera vật lý, driver DirectShow/MSMF, codec trên Windows.
- Runtime Windows Python 3.11 và quy trình cài MSVC/InsightFace từ source trên máy
  Windows sạch. Grammar 3.11 thành công không thay thế chạy runtime thật.
- CUDA/cuDNN/NVIDIA GPU và tốc độ inference phần cứng. Provider fallback tests
  dùng đối tượng thay thế; không phải inference CUDA thật.
- EXE PyInstaller và triển khai trên máy đích sạch.

Hoàn tất `MANUAL_TESTS.md`, bắt đầu bằng CPU thật rồi mới GPU, trước khi dùng dữ
liệu thực tế. ZIP không chứa mô hình, sinh trắc học thật, database người dùng hoặc
môi trường cài sẵn.
