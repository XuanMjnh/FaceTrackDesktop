# FaceTrack Desktop

FaceTrack Desktop là ứng dụng Windows dùng InsightFace để nhận diện người đã đăng ký, quản lý ảnh tham chiếu và lưu lịch sử xuất hiện vào SQLite. Dữ liệu và xử lý được lưu trên máy. Hỗ trợ Windows 10/11, Python 3.11 x64, CPU và NVIDIA CUDA.

## 1. Cài đặt bản CPU

1. Cài Python 3.11 x64 từ [python.org](https://www.python.org/downloads/windows/), gồm Python Launcher (`py`) và tùy chọn Add Python to PATH. Không dùng Python 32 bit.
2. Cài Microsoft Visual C++ Redistributable 2015–2022 x64. InsightFace 0.7.3 được cài từ mã nguồn và có thể cần Visual Studio Build Tools 2022, workload Desktop development with C++, MSVC và Windows SDK: [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
3. Giải nén ứng dụng vào thư mục có quyền ghi. Mở Command Prompt tại thư mục `FaceTrackDesktop` và chạy:

```bat
setup_windows.bat cpu
```

Script tạo môi trường `.venv-cpu`, cài NumPy và Cython trước khi build InsightFace, cài các dependency còn lại và chạy `pip check`. Nếu build extension thất bại, cài C++ Build Tools rồi chạy lại trong Developer Command Prompt x64. Không dùng wheel từ nguồn không xác định.

Cài thủ công tương đương:

```bat
py -3.11 -m venv .venv-cpu
.venv-cpu\Scripts\python -m pip install --upgrade "pip<26" setuptools wheel Cython==3.0.11 numpy==1.26.4
.venv-cpu\Scripts\python -m pip install --no-build-isolation -r requirements.txt -r requirements-dev.txt
.venv-cpu\Scripts\python -m pip check
```

Ứng dụng dùng OpenCV headless để đọc và ghi ảnh/video; giao diện hình ảnh do PySide6 đảm nhiệm. Không cài thêm `opencv-python` trong cùng môi trường vì cả hai gói đều cung cấp module `cv2`.

## 2. Cài mô hình

Ứng dụng không tự tải mô hình hoặc cài package khi chạy. Tải `buffalo_l.zip` từ [bản phát hành InsightFace 0.7](https://github.com/deepinsight/insightface/releases/tag/v0.7) và xem [điều khoản sử dụng](https://github.com/deepinsight/insightface#license) trước khi triển khai. Mã InsightFace và trọng số có điều khoản riêng; trọng số tải sẵn được công bố cho nghiên cứu phi thương mại. Mục đích sử dụng khác có thể cần giấy phép từ chủ sở hữu mô hình.

Cài từ tệp ZIP đã tải:

```bat
.venv-cpu\Scripts\python tools\install_model.py "C:\Downloads\buffalo_l.zip"
```

Mặc định, hai tệp mô hình nằm tại:

```text
%USERPROFILE%\FaceTrackDesktop\insightface\models\buffalo_l\det_10g.onnx
%USERPROFILE%\FaceTrackDesktop\insightface\models\buffalo_l\w600k_r50.onnx
```

Installer chỉ cài hai tệp có tên được yêu cầu và không giải nén đường dẫn tùy ý. Có thể chỉ định thư mục gốc bằng `--root "D:\FaceTrack\insightface"` và checksum bằng `--sha256 CHECKSUM`. Khi dùng thư mục gốc khác, nhập đường dẫn đó trong Cài đặt. Khi dùng biến môi trường `FACETRACK_HOME`, dùng cùng giá trị lúc cài mô hình và chạy ứng dụng.

## 3. Khởi chạy và sử dụng

Khởi chạy bản CPU:

```bat
run_cpu.bat
```

`run.bat` cũng chạy bản CPU. Để dùng backend đã lưu trong Cài đặt:

```bat
.venv-cpu\Scripts\python main.py
```

Tham số `--backend cpu|cuda|auto` được ưu tiên hơn backend đã lưu.

Khi mở ứng dụng, model được nạp ở worker nền. Thanh trạng thái hiển thị tiến trình nạp và backend sau khi khởi tạo. Nếu model không nạp được, ứng dụng hiển thị lỗi tại thanh trạng thái. Giao diện vẫn phản hồi trong lúc nạp.

Quy trình sử dụng:

1. Mở **Cơ sở dữ liệu người → Thêm người**, nhập tên và chọn ảnh có một khuôn mặt rõ. Ảnh không có mặt, có nhiều mặt hoặc mặt quá nhỏ sẽ bị từ chối.
2. Chọn hồ sơ → **Ảnh tham chiếu** để xem, thêm, thay hoặc xóa ảnh. Nếu ảnh mới tương đồng cao với hồ sơ khác, hộp thoại cho phép thêm vào hồ sơ hiện có, tiếp tục với hồ sơ đã chọn, tạo hồ sơ mới hoặc hủy. Mức tương đồng không xác nhận hai ảnh là cùng một người.
3. Mở **Camera**, bấm **Quét camera** hoặc nhập mã thiết bị (0, 1, …), sau đó bấm **Bắt đầu camera**. Quét thử mã 0–7; có thể nhập mã khác. Kiểm tra quyền Camera Privacy của Windows và đóng ứng dụng khác đang sử dụng camera. **Chụp ảnh** lưu ảnh kiểm tra tại đường dẫn đã chọn, không tạo hồ sơ.
4. Mở **Video → Mở video** để phát, tạm dừng, tua về đầu, kéo thanh thời gian hoặc chọn tốc độ 0.25x, 0.5x, 1x, 1.5x hay 2x. Mỗi lần chỉ chạy một nguồn camera hoặc video. Âm thanh video không được phát. Định dạng ngoài MP4/AVI có thể cần codec phù hợp.
5. Ghi lịch sử mặc định tắt cho camera và video. Chỉ bật khi có căn cứ và sự cho phép phù hợp. Khi tắt ghi lịch sử, nhận diện và hiển thị trực tiếp vẫn hoạt động.
6. Trong **Lịch sử xuất hiện**, tìm theo tên/ID, chọn nguồn, lọc ngày camera hoặc khoảng giây video, rồi bấm **Áp dụng**. Bấm tiêu đề cột để sắp xếp; dùng Ctrl/Shift để chọn nhiều hàng. CSV xuất các hàng đang hiển thị theo bộ lọc đã áp dụng gần nhất.
7. Cài đặt được lưu và áp dụng khi khởi động lại. Kiểm tra môi trường báo cáo backend đang chạy. Khởi động lại ứng dụng sau khi đổi backend.

## 4. CPU và NVIDIA CUDA

CPU và CUDA dùng hai môi trường riêng để tránh cài đồng thời `onnxruntime` và `onnxruntime-gpu`. Cài và chạy bản CUDA:

```bat
setup_windows.bat cuda
run_cuda.bat --diagnose
run_cuda.bat
```

Bản CUDA dùng `onnxruntime-gpu 1.20.2`, CUDA 12.x và cuDNN 9.x theo [bảng tương thích chính thức](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html#requirements). `setup_windows.bat cuda` cài CUDA runtime và cuDNN vào `.venv-cuda`; `run_cuda.bat` bổ sung thư mục DLL vào PATH. Cần NVIDIA driver tương thích. CUDA Toolkit dành cho phát triển native; inference không yêu cầu cài toàn bộ Toolkit.

Engine kiểm tra provider khả dụng, tạo session, chạy thử detection và recognition, rồi kiểm tra provider của từng session. Nếu CUDA không khả dụng hoặc khởi tạo/inference thất bại, engine dựng lại trên CPU và hiển thị nguyên nhân. Chế độ CPU fallback vẫn cần các dependency CPU hoạt động. Trạng thái `CUDA + CPU fallback` cho biết CUDA là provider ưu tiên; ONNX Runtime có thể phân bổ một số toán tử sang CPU.

Tài liệu chính thức:

- [CUDA Execution Provider: yêu cầu](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html#requirements)
- [Cài đặt ONNX Runtime](https://onnxruntime.ai/docs/install/)
- [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit-archive)
- [cuDNN](https://developer.nvidia.com/cudnn-downloads)

Với lỗi `LoadLibrary failed 126`, thiếu `cudnn64_9.dll` hoặc `cublasLt64_12.dll`, kiểm tra PATH, CUDA runtime, phiên bản major của cuDNN và driver. GPU đời mới có thể cần ONNX Runtime mới hơn; thay đổi phiên bản cần được kiểm tra cùng CUDA/cuDNN tương ứng. Bản 1.20.2 không đảm bảo hỗ trợ mọi GPU hiện hành.

## 5. Quy tắc phiên và timeline

- Mỗi người chỉ có một phiên đang mở trong từng nguồn phân tích. Lần nhận diện được xác nhận đầu tiên mở phiên; các lần tiếp theo cập nhật `last_seen` trong RAM.
- Gallery dùng embedding đã lưu, không trích xuất lại ảnh tham chiếu ở mỗi frame.
- Tracker liên kết bằng IoU và yêu cầu hai kết quả liên tiếp có cùng danh tính. Việc gán nhãn cũng phải đạt ngưỡng cosine và khoảng cách điểm giữa hai danh tính. Kết quả không đủ tin cậy được hiển thị là **Không xác định**.
- Mất dấu ngắn không đóng phiên. Mặc định, vắng quá 30 giây sẽ đóng phiên; lần xuất hiện sau mở phiên mới. Thời điểm checkout là lần nhận diện cuối cùng, không cộng thời gian chờ.
- Camera dùng Unix timestamp và monotonic clock cho timeout. Giờ hiển thị/CSV có offset múi giờ máy. Nếu đồng hồ bị chỉnh lùi, `last_seen` không nhỏ hơn `first_seen`; đồng bộ đồng hồ hệ điều hành trước khi vận hành.
- Video dùng vị trí media tính bằng giây/millisecond, không dùng giờ phát trên máy. SHA-256 của toàn bộ nội dung định danh video; đổi tên hoặc sao chép không đổi nguồn. Việc tính hash chạy nền và có thể mất thời gian với video lớn. Metadata ngày quay không được suy đoán hoặc tự áp dụng.
- Seek, tắt ghi hoặc đổi nguồn làm tăng epoch, loại bỏ frame/kết quả cũ và đóng phiên hiện tại. Khi phân tích lại cùng video, các khoảng trùng/chồng lấn hoặc cách nhau không quá thời gian vắng mặt được hợp nhất trong giao dịch SQLite. Hợp nhất bắc cầu để tránh tạo nhiều bản ghi trùng khi replay.
- Tạm dừng không tính thêm thời gian vắng mặt. Seek khi video đang dừng xử lý một frame tại vị trí đích.
- Backend OpenCV cần cung cấp FPS và số frame hợp lệ. Với video CFR, ứng dụng ưu tiên POS_MSEC và đối chiếu frame_index/FPS; nếu timestamp từ backend không hợp lệ, dùng frame_index/FPS. Timestamp từng frame của video VFR không được đảm bảo khi backend thiếu PTS; chuyển video sang MP4 CFR khi cần timeline chính xác.
- Pipeline lấy mẫu frame mới nhất nên không đảm bảo nhận diện mọi frame. Tăng Hz hoặc giảm tốc độ phát để phân tích đoạn ngắn; cần đánh giá trên dữ liệu vận hành.
- Phiên được lưu khi mở/đóng và checkpoint phần thay đổi khoảng 2 giây. Đóng ứng dụng bình thường sẽ flush toàn bộ dữ liệu. Mất điện hoặc kết thúc tiến trình cưỡng bức có thể làm mất phần cập nhật kể từ checkpoint gần nhất. Khi khởi động lại, phiên bị gián đoạn được đóng tại `last_seen` đã lưu.

## 6. Dữ liệu và quyền riêng tư

Thư mục dữ liệu mặc định là `%USERPROFILE%\FaceTrackDesktop\`, gồm:

- `settings.json`: cài đặt
- `facetrack.sqlite3`: cơ sở dữ liệu
- `images\<person-uuid>\<reference-uuid>.jpg`: ảnh tham chiếu
- `insightface`: model

Biến `FACETRACK_HOME` đặt thư mục dữ liệu khác. Không commit dữ liệu người dùng vào mã nguồn. Thay đường dẫn trong Cài đặt không di chuyển ảnh/DB và không cập nhật đường dẫn ảnh đã lưu. Sao lưu và lập kế hoạch di chuyển khi ứng dụng đã đóng.

Xóa lịch sử không xóa hồ sơ hoặc embedding. Xóa hồ sơ sẽ xóa ảnh/embedding, giữ snapshot ID/tên trong lịch sử và đặt khóa ngoại `person_ref` thành NULL. Tên trong lịch sử là tên tại thời điểm ghi nhận và không thay đổi khi sửa tên hồ sơ. Hồ sơ ngừng hoạt động vẫn giữ ảnh nhưng bị loại khỏi gallery so khớp. Khi xóa lịch sử hoặc hồ sơ, nguồn đang chạy sẽ dừng để tránh ghi lại dữ liệu đã xóa; cần bắt đầu lại nguồn để tiếp tục.

CSV gồm bốn cột, mã hóa UTF-8 BOM và một hàng cho mỗi phiên. Thời gian video có định dạng `Video [sha256:…] HH:MM:SS.mmm`; thời gian camera dùng ISO 8601 kèm offset. Tên bắt đầu bằng ký tự công thức Excel được thêm dấu nháy đơn để tránh thực thi công thức.

Ảnh chưa đăng ký không được lưu thành hồ sơ. Ứng dụng không tải ảnh/embedding lên dịch vụ bên ngoài và không ghi embedding vào debug log. Chỉ thu thập dữ liệu khi có căn cứ và sự cho phép phù hợp. SQLite và ảnh chưa được mã hóa; sử dụng quyền truy cập Windows và mã hóa ổ đĩa khi cần. Sao lưu cả DB lẫn ảnh khi ứng dụng đã đóng. Không chỉ sao chép tệp SQLite đang mở vì WAL có thể còn giao dịch.

## 7. Kiểm thử và đóng gói

Chạy kiểm thử và chẩn đoán model:

```bat
.venv-cpu\Scripts\python -m pytest -q
.venv-cpu\Scripts\python main.py --backend cpu --diagnose
```

Unit/integration tests dùng embedding tổng hợp, detector thay thế có kiểm soát, SQLite thật, video AVI tổng hợp qua OpenCV và GUI Qt offscreen. Không cần camera vật lý hoặc tải trọng số để chạy bộ kiểm thử. Dùng `--diagnose` để kiểm tra model thật trên máy triển khai. Kịch bản nghiệm thu thủ công nằm tại `docs/MANUAL_TESTS.md`.

Đóng gói CPU bằng PyInstaller trên Windows, trong môi trường đã cài đủ dependency:

```bat
tools\build_exe.bat
```

Phân phối toàn bộ thư mục `dist\FaceTrackDesktop\` ở chế độ onedir. Trọng số được cài riêng trong user profile. Kiểm tra ứng dụng trên Windows sạch, gồm Qt platform plugins và ONNX DLL. PyInstaller không đóng gói CUDA/driver hệ thống. Script build chưa được xác nhận trên Windows. Bản GPU cần môi trường riêng, kiểm tra DLL và rà soát giấy phép runtime.

## 8. Cấu trúc dự án

- `main.py`: CLI, single-instance lock và khởi động GUI.
- `app/config.py`, `app/models`: cấu hình và dữ liệu frame/face.
- `app/ui`: năm trang giao diện và vẽ nhãn Unicode bằng QPainter.
- `app/workers/pipeline.py`: capture thread, recognition thread, mailbox một frame và epoch gate; không dùng hàng đợi frame vô hạn.
- `app/services`: engine, matcher, tracker, enrollment, session, SQLite actor, CSV, camera và video timestamp.
- `tests`: kiểm thử độc lập thiết bị.
- `tools`: cài model và build EXE.


