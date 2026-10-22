# FaceTrack Desktop

Ứng dụng desktop Python/PySide6 nhận diện người đã đăng ký bằng InsightFace,
quản lý ảnh tham chiếu và lưu phiên xuất hiện vào SQLite. Dành cho Windows 10/11,
Python **3.11 x64**, chạy CPU hoặc NVIDIA CUDA. Giao diện tiếng Việt, xử lý cục bộ.

Đây là gói mã nguồn. Gói ZIP không chứa Python, thư viện, mô hình, dữ liệu khuôn
mặt thật hoặc EXE đã biên dịch. Cần cài môi trường và mô hình trước khi nhận diện.
Xem `docs/TEST_REPORT.md` để biết chính xác phần đã kiểm thử và phần cần nghiệm thu
trên thiết bị thật. Ngưỡng 0.45 là điểm khởi đầu để hiệu chỉnh, không phải cam kết
độ chính xác. Ứng dụng chưa có phát hiện ảnh giả/liveness.

## 1. Cài đặt CPU trên Windows

1. Cài Python 3.11 x64 từ <https://www.python.org/downloads/windows/>. Bật Python
   Launcher (`py`) và Add Python to PATH. Không dùng Python 32 bit.
2. Cài Microsoft Visual C++ Redistributable 2015–2022 x64. InsightFace 0.7.3 phát
   hành dạng source nên có thể cần **Visual Studio Build Tools 2022**, workload
   **Desktop development with C++**, MSVC và Windows SDK:
   <https://visualstudio.microsoft.com/visual-cpp-build-tools/>.
3. Giải nén vào thư mục có quyền ghi. Mở Command Prompt tại `FaceTrackDesktop`:

```bat
setup_windows.bat cpu
```

Script tạo `.venv-cpu`, cài NumPy/Cython trước khi build InsightFace, cài dependency
và chạy `pip check`. Nếu lỗi build extension, kiểm tra C++ Build Tools, mở Developer
Command Prompt x64 rồi chạy lại. Không tải wheel không rõ nguồn gốc.

Cài thủ công tương đương:

```bat
py -3.11 -m venv .venv-cpu
.venv-cpu\Scripts\python -m pip install --upgrade "pip<26" setuptools wheel Cython==3.0.11 numpy==1.26.4
.venv-cpu\Scripts\python -m pip install --no-build-isolation -r requirements.txt -r requirements-dev.txt
.venv-cpu\Scripts\python -m pip check
```

Ứng dụng dùng OpenCV headless để đọc/ghi ảnh và video; toàn bộ hiển thị do PySide6.
Không cài thêm `opencv-python` trong cùng môi trường vì hai gói dùng chung `cv2`.

## 2. Cài mô hình một lần, có chủ ý

Ứng dụng **không tự tải mô hình hoặc cài package khi chạy**. Mở nguồn phát hành
chính thức: <https://github.com/deepinsight/insightface/releases/tag/v0.7> và lấy
`buffalo_l.zip`. Đọc điều khoản mô hình trước khi dùng. Mã InsightFace và trọng số
có điều khoản khác nhau; trọng số tải sẵn được công bố cho nghiên cứu phi thương
mại. Liên hệ chủ sở hữu mô hình nếu mục đích sử dụng yêu cầu giấy phép khác:
<https://github.com/deepinsight/insightface#license>.

Sau khi tải ZIP bằng trình duyệt, cài từ tệp cục bộ:

```bat
.venv-cpu\Scripts\python tools\install_model.py "C:\Downloads\buffalo_l.zip"
```

Mặc định hai tệp cần dùng nằm ở:

```text
%USERPROFILE%\FaceTrackDesktop\insightface\models\buffalo_l\det_10g.onnx
%USERPROFILE%\FaceTrackDesktop\insightface\models\buffalo_l\w600k_r50.onnx
```

Installer chỉ lấy đúng hai tên tệp, không giải nén đường dẫn tùy ý. Có thể thêm
`--root "D:\FaceTrack\insightface"` và `--sha256 CHECKSUM` nếu có checksum tin cậy.
Khi chọn root khác, nhập cùng đường dẫn trong Cài đặt rồi khởi động lại ứng dụng.
Nếu dùng `FACETRACK_HOME`, cài mô hình và chạy ứng dụng trong cùng biến môi trường.

