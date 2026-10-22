# Nghiệm thu trên Windows và thiết bị thật

Chỉ đánh dấu đạt sau khi thực hiện trên máy mục tiêu. Dùng dữ liệu khuôn mặt có
sự cho phép; không đưa dữ liệu đó vào source hoặc gửi ra bên ngoài.

| Bước | Thao tác | Kết quả cần đạt |
|---|---|---|
| 1 | Cài Python 3.11 x64, setup_windows.bat cpu; pip check | Không xung đột gói, chỉ có ORT CPU |
| 2 | Cài model chính thức, run_cpu.bat --diagnose | Cả detection/recognition warmup thành công, backend CPU |
| 3 | Thêm ảnh một mặt rõ với tên tiếng Việt | UUID, avatar và 1 embedding; khởi động lại vẫn còn |
| 4 | Chọn ảnh không mặt, nhiều mặt, quá nhỏ hoặc file hỏng | Báo rõ lỗi; không tạo hồ sơ rỗng/embedding |
| 5 | Thêm ảnh cùng người, thêm ảnh giống người khác | Có cảnh báo và ba lựa chọn; nhiều reference đúng hồ sơ |
| 6 | Thay/xóa ảnh, sửa tên, ngừng/bật hồ sơ | Gallery cập nhật; hồ sơ ngừng không được nhận diện |
| 7 | Quét/chọn camera, Bắt đầu, di chuyển cửa sổ | Giao diện tương tác được; tên/ID Unicode, FPS/backend đúng |
| 8 | Đưa người chưa đăng ký vào cạnh người đã đăng ký | Người lạ là Không xác định; không tự lưu ảnh người lạ |
| 9 | Bật ghi, người đã đăng ký liên tục 15 phút | Một phiên; last_seen tăng; không thêm một row mỗi frame |
| 10 | Che mặt 10 giây, quay lại; rồi vắng hơn 30 giây | Che ngắn giữ phiên; vắng dài tạo phiên mới |
| 11 | Hai người cùng khung hình, rồi rời khác lúc | Phiên độc lập; Check-out đúng lần nhận diện cuối |
| 12 | Tắt ghi, mở MP4/AVI, thử năm tốc độ | Phát/pause/seek/dừng về đầu hoạt động; không ghi row mới |
| 13 | Bật ghi, pause 60 giây rồi tiếp tục | Timeout dựa media, không tách phiên vì wall-clock pause |
| 14 | Tua lui nhiều lần rồi tua tới; phát cùng video đổi tên | Không frame/nhãn cũ ghi đè; nguồn cùng hash; interval hợp nhất |
| 15 | Mở video khác ở cùng timeline | Không gộp với video trước |
| 16 | Lọc ngày camera/timeline video; tìm tên/ID, sắp xếp | Đúng dữ liệu; ngày camera không biến thành ngày quay video |
| 17 | Xuất lọc CSV, mở trong Excel | BOM, tên tiếng Việt, đúng bốn cột, phân biệt Video với giờ thực |
| 18 | Xóa một/nhiều/toàn bộ phiên; mở lại ứng dụng | Người/ảnh/embedding vẫn nguyên; lịch sử đã xóa không tự hồi sinh |
| 19 | Xóa hồ sơ sau xác nhận | Reference biến mất; lịch sử giữ ID/tên cũ |
| 20 | Dừng camera, đóng cửa sổ khi đang phát/seek/đăng ký | Worker dừng, flush, đóng SQLite an toàn, không treo GUI |
| 21 | Kiểm tra khởi động lại sau kill tiến trình có chủ ý | DB toàn vẹn, phiên open cũ đóng tại checkpoint, người còn |
| 22 | setup_windows.bat cuda, cấu hình CUDA/cuDNN đúng | Chỉ ORT GPU trong venv-cuda; diagnostics chạy cả hai mạng |
| 23 | Trên máy GPU, kiểm tra provider và warmup, video thật | CUDA ưu tiên trong cả hai session; đo CPU/GPU và FPS |
| 24 | Thiếu DLL/provider trong môi trường thử riêng | Nêu nguyên nhân và CPU fallback; không tự cài/tải package |
| 25 | Build CPU onedir trên Windows, thử máy sạch | Qt/ORT DLL đầy đủ, model/user data cài riêng, quyền ghi đúng |

Đánh giá ngưỡng: tạo tập cùng người/khác người ở nhiều góc, ánh sáng, kính và độ
mờ. Đo false accept/false reject, chọn similarity và tần suất phù hợp. Thử cảnh
hai người đi cắt nhau để đánh giá giới hạn tracker IoU. Không dùng kết quả một
ảnh đơn lẻ để khẳng định độ chính xác vận hành.

Để xác minh timestamp, dùng video CFR có đồng hồ đóng trên ảnh hoặc danh sách
frame time độc lập; thử đầu/cuối và seek hai chiều. Chuyển VFR sang CFR trước nếu
OpenCV backend thiếu PTS chính xác. Thử ghi vào đường dẫn không có quyền để kiểm
tra thông báo lỗi CSV và lưu ảnh.
