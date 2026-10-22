# Đối chiếu API và dependency

Đối chiếu ngày 21/10/2026. Chọn InsightFace **0.7.3**, không triển khai dựa vào API
master đang thay đổi. Đã tải source distribution từ PyPI bằng
`pip download --no-deps insightface==0.7.3` và đọc trực tiếp các file bên trong.
Không bao gồm source bên thứ ba hoặc trọng số trong ZIP dự án.

SHA-256 của `insightface-0.7.3.tar.gz` đã kiểm tra:
`f191f719612ebb37018f41936814500544cd0f86e6fcd676c023f354c668ddf7`.

| API sử dụng | Xác nhận trong source 0.7.3 |
|---|---|
| `FaceAnalysis(name, root, allowed_modules, **kwargs)` | `insightface/app/face_analysis.py`; kwargs truyền tới model_zoo.get_model |
| `prepare(ctx_id, det_thresh=0.5, det_size=(640,640))` | Cùng file; recognition.prepare(ctx_id), detection.prepare(input_size=det_size) |
| `get(img, max_num=0)` | Trả danh sách Face có bbox, det_score và embedding từ recognition |
| `face.normed_embedding` | Property trong `insightface/app/common.py`, embedding / embedding_norm |
| `models['recognition'].get_feat(image)` | `model_zoo/arcface_onnx.py`; hỗ trợ BGR image hoặc list image |
| `model.session.get_providers()` | session ONNX Runtime của detector/recognizer |
| `ctx_id=-1` | `prepare` của model chuyển session về CPUExecutionProvider |
| `ensure_available('models', name, root)` | `utils/storage.py`; thư mục đã tồn tại sẽ không được tự tải lại |

Engine kiểm tra sẵn hai file buffalo_l trong thư mục model trước khi tạo
FaceAnalysis để không kích hoạt download tự động. Không gọi draw_on của upstream:
API đó có sử dụng np.int trong bản cũ và không hiển thị tốt tên tiếng Việt.
Nhãn được vẽ bằng QPainter.

Nguồn gốc và tài liệu tham khảo chính thức:

- PyPI phiên bản cố định: <https://pypi.org/project/insightface/0.7.3/>.
- Upstream: <https://github.com/deepinsight/insightface/tree/master/python-package>.
  Master chỉ để đối chiếu tham khảo; API adapter dựa vào sdist nêu trên.
- Mô hình: <https://github.com/deepinsight/insightface/releases/tag/v0.7>.
- ONNX Runtime CUDA: <https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html>.

Theo bảng ORT đã đọc, 1.20.x trên PyPI dùng CUDA 12.x và cuDNN 9.x; major cuDNN
8/9 không tương thích thay thế. Requirements giữ đúng 1.20.1 và tách CPU/GPU.
Không coi việc provider xuất hiện trong danh sách là kiểm thử GPU; diagnostics
còn tạo session và chạy warmup cả hai mạng. Khả năng tương thích package Windows,
driver và chất lượng nhận diện vẫn cần kiểm thử thực tế theo MANUAL_TESTS.