## 3. Khởi chạy

```bat
run_cpu.bat
```

`run.bat` cũng chạy bản CPU. Có thể chạy trực tiếp
`.venv-cpu\Scripts\python main.py` để áp dụng backend lưu trong Cài đặt; tham số
`--backend cpu|cuda|auto` được ưu tiên hơn cài đặt đã lưu.

Trình tự sử dụng:

1. Vào **Cơ sở dữ liệu người → Thêm người**, nhập tên và chọn ảnh rõ, chỉ có một
   khuôn mặt. Ảnh không có mặt, nhiều mặt hoặc mặt quá nhỏ sẽ bị từ chối.
2. Chọn hồ sơ → **Ảnh tham chiếu** để xem/thêm/thay/xóa nhiều ảnh. Nếu có khuôn mặt
   tương đồng cao với hồ sơ khác, hộp thoại cho phép thêm vào hồ sơ hiện có, tiếp
   tục hồ sơ đã chọn/mới hoặc hủy. Cảnh báo tương đồng không chứng minh hai ảnh là
   cùng một người.
3. Vào **Camera**, bấm **Quét camera** hoặc nhập mã thiết bị (0, 1, …), rồi Bắt đầu.
   Danh sách quét thử mã 0–7; có thể nhập mã khác. Kiểm tra Windows Camera Privacy
   và đóng ứng dụng khác nếu camera đang bận. Nút Chụp ảnh lưu ảnh kiểm tra tại
   đường dẫn người dùng chọn, không tự đăng ký người trong ảnh.
4. Hoặc vào **Video → Mở video**. Phát/tạm dừng, dừng về đầu, kéo thanh tua và chọn
   0.25x, 0.5x, 1x, 1.5x hoặc 2x. Chỉ một nguồn camera/video hoạt động mỗi lúc.
   Âm thanh video không được phát. Có thể cần codec phù hợp cho định dạng khác MP4/AVI.
5. **Ghi lịch sử mặc định tắt** cho cả camera và video. Bật rõ ràng khi được phép
   thu thập. Tắt ghi lịch sử vẫn nhận diện và hiển thị để xem trước.
6. Vào **Lịch sử xuất hiện**, tìm tên/ID, chọn nguồn, lọc ngày camera hoặc khoảng
   giây video, rồi Áp dụng. Bấm tiêu đề cột để sắp xếp; Ctrl/Shift để chọn nhiều
   hàng. CSV xuất đúng các hàng đang hiển thị sau lần áp dụng bộ lọc gần nhất.
7. Cài đặt được lưu và áp dụng ở lần khởi động tiếp theo. Nút kiểm tra môi trường
   kiểm tra cấu hình đang chạy; sau đổi backend, hãy mở lại trước khi kiểm tra.

## 4. CPU và NVIDIA CUDA

Hai môi trường tách biệt giúp tránh cài đồng thời `onnxruntime` và
`onnxruntime-gpu`. Cài bản GPU:

```bat
setup_windows.bat cuda
run_cuda.bat --diagnose
run_cuda.bat
```

Bản này cố định **onnxruntime-gpu 1.20.2**, dùng CUDA **12.x** và cuDNN **9.x** theo
bảng tương thích chính thức. `setup_windows.bat cuda` cài CUDA runtime/cuDNN vào
`.venv-cuda`; `run_cuda.bat` thêm các thư mục DLL vào PATH khi chạy. Cần NVIDIA
driver tương thích. CUDA Toolkit dùng cho phát triển native; không cần cài toàn bộ
Toolkit để chạy inference. Có card NVIDIA hoặc thấy tên provider chưa đủ chứng minh
inference chạy được. Hướng dẫn chính thức:

- <https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html#requirements>
- <https://onnxruntime.ai/docs/install/>
- <https://developer.nvidia.com/cuda-toolkit-archive>
- <https://developer.nvidia.com/cudnn-downloads>

Engine kiểm tra `get_available_providers()`, nạp session, chạy thử detection và
recognition, rồi đọc `session.get_providers()` cho từng mạng. Nếu CUDA thiếu hoặc
khởi tạo/inference thất bại, dựng lại engine CPU và hiển thị nguyên nhân. CPU
fallback vẫn cần các dependency CPU hoạt động. Trạng thái `CUDA + CPU fallback`
có nghĩa CUDA là provider ưu tiên của cả hai session; một số toán tử có thể được
ORT phân bổ cho CPU. Không tuyên bố mọi toán tử đều chạy trên GPU.

