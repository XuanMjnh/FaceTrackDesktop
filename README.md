# Tìm Người

Tìm Người là ứng dụng desktop trên Windows để đăng ký hồ sơ
khuôn mặt, nhận diện người trong camera trực tiếp hoặc video, theo dõi
các phiên xuất hiện và tra cứu/xuất lịch sử. Ứng dụng dùng InsightFace
và ONNX Runtime; ảnh tham chiếu, embedding và cơ sở dữ liệu được lưu
trên máy.

Khi bật **Thông báo khi phát hiện**, ứng dụng gửi metadata sự kiện (nguồn, thời điểm, tên/ID hoặc số khuôn mặt không xác định) qua máy
chủ SMTP do người dùng cấu hình. Ảnh camera/video và embedding không
được đính kèm email.

## Mục lục

- [Tính năng](#tính-năng)
- [Kiến trúc tổng thể](#kiến-trúc-tổng-thể)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Luồng hoạt động](#luồng-hoạt-động)
- [Cài đặt và chạy](#cài-đặt-và-chạy)
- [Cách sử dụng](#cách-sử-dụng)
- [Quy tắc nhận diện và lịch sử](#quy-tắc-nhận-diện-và-lịch-sử)
- [Dữ liệu và quyền riêng tư](#dữ-liệu-và-quyền-riêng-tư)
- [Kiểm thử và đóng gói](#kiểm-thử-và-đóng-gói)
- [Cấu trúc source code](#cấu-trúc-source-code)
- [Xử lý lỗi thường gặp](#xử-lý-lỗi-thường-gặp)

## Tính năng

Ứng dụng có sáu trang chính:

1.  **Camera trực tiếp**
    - Quét camera ở các chỉ số `0–7`, hoặc nhập chỉ số thiết bị thủ
      công.
    - Hiển thị khung hình, bounding box, nhãn nhận diện, họ tên, ID và
      điểm tương đồng theo cài đặt.
    - Chụp khung hình hiện tại thành ảnh JPEG.
    - Bật/tắt ghi lịch sử và bật/tắt thông báo email độc lập với nhau.
2.  **Video**
    - Mở video có codec được OpenCV hỗ trợ; hộp thoại chọn tệp lọc các
      định dạng MP4, AVI, MKV, MOV và WMV.
    - Phát/tạm dừng, về đầu, tua ±10 giây, kéo thanh timeline, nhảy tới
      thời điểm nhập tay và chọn tốc độ `0.25x`, `0.5x`, `1x`, `1.5x`,
      `2x`.
    - Phân tích video và ghi lịch sử theo thời gian media; âm thanh
      video không được phát.
    - Thông báo email hoạt động độc lập với việc ghi lịch sử.
3.  **Hồ sơ người**
    - Tạo hồ sơ, đổi tên, bật/ngừng sử dụng, tìm theo họ tên hoặc ID,
      xem lịch sử và xóa hồ sơ.
    - Mỗi hồ sơ hỗ trợ nhiều ảnh tham chiếu; thêm, thay thế hoặc xóa
      từng ảnh.
    - Ảnh đăng ký phải có đúng một khuôn mặt, độ tin cậy detector tối
      thiểu `0.6` và cạnh ngắn của bounding box tối thiểu `40 px`.
    - Khi ảnh mới tương đồng cao với hồ sơ khác, ứng dụng đưa ra lựa
      chọn thêm vào hồ sơ hiện có, tiếp tục hồ sơ đang chọn/tạo hồ sơ
      mới hoặc hủy.
4.  **Lịch sử xuất hiện**
    - Tìm theo họ tên/ID; lọc theo loại nguồn, mã nguồn, ngày camera
      hoặc khoảng thời gian trong video.
    - Sắp xếp các cột, chọn và xóa một hoặc nhiều phiên, hoặc xóa toàn
      bộ lịch sử.
    - Xuất các hàng đang hiển thị ra CSV gồm ID, họ tên, check-in và
      check-out. File dùng UTF-8 BOM và xử lý an toàn nội dung tên/ID.
5.  **Thông báo**
    - Đăng nhập tài khoản gửi email bằng SMTP; hỗ trợ SSL và STARTTLS.
      Cấu hình mặc định phù hợp với Gmail là `smtp.gmail.com`, cổng
      `465`, SSL.
    - Quản lý nhiều địa chỉ email nhận, gửi email kiểm tra, bật thông
      báo cho camera/video và xem nhật ký gửi email.
    - Cấu hình khoảng nghỉ giữa các thông báo cho cùng một người/nguồn
      (mặc định `60` giây, giới hạn `10–3600` giây) và chọn có báo cả
      khuôn mặt không xác định hay không.
    - Thao tác SMTP chạy ở worker nền; hàng đợi thông báo có giới hạn để
      tránh làm nghẽn luồng camera hoặc giao diện.
    - Trên Windows, tùy chọn ghi nhớ tài khoản dùng DPAPI theo tài khoản
      Windows để bảo vệ mật khẩu.
6.  **Cài đặt**
    - Chọn backend `auto`, `cpu` hoặc `cuda`; kích thước đầu vào
      detector; ngưỡng tương đồng; thời gian vắng mặt để đóng phiên; tần
      suất nhận diện.
    - Cấu hình đường dẫn SQLite, thư mục ảnh tham chiếu, thư mục model
      InsightFace.
    - Chọn thông tin hiển thị trên khung hình và chạy chẩn đoán
      backend/model.
    - Thay đổi cài đặt được lưu và có hiệu lực sau khi khởi động lại ứng
      dụng. Đổi đường dẫn không tự di chuyển dữ liệu hiện có.

## Kiến trúc tổng thể

``` mermaid
flowchart TB
    UI["PySide6 GUI<br/>6 trang chức năng"]
    MAIN["main.py / MainWindow"]
    PIPE["Pipeline<br/>capture worker + recognition worker"]
    CAP["OpenCV<br/>camera hoặc video"]
    ENGINE["FaceEngine<br/>InsightFace buffalo_l + ONNX Runtime"]
    MATCH["FaceMatcher + Tracker<br/>embedding cosine + IoU"]
    SESSION["SessionManager"]
    DB["Database<br/>SQLite + WAL"]
    ENROLL["Enrollment<br/>kiểm tra ảnh đăng ký"]
    CSV["CSV exporter"]
    MAIL["NotificationService<br/>SMTP worker"]
    SMTP["SMTP server / email người nhận"]

    UI --> MAIN
    MAIN <--> PIPE
    CAP --> PIPE
    PIPE --> ENGINE
    ENGINE --> MATCH
    MATCH --> UI
    MATCH --> SESSION
    SESSION --> DB
    UI --> ENROLL
    ENROLL --> ENGINE
    ENROLL --> DB
    DB --> UI
    UI --> CSV
    PIPE --> MAIL
    MAIL --> SMTP
```

### Các lớp và trách nhiệm

- **`main.py`**: đọc tham số dòng lệnh, tải `Settings`, chạy chế độ chẩn
  đoán nếu có `--diagnose`, khóa single-instance theo thư mục dữ liệu,
  khởi tạo SQLite và cửa sổ chính.
- **`app/config.py`**: định nghĩa, kiểm tra và lưu cài đặt trong
  `settings.json`; xác định thư mục dữ liệu mặc định hoặc từ biến môi
  trường `FACETRACK_HOME`.
- **`app/models/schemas.py`**: các kiểu dữ liệu dùng chung cho
  detection, match, frame và nhãn khuôn mặt.
- **`app/services/face_engine.py`**: adapter InsightFace; chỉ nạp các
  model detection và recognition từ `buffalo_l`; kiểm tra inference và
  provider ONNX Runtime khi khởi tạo.
- **`app/services/face_matcher.py`**: chuẩn hóa embedding 512 chiều, so
  khớp cosine với gallery và xử lý trường hợp không đủ tin cậy/mơ hồ.
- **`app/services/tracker.py`**: liên kết bounding box giữa các frame
  bằng IoU và yêu cầu xác nhận danh tính qua các kết quả liên tiếp.
- **`app/services/enrollment.py`**: đọc ảnh, kiểm tra số khuôn mặt/chất
  lượng tối thiểu, cảnh báo ảnh tương đồng và lưu ảnh tham chiếu cùng
  embedding.
- **`app/services/database.py`**: quản lý hồ sơ, embedding và phiên xuất
  hiện. Mọi thao tác SQLite được tuần tự hóa qua một owner thread; bật
  foreign key, WAL và `synchronous=FULL`.
- **`app/services/session_manager.py`**: mở, cập nhật, checkpoint và
  đóng phiên theo từng nguồn phân tích.
- **`app/services/camera_service.py` / `video_service.py`**: mở nguồn
  hình, quét camera, định danh video bằng SHA-256 và xác định timestamp
  từng frame.
- **`app/services/csv_exporter.py`**: định dạng timestamp camera/video
  và xuất CSV an toàn hơn với ứng dụng bảng tính.
- **`app/services/notifications.py`**: lưu cấu hình/người nhận/nhật ký
  email; quản lý đăng nhập SMTP, cooldown, hàng đợi gửi nền và bảo vệ
  mật khẩu bằng Windows DPAPI khi được bật.
- **`app/workers/pipeline.py`**: phối hợp capture, nhận diện, tracker,
  session và thông báo. Các mailbox chỉ giữ frame mới nhất; `epoch` vô
  hiệu hóa kết quả cũ khi đổi nguồn, tua, dừng hoặc thay đổi chế độ ghi.
- **`app/ui/`**: sáu trang UI, widget hiển thị frame, bảng, bộ lọc và
  theme dùng chung. Tác vụ chậm được đưa sang worker nền để tránh khóa
  giao diện.

## Công nghệ sử dụng

| Thành phần               | Công nghệ / phiên bản được ghim                                                     |
|--------------------------|-------------------------------------------------------------------------------------|
| Ngôn ngữ                 | Python 3.11 x64                                                                     |
| Giao diện desktop        | PySide6 `6.8.3`, Qt Widgets                                                         |
| Đọc camera, ảnh và video | OpenCV Headless `4.10.0.84`                                                         |
| Nhận diện khuôn mặt      | InsightFace `0.7.3`, model `buffalo_l`                                              |
| Runtime suy luận CPU     | ONNX Runtime `1.20.1`                                                               |
| Runtime suy luận GPU     | ONNX Runtime GPU `1.20.2`                                                           |
| Vector và xử lý số       | NumPy `1.26.4`, SciPy; embedding 512 chiều                                          |
| Lưu dữ liệu              | SQLite tích hợp Python, WAL                                                         |
| Kiểm thử                 | pytest `8.3.5`                                                                      |
| Đóng gói Windows         | PyInstaller `6.12.0`, chế độ `onedir`                                               |
| Dependency hỗ trợ model  | ONNX, Cython, scikit-learn, scikit-image và các gói trong `requirements-common.txt` |

CPU và CUDA dùng **hai môi trường Python riêng** để tránh xung đột giữa
`onnxruntime` và `onnxruntime-gpu`. Môi trường CUDA sử dụng các gói CUDA
12.x và cuDNN 9.x được ghim trong `requirements-cuda.txt`; cần driver
NVIDIA tương thích.

### Model và giấy phép

Model `buffalo_l` không được đóng gói cùng source và ứng dụng không tự
tải model khi khởi động. Người dùng cần tự tải `buffalo_l.zip` từ
[InsightFace release
v0.7](https://github.com/deepinsight/insightface/releases/tag/v0.7), sau
đó cài bằng script đi kèm. Thông tin giấy phép tại [InsightFace
License](https://github.com/deepinsight/insightface#license).

## Luồng hoạt động

1.  **Khởi động**: `main.py` đọc cài đặt, khóa ứng dụng để tránh hai
    tiến trình cùng ghi một vùng dữ liệu, khởi tạo SQLite và
    `MainWindow`. Model được nạp trong tác vụ nền; giao diện hiển thị
    trạng thái model/backend.
2.  **Chọn nguồn**: người dùng mở camera hoặc video. Camera được định
    danh dạng `camera:<index>`. Video được đọc toàn bộ để tính SHA-256;
    cùng nội dung video sẽ có cùng ID nguồn kể cả khi đổi tên hoặc sao
    chép file.
3.  **Capture**: capture worker đọc frame bằng OpenCV. Pipeline giữ
    frame mới nhất trong mailbox thay vì xếp hàng vô hạn; việc này giúp
    giảm độ trễ khi tốc độ nhận diện thấp hơn tốc độ nguồn.
4.  **Nhận diện**: recognition worker gửi frame vào `FaceEngine`;
    InsightFace phát hiện khuôn mặt và tạo embedding. `FaceMatcher` so
    khớp với embedding của các hồ sơ đang hoạt động; `Tracker` xác nhận
    nhãn qua nhiều frame trước khi hiển thị danh tính.
5.  **Hiển thị**: UI vẽ bounding box, tên/ID/điểm tùy cài đặt và cập
    nhật danh sách người trong frame mới nhất. Khuôn mặt không đủ tin
    cậy được hiển thị là **Không xác định**.
6.  **Ghi lịch sử (tùy chọn)**: khi bật ghi lịch sử cho nguồn hiện tại,
    `SessionManager` tạo phiên cho người đã nhận diện được, cập nhật lần
    xuất hiện cuối và lưu vào SQLite. Nếu tắt ghi lịch sử, việc nhận
    diện và hiển thị vẫn hoạt động.
7.  **Thông báo (tùy chọn)**: khi người dùng đã đăng nhập SMTP và bật
    thông báo cho nguồn, sự kiện đạt cooldown được đưa vào hàng đợi gửi
    email. Gửi mạng không chạy trên luồng giao diện/capture.
8.  **Tra cứu/xuất**: trang Lịch sử truy vấn các phiên trong SQLite theo
    bộ lọc; CSV exporter xuất các hàng đang hiển thị.

## Cài đặt và chạy

### Yêu cầu

- Windows 10/11 x64.
- Python **3.11 x64** và Python Launcher (`py`). Không dùng Python
  32-bit.
- Microsoft Visual C++ Redistributable 2015–2022 x64.
- InsightFace `0.7.3` có thể phải build extension từ source. Khi pip báo
  thiếu compiler, cài [Visual Studio Build Tools
  2022](https://visualstudio.microsoft.com/visual-cpp-build-tools/) với
  workload **Desktop development with C++**, MSVC và Windows SDK.
- Camera vật lý chỉ cần khi dùng tính năng camera trực tiếp; kiểm thử có
  thể dùng video tổng hợp.

### 1. Cài môi trường CPU

Giải nén source, mở Command Prompt tại thư mục dự án rồi chạy:

``` bat
setup_windows.bat cpu
```

Script tạo môi trường `.venv-cpu`, cài các dependency đã ghim, cài
dependency phát triển và chạy `pip check`. Nếu build InsightFace thất
bại, cài C++ Build Tools như trên rồi chạy lại từ x64 Native Tools
Command Prompt của Visual Studio.

### 2. Cài model InsightFace

Tải `buffalo_l.zip` từ trang release đã nêu ở trên. Sau khi cài môi
trường CPU, chạy:

``` bat
.venv-cpu\Scripts\python tools\install_model.py "C:\Downloads\buffalo_l.zip"
```

Mặc định, ứng dụng mong đợi hai file sau:

``` text
%USERPROFILE%\FaceTrackDesktop\insightface\models\buffalo_l\det_10g.onnx
%USERPROFILE%\FaceTrackDesktop\insightface\models\buffalo_l\w600k_r50.onnx
```

Installer chỉ lấy hai file có tên yêu cầu từ ZIP và không giải nén tùy ý
toàn bộ archive. Dùng các lệnh sau để kiểm tra SHA-256 hoặc chỉ định thư mục gốc riêng:

``` bat
.venv-cpu\Scripts\python tools\install_model.py "C:\Downloads\buffalo_l.zip" --sha256 CHECKSUM_SHA256
.venv-cpu\Scripts\python tools\install_model.py "C:\Downloads\buffalo_l.zip" --root "D:\FaceTrack\insightface"
```

Nếu đổi `model_root` trong Cài đặt, phải cài model vào đúng thư mục gốc
đó. Nếu dùng `FACETRACK_HOME`, hãy đặt cùng giá trị khi cài model và
chạy ứng dụng.

### 3. Khởi chạy bản CPU

``` bat
run_cpu.bat
```

Hoặc dùng `run.bat` (wrapper của `run_cpu.bat`). Chẩn đoán model/backend
mà không mở GUI:

``` bat
run_cpu.bat --diagnose
```

Chạy trực tiếp để dùng backend đã lưu trong `settings.json` bằng lệnh:

``` bat
.venv-cpu\Scripts\python main.py
```

Tham số `--backend auto|cpu|cuda` ghi đè backend đã lưu. `run_cpu.bat`
luôn truyền `--backend cpu`.

### 4. Khởi chạy NVIDIA CUDA (tùy chọn)

``` bat
setup_windows.bat cuda
run_cuda.bat --diagnose
run_cuda.bat
```

`run_cuda.bat` dùng môi trường `.venv-cuda` và bổ sung các thư mục DLL
từ những gói NVIDIA đã cài vào `PATH`. Cần NVIDIA driver tương thích với
CUDA/cuDNN trong môi trường. Xem [yêu cầu CUDA Execution
Provider](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html#requirements)
và [cài đặt ONNX Runtime](https://onnxruntime.ai/docs/install/).

Nếu CUDA provider không khả dụng hoặc khởi tạo/inference thất bại,
engine chuyển sang CPU và hiển thị cảnh báo.

### 5. Chỉ định thư mục dữ liệu khác

Mặc định dữ liệu được lưu trong `%USERPROFILE%\FaceTrackDesktop`. Đặt
biến môi trường `FACETRACK_HOME` trước khi chạy để đổi thư mục gốc.
Cài model và khởi động ứng dụng bằng cùng cấu hình thư mục. Thay đường
dẫn SQLite, ảnh hoặc model trong Cài đặt không tự sao chép dữ liệu cũ;
khởi động lại để áp dụng.

## Cách sử dụng

### Đăng ký hồ sơ

1.  Mở **Hồ sơ người** → **Thêm người**.
2.  Nhập họ tên và chọn ảnh có đúng một khuôn mặt rõ.
3.  Xử lý cảnh báo ảnh tương đồng nếu ứng dụng phát hiện hồ sơ gần
    giống.
4.  Chọn hồ sơ để thêm nhiều ảnh tham chiếu, thay ảnh hoặc xóa ảnh không
    còn phù hợp.
5.  Hồ sơ ở trạng thái **Ngừng sử dụng** vẫn giữ ảnh nhưng bị loại khỏi
    gallery so khớp. Bật lại để cho phép nhận diện.

### Nhận diện camera

1.  Mở **Camera trực tiếp** và bấm **Quét camera**, hoặc nhập mã thiết
    bị như `0`.
2.  Bấm **Bắt đầu camera**. Kiểm tra quyền Camera Privacy của Windows
    và đóng ứng dụng khác đang giữ camera nếu camera không mở được.
3.  Bật **Ghi lịch sử xuất hiện** để lưu các phiên nhận diện.
4.  Bật **Thông báo khi phát hiện** nếu muốn gửi email và đã cấu hình
    tài khoản/người nhận trong trang Thông báo.
5.  **Chụp ảnh** chỉ lưu khung hình thành JPEG, không tự tạo hồ sơ
    người.

### Phân tích video

1.  Mở **Video** → **Mở video** và chọn tệp.
2.  Dùng các nút phát/tạm dừng, tua, thanh timeline, tốc độ hoặc trường
    nhập thời gian.
3.  Bật **Phân tích và ghi lịch sử theo timeline** để ghi các phiên vào
    lịch sử; nếu tắt, video vẫn được phát và nhận diện nhưng không ghi
    phiên.
4.  Bật **Thông báo khi phát hiện** nếu đã cấu hình email. Tua hoặc đổi
    nguồn sẽ vô hiệu hóa kết quả cũ để tránh ghi nhầm frame vào timeline mới.

### Cấu hình email thông báo

1.  Mở trang **Thông báo**.
2.  Nhập tài khoản gửi, mật khẩu ứng dụng, máy chủ SMTP, cổng và
    SSL/STARTTLS. Với Gmail, dùng mật khẩu ứng dụng theo hướng dẫn của
    Google.
3.  Bấm **Đăng nhập**, thêm ít nhất một địa chỉ nhận rồi bấm **Gửi
    thử**.
4.  Điều chỉnh cooldown và tùy chọn thông báo khuôn mặt không xác định.
5.  Quay lại trang Camera hoặc Video và bật checkbox **Thông báo khi
    phát hiện** cho nguồn mong muốn.
6.  Xem trạng thái và chi tiết tại bảng **Nhật ký email**.

### Tra cứu lịch sử và xuất CSV

- Tìm theo tên/ID, chọn mọi nguồn/camera/video và lọc thêm theo mã
  nguồn.
- Bộ lọc ngày chỉ áp dụng cho camera; bộ lọc timeline chỉ áp dụng cho
  video. Hai bộ lọc thời gian không dùng đồng thời.
- Bấm **Áp dụng bộ lọc** trước khi tra cứu. **Xuất CSV** xuất các hàng
  đang hiển thị theo kết quả đã tải gần nhất.
- Xóa lịch sử không xóa hồ sơ hay ảnh tham chiếu. Xóa hồ sơ sẽ xóa
  ảnh/embedding của hồ sơ nhưng giữ bản chụp ID và tên trong lịch sử cũ.

## Quy tắc nhận diện và lịch sử

- **Embedding**: mỗi khuôn mặt được biểu diễn bằng vector float32 512
  chiều đã chuẩn hóa. Gallery sử dụng ảnh tham chiếu của các hồ sơ đang
  hoạt động; điểm của một người là điểm cosine cao nhất trong các ảnh
  tham chiếu của người đó.
- **Ngưỡng so khớp**: mặc định `0.45`. Nếu điểm thấp hơn ngưỡng, hoặc
  khoảng cách giữa hai danh tính đứng đầu nhỏ hơn `0.04`, nhãn là
  **Không xác định**.
- **Tracker**: ghép detection giữa frame bằng IoU; nhãn danh tính cần
  hai kết quả liên tiếp cùng người. Khi điểm không đủ tin cậy, tracker
  không giữ lại tên cũ chỉ vì detection trước đó đã được nhận diện.
- **Phiên camera**: thời gian hiển thị dùng Unix timestamp theo múi giờ
  máy; timeout vắng mặt dùng monotonic clock để tránh bị ảnh hưởng khi
  đồng hồ hệ thống thay đổi. Mặc định vắng quá `30` giây sẽ đóng phiên;
  check-out là lần nhận diện cuối cùng, không phải thời điểm timeout.
- **Phiên video**: thời gian lưu theo giây của media, không phải giờ
  phát trên máy. Nguồn video dùng SHA-256 toàn bộ nội dung. Khi phân
  tích lại cùng video, các khoảng của cùng người có thể được hợp nhất
  nếu chồng lấn hoặc cách nhau không quá ngưỡng vắng mặt.
- **Tua, dừng và đổi chế độ ghi**: pipeline tăng `epoch`, xóa
  mailbox/kết quả cũ và đóng phiên đang mở. Tạm dừng video không tự tăng
  thời gian vắng mặt.
- **Tần suất nhận diện**: pipeline lấy mẫu frame mới nhất theo
  `recognition_hz`; không xử lý mọi frame của video/camera.
- **Lưu bền vững**: phiên được ghi khi mở/đóng và checkpoint các cập
  nhật đang hoạt động khoảng mỗi 2 giây. Khi khởi động lại, phiên còn
  trạng thái `open` từ lần chạy bị gián đoạn được đóng tại `last_seen`
  đã lưu.

## Dữ liệu và quyền riêng tư

Thư mục dữ liệu mặc định là `%USERPROFILE%\FaceTrackDesktop\`:

``` text
FaceTrackDesktop/
├── settings.json          # cài đặt ứng dụng
├── facetrack.sqlite3      # hồ sơ, embedding và lịch sử xuất hiện
├── notifications.sqlite3  # cấu hình SMTP, email nhận và nhật ký email
├── facetrack.lock         # khóa một tiến trình theo vùng dữ liệu
├── images/<person-id>/    # ảnh tham chiếu của từng hồ sơ
└── insightface/models/buffalo_l/
    ├── det_10g.onnx
    └── w600k_r50.onnx
```

- Ảnh tham chiếu và embedding được lưu cục bộ; frame camera/video không
  được tự lưu thành hồ sơ. Ứng dụng không tự tải ảnh hoặc embedding lên
  dịch vụ nhận diện bên ngoài và không tự tải model lúc khởi động.
- Nếu bật email, thông tin sự kiện (tên/ID, nguồn, thời điểm và số khuôn
  mặt không xác định nếu tùy chọn này bật) được gửi tới máy chủ SMTP và
  địa chỉ nhận do người dùng cấu hình. Email không đính kèm ảnh hay
  embedding.
- Nếu bật **Ghi nhớ tài khoản** trên Windows, mật khẩu được bảo vệ bằng
  DPAPI theo người dùng Windows hiện tại. SQLite vẫn chứa cấu hình, địa
  chỉ nhận và nhật ký; không được mã hóa toàn bộ cơ sở dữ liệu.
- SQLite và ảnh tham chiếu **không được mã hóa bởi ứng dụng**.
- Xóa hồ sơ sẽ xóa ảnh tham chiếu và embedding của hồ sơ đó; lịch sử giữ
  snapshot ID/tên tại thời điểm ghi nhận. Xóa lịch sử không xóa hồ sơ.
  Tên trong lịch sử không tự đổi khi đổi tên hồ sơ.

## Kiểm thử và đóng gói

### Chạy test

Sau khi cài môi trường CPU:

``` bat
.venv-cpu\Scripts\python -m pytest -q
```

Bộ kiểm thử bao gồm so khớp embedding, đăng ký ảnh, SQLite, session
timeout/recovery, hợp nhất timeline khi phát lại video, timestamp, xuất
CSV và pipeline với video AVI tổng hợp. Các test này không cần camera
vật lý hoặc model thật; test GUI dùng Qt offscreen.

Chẩn đoán model thật trên máy triển khai:

``` bat
.venv-cpu\Scripts\python main.py --backend cpu --diagnose
```

### Đóng gói EXE

Trên Windows, sau khi cài môi trường CPU:

``` bat
tools\build_exe.bat
```

Script dùng PyInstaller ở chế độ `onedir`; đầu ra nằm trong
`dist\TimNguoi\`. Model vẫn phải được cài riêng trong profile
người dùng. Script này tạo bản CPU; không đóng gói NVIDIA driver/CUDA hệ thống.

## Cấu trúc source code

``` text
FaceTrackDesktop/
├── main.py
├── app/
│   ├── config.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   ├── camera_service.py
│   │   ├── csv_exporter.py
│   │   ├── database.py
│   │   ├── enrollment.py
│   │   ├── face_engine.py
│   │   ├── face_matcher.py
│   │   ├── notifications.py
│   │   ├── session_manager.py
│   │   ├── tracker.py
│   │   └── video_service.py
│   ├── ui/
│   │   ├── camera_page.py
│   │   ├── common.py
│   │   ├── history_page.py
│   │   ├── main_window.py
│   │   ├── notifications_page.py
│   │   ├── persons_page.py
│   │   ├── presence_panel.py
│   │   ├── settings_page.py
│   │   ├── theme.py
│   │   └── video_page.py
│   └── workers/
│       └── pipeline.py
├── tools/
│   ├── build_exe.bat
│   └── install_model.py
├── tests/
├── data/
├── requirements.txt
├── requirements-common.txt
├── requirements-cuda.txt
├── requirements-dev.txt
├── setup_windows.bat
├── run.bat
├── run_cpu.bat
└── run_cuda.bat
```

## Xử lý lỗi thường gặp

- **Thiếu model `buffalo_l`**: chạy `tools/install_model.py` và kiểm tra
  `model_root` có thư mục `models\buffalo_l` chứa cả `det_10g.onnx` và
  `w600k_r50.onnx`.
- **InsightFace không cài được**: kiểm tra Python 3.11 x64; cài Visual
  C++ Redistributable và Visual Studio Build Tools 2022 với MSVC/Windows
  SDK rồi chạy lại setup.
- **Không mở được camera**: kiểm tra lần lượt các chỉ số `0`, `1`, …;
  kiểm tra Windows Camera Privacy và đóng phần mềm khác đang dùng camera.
- **Không mở được video**: kiểm tra codec, FPS và số frame. Chuyển video
  có codec không được hỗ trợ sang định dạng MP4 CFR.
- **CUDA báo thiếu DLL hoặc chuyển sang CPU**: chạy
  `run_cuda.bat --diagnose`, kiểm tra NVIDIA driver, PATH và tính tương
  thích CUDA/cuDNN với ONNX Runtime. Xem thông báo backend trong thanh
  trạng thái.
- **Không gửi được email**: kiểm tra máy chủ/cổng/TLS, mạng, quyền SMTP,
  mật khẩu ứng dụng và danh sách email nhận. Nhật ký email hiển thị chi
  tiết lỗi đã được làm sạch để tránh lộ thông tin nhạy cảm từ phản hồi
  SMTP.
- **Đổi thư mục dữ liệu nhưng không thấy hồ sơ cũ**: đường dẫn mới không
  tự di chuyển database hoặc ảnh. Khôi phục đúng database và thư mục
  ảnh, hoặc đặt lại đường dẫn cũ rồi khởi động lại.
