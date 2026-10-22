# Kiến trúc triển khai

## Phân chia trách nhiệm

| Thành phần | Luồng | Trách nhiệm |
|---|---|---|
| PySide6, QTimer 33 ms | GUI | Điều khiển, vẽ ảnh/nhãn Unicode, hiển thị kết quả công việc nền |
| Capture | Python thread | Mở camera/video, SHA-256 video, đọc/tua/pacing media |
| Recognition | Python thread | FaceAnalysis, gallery matching, IoU/votes, cập nhật session |
| Engine | Khóa RLock | Tái sử dụng model, tuần tự hóa inference giữa enrollment và media |
| Jobs | ThreadPoolExecutor 2 worker | Đăng ký ảnh, truy vấn bảng, CSV và chẩn đoán |
| Database | ThreadPoolExecutor 1 worker | Sở hữu kết nối SQLite, giao dịch và WAL |

Luồng đọc và nhận diện trao đổi qua mailbox chỉ chứa frame mới nhất. GUI lấy
snapshot theo timer; không phát signal Qt cho từng frame nên không tích lũy
backlog trên event loop. GUI vẽ bounding box lên đúng frame đã nhận diện; khi
inference quá trễ, dùng preview raw thay vì gắn nhãn cũ lên ảnh mới. Tần suất vẽ
ảnh có nhãn vì thế phụ thuộc tốc độ inference. FPS trên giao diện là tốc độ xử lý
inference một frame, không phải tốc độ capture hoặc số frame đã phân tích mỗi giây.

## Tính nhất quán

Một `epoch` nhận diện một đoạn timeline. Seek/đổi nguồn/tắt ghi/đổi gallery vô
hiệu hóa mailbox, flush và đóng phiên dưới cùng khóa gate. Inference chạy ngoài
gate; trước khi xuất kết quả hoặc ghi session phải kiểm tra lại epoch. Thao tác
đang xử lý ở timeline cũ không ghi đè kết quả mới. GUI giữ các thao tác gate ngắn;
lệnh thay đổi đoạn có thể đợi một giao dịch flush SQLite đang hoàn tất, không đợi
inference. Các thao tác DB thực thi trên SQLite actor dù API đồng bộ với caller.

SessionManager chỉ có một instance đang hoạt động, được truy cập dưới gate.
Không có hai recognition writer. `QLockFile` tránh hai tiến trình dùng cùng
FACETRACK_HOME. Hai FACETRACK_HOME khác nhau không được trỏ vào cùng DB đang chạy;
ứng dụng không hỗ trợ nhiều tiến trình nhận diện trên cùng database.

Các session video được hợp nhất trong một giao dịch để giữ khoảng min(first)/
max(last); khóa nguồn và person ngăn gộp hai người hoặc hai video khác nhau.
Chính sách timeout áp dụng cả khoảng thiếu nhận diện ngắn, nên khi đã có bằng
chứng hai đoạn cách nhau ≤ ngưỡng, chúng được coi là cùng phiên. Việc seek không
tự suy ra sự hiện diện trong một khoảng chưa có quan sát xa hơn ngưỡng.

## Persistence

Ba bảng chính: persons, face_embeddings, presence_sessions. Embedding little-endian
float32 chuẩn hóa 512 chiều. Reference có FK CASCADE; lịch sử có person_ref FK
SET NULL và snapshot person_id/person_name giữ định danh sau xóa. SQLite actor
khởi tạo schema v1 và chỉ mục, bật foreign_keys, WAL và synchronous FULL. Phiên
được checkpoint định kỳ, không commit cho mỗi frame. Phiên open ở lần chạy trước
được đánh dấu closed khi khởi động lại, giữ thời điểm bền vững gần nhất.

Ảnh được ghi trước khi commit embedding, rollback hồ sơ mới nếu bước lưu thất bại.
Thay reference commit ảnh mới trước khi xóa ảnh cũ. Hệ thống file và SQLite không
có giao dịch chung: crash đúng giữa hai bước có thể để lại ảnh mồ côi, không tạo
embedding trỏ vào ảnh chưa được ghi. Xóa file thất bại được báo lỗi; quyền Windows
cần cho phép xóa thư mục dữ liệu.

## Giới hạn kỹ thuật và hướng mở rộng

IoU + hai xác nhận giúp giảm nhấp nháy, không thay thế tracker đa đối tượng có
motion model/ReID trong cảnh đông người. Không phải hệ thống liveness hoặc nhận
diện chống giả mạo. Ngưỡng/margin cần kiểm định trên dữ liệu được phép dùng.

OpenCV không cung cấp bảo đảm universal về PTS/VFR và codec. Dùng CFR cho lịch sử
chính xác; có thể thay VideoCapture bằng PyAV trong phiên bản sau. Mẫu mới nhất
ưu tiên GUI đáp ứng và không tăng RAM; không bảo đảm phân tích tất cả frame.

Shutdown chạy nền, chờ job, dừng capture/recognizer rồi flush session và đóng DB.
Nếu driver C bị chặn hoặc model chưa trả về sau timeout, báo đang chờ, giữ DB mở
và cho phép thử đóng lại. Không kill thread đang ghi dữ liệu. Nguồn bị treo lâu
cần được xử lý ở mức driver/hệ điều hành; không cam kết cưỡng bức hủy VideoCapture.