Lỗi `LoadLibrary failed 126`, `cudnn64_9.dll`, `cublasLt64_12.dll`: kiểm tra PATH,
CUDA runtime, cuDNN đúng major và driver. `no kernel image` trên GPU
đời mới có thể cần ORT mới hơn; hãy dùng môi trường khác và kiểm thử lại toàn bộ
trước khi thay phiên bản. Bản 1.20.2 không được bảo đảm hỗ trợ mọi GPU hiện tại.
Không nâng GPU package tùy tiện mà giữ nguyên CUDA/cuDNN của bản cũ.

## 5. Quy tắc Check-in/Check-out và timeline

- Chỉ một phiên đang mở cho mỗi người trong nguồn đang phân tích. Lần nhận diện
  được xác nhận đầu tiên mở phiên; các lần sau cập nhật `last_seen` trong RAM.
- Gallery được nạp từ embedding lưu sẵn, không trích xuất lại ảnh đăng ký mỗi frame.
- Tracker liên kết IoU, yêu cầu hai kết quả cùng danh tính liên tiếp, đồng thời
  kiểm tra ngưỡng cosine và khoảng cách điểm giữa hai người. Nếu điểm thấp, nhãn
  trở về Không xác định; không giữ tên cũ qua một kết quả không đủ tin cậy.
- Mất dấu ngắn giữ phiên mở. Vắng **quá** 30 giây mặc định đóng phiên; trở lại mở
  phiên mới. Check-out là nhận diện cuối cùng, không cộng thêm thời gian chờ.
- Camera dùng Unix timestamp của máy và monotonic clock cho timeout. Giờ hiển
  thị/CSV có offset múi giờ của máy. Nếu đồng hồ bị chỉnh lùi, không để last_seen
  nhỏ hơn first_seen; đồng bộ đồng hồ hệ điều hành trước khi vận hành.
- Video dùng vị trí media tính bằng giây/ms, không dùng giờ phát trên máy. Hash
  SHA-256 toàn bộ nội dung định danh video, vì vậy đổi tên/sao chép vẫn cùng nguồn.
  Hash chạy nền nhưng có thể mất thời gian với video lớn. Metadata ngày quay
  không được suy đoán hoặc tự áp dụng.
- Seek/tắt ghi/đổi nguồn làm tăng epoch, loại khung hình và kết quả cũ, đóng đoạn
  phiên hiện tại. Phân tích lại cùng video hợp nhất khoảng trùng/chồng lấn và các
  khoảng cách nhau không quá thời gian vắng mặt, trong giao dịch SQLite. Hợp nhất
  mở rộng bắc cầu để replay không sinh nhiều bản ghi trùng.
- Tạm dừng không tạo tick thời gian vắng mặt. Tua tới một vị trí mới khi đang
  dừng sẽ xử lý một frame tại vị trí đó. Kết quả không tự tạo giờ quay giả.
- Backend OpenCV phải cung cấp FPS/số frame hợp lệ. Với video CFR, POS_MSEC được
  ưu tiên và đối chiếu frame_index/FPS; khi backend trả timestamp sai, dùng
  frame_index/FPS. Video VFR không được bảo đảm chính xác từng timestamp khi
  backend thiếu PTS; hãy chuyển sang MP4 CFR trước khi yêu cầu timeline chính xác.
- Kiến trúc lấy mẫu mới nhất, không bảo đảm nhận diện mọi frame. Tăng Hz hoặc giảm
  tốc độ phát nếu cần phân tích đoạn ngắn; kiểm định trên dữ liệu thực tế.
- Lưu ngay lúc mở/đóng phiên và checkpoint phần thay đổi khoảng 2 giây. Đóng bình
  thường flush toàn bộ; mất điện/kill tiến trình có thể mất tối đa phần cập nhật
  sau checkpoint gần nhất. Lần mở lại đóng các phiên bị gián đoạn ở last_seen đã lưu.

## 6. Dữ liệu, CSV và quyền riêng tư

Dữ liệu mặc định: `%USERPROFILE%\FaceTrackDesktop\`, gồm `settings.json`,
`facetrack.sqlite3`, `images\<person-uuid>\<reference-uuid>.jpg` và `insightface`.
Biến `FACETRACK_HOME` đặt vùng dữ liệu khác. Không commit thư mục dữ liệu thật.
Thay đường dẫn trong cài đặt không tự di chuyển ảnh/DB hoặc cập nhật đường dẫn ảnh
đã lưu; cần sao lưu và lập kế hoạch di chuyển khi ứng dụng đóng.

Xóa lịch sử giữ nguyên người/embedding. Xóa hồ sơ xóa ảnh/embedding và giữ snapshot
ID/tên trong lịch sử; khóa ngoại `person_ref` chuyển NULL. Tên trong lịch sử là tên
tại thời điểm ghi nhận, không tự thay khi đổi tên hồ sơ. Ngừng hồ sơ giữ ảnh nhưng
loại khỏi gallery so khớp. Xóa lịch sử/hồ sơ sẽ dừng nguồn để tránh worker đang chạy
ghi lại bản ghi vừa xóa. Muốn ghi tiếp, chủ động bắt đầu lại nguồn.

CSV có đúng bốn cột, UTF-8 BOM, một hàng mỗi phiên. Thời gian video ghi
`Video [sha256:…] HH:MM:SS.mmm`; camera là ISO 8601 có offset. Tên bắt đầu bằng ký
tự công thức Excel được thêm dấu nháy đơn để tránh thực thi công thức.

Ảnh chưa đăng ký không được lưu thành hồ sơ. Không tải ảnh/embedding lên dịch vụ
bên ngoài; ứng dụng không ghi embedding vào debug log. Chỉ vận hành khi có căn cứ
và sự cho phép phù hợp cho việc thu thập. Dữ liệu SQLite/ảnh chưa mã hóa; dùng quyền
truy cập Windows và mã hóa ổ đĩa nếu cần. Sao lưu cả DB và ảnh khi ứng dụng đã đóng;
không chỉ sao chép tệp SQLite đang mở vì WAL có thể còn giao dịch.

## 7. Kiểm thử và đóng gói

```bat
.venv-cpu\Scripts\python -m pytest -q
.venv-cpu\Scripts\python main.py --backend cpu --diagnose
```

Unit/integration tests dùng embedding tổng hợp, detector thay thế có kiểm soát,
SQLite thật, video AVI tổng hợp qua OpenCV thật và GUI Qt offscreen; không cần
camera vật lý hoặc tải trọng số. Chạy `--diagnose` để kiểm tra mô hình thật tại
máy triển khai. Kế hoạch nghiệm thu: `docs/MANUAL_TESTS.md`.

Đóng gói thử CPU bằng PyInstaller trên **Windows**, trong môi trường đã cài đủ:

```bat
tools\build_exe.bat
```

Phân phối toàn bộ `dist\FaceTrackDesktop\` của chế độ onedir. Trọng số vẫn được
cài riêng ở user profile. Khởi chạy và thử trên Windows sạch, kiểm tra Qt platform
plugins và ONNX DLL; PyInstaller không đóng gói CUDA/driver hệ thống. Script build
chưa được chạy trên Windows trong môi trường tạo gói này. Không có EXE đã nghiệm
thu trong ZIP. Với bản GPU, dùng môi trường GPU riêng và bổ sung kiểm thử DLL cùng
giấy phép phân phối runtime.

## 8. Cấu trúc và tài liệu

- `main.py`: CLI, single-instance lock, khởi động GUI.
- `app/config.py`, `app/models`: cấu hình, dữ liệu frame/face.
- `app/ui`: năm trang và vẽ nhãn Unicode bằng QPainter.
- `app/workers/pipeline.py`: capture thread, recognition thread, mailbox dung
  lượng một frame, epoch gate. Không dùng hàng đợi frame vô hạn.
- `app/services`: engine, matcher, tracker, enrollment, sessions, SQLite actor,
  CSV, camera và video timestamp.
- `tests`: kiểm thử độc lập thiết bị; `tools`: cài mô hình và build EXE.
- `docs/ARCHITECTURE.md`: kiến trúc và đánh đổi; `docs/API_VERIFICATION.md`: API
  thực tế đã đối chiếu; `docs/TEST_REPORT.md`: kết quả kiểm thử.
