# Brain Tumor Detection AI

Hệ thống web hỗ trợ phân loại ảnh MRI não bằng mô hình học sâu, quản lý hồ sơ
bệnh nhân và theo dõi toàn bộ quy trình dự đoán. Ứng dụng cung cấp xác suất cho
bốn lớp, ảnh Grad-CAM giải thích vùng mô hình tập trung, dashboard thống kê,
đánh giá kết quả AI của bác sĩ và nhật ký kiểm toán dành cho quản trị viên.

> [!WARNING]
> Dự án phục vụ mục đích học tập và nghiên cứu. Kết quả từ mô hình không thay
> thế chẩn đoán, kết luận lâm sàng hoặc chỉ định điều trị của bác sĩ.

## Tính năng chính

### Phân loại MRI và giải thích kết quả

- Nhận ảnh `JPG`, `JPEG` hoặc `PNG`, dung lượng tối đa mặc định 10 MB.
- Phân loại ảnh MRI thành bốn nhóm:

  | Nhãn hệ thống | Ý nghĩa |
  | --- | --- |
  | `glioma_tumor` | U thần kinh đệm |
  | `meningioma_tumor` | U màng não |
  | `pituitary_tumor` | U tuyến yên |
  | `no_tumor` | Không phát hiện u |

- Hiển thị lớp dự đoán, độ tin cậy và xác suất của toàn bộ các lớp.
- Sinh ảnh Grad-CAM để trực quan hóa vùng ảnh ảnh hưởng đến dự đoán.
- Lưu cả lần dự đoán thành công và thất bại để hỗ trợ truy vết.

### Nghiệp vụ bác sĩ

- Đăng nhập bằng username hoặc email.
- Xem dashboard theo đúng phạm vi dữ liệu được cấp.
- Tạo, tìm kiếm và cập nhật hồ sơ bệnh nhân.
- Tự động sinh mã bệnh nhân duy nhất dạng `BN000001`.
- Chuẩn hóa số điện thoại và cảnh báo hồ sơ có khả năng bị tạo trùng.
- Xem chi tiết bệnh nhân cùng toàn bộ lịch sử MRI liên quan.
- Lọc lịch sử theo bệnh nhân, bác sĩ, kết quả, trạng thái xử lý, trạng thái đánh
  giá và khoảng thời gian.
- Xác nhận hoặc bác bỏ kết quả AI, lưu kết luận lâm sàng và ghi chú. Chỉ bác sĩ
  đã thực hiện lần dự đoán mới được sửa phần đánh giá đó.

### Nghiệp vụ quản trị

- Quản lý tài khoản bác sĩ và quản trị viên.
- Tạo, cập nhật, khóa/mở khóa và đặt lại mật khẩu tài khoản.
- Xem dữ liệu bệnh nhân và dự đoán trên toàn hệ thống.
- Xem audit log theo người thực hiện, hành động và đối tượng bị tác động.
- Xóa file MRI và Grad-CAM đã hết hạn mà không xóa lịch sử dự đoán.

### Bảo mật và vận hành

- Xác thực JWT; mật khẩu được băm bằng Argon2.
- Phân quyền `admin` và `doctor` tại backend.
- Giới hạn đăng nhập sai theo cả tài khoản và địa chỉ IP.
- Audit log cho đăng nhập, tài khoản, bệnh nhân, dự đoán và đánh giá AI.
- Ảnh MRI/Grad-CAM mặc định được giữ 24 giờ; bản ghi kết quả vẫn tồn tại sau khi
  file ảnh bị dọn.
- Health check kiểm tra kết nối PostgreSQL, cấu trúc model và warm-up inference.

## Công nghệ

| Thành phần | Công nghệ |
| --- | --- |
| AI/Computer Vision | TensorFlow/Keras, OpenCV, Pillow, NumPy |
| Backend | FastAPI, SQLAlchemy 2, Pydantic 2, Uvicorn |
| Database | PostgreSQL 16 |
| Authentication | JWT, Argon2 |
| Frontend | HTML, CSS, JavaScript thuần |
| Web server | Nginx |
| Triển khai | Docker Compose |

## Kiến trúc hệ thống

```text
Trình duyệt
    |
    v
Frontend Nginx :8080
    |-- /                 HTML, CSS, JavaScript
    |-- /api/*            FastAPI :8000
    `-- /storage/*        MRI và Grad-CAM
                              |
                              |-- CNN inference
                              |-- Grad-CAM
                              `-- PostgreSQL :5432
```

Docker Compose khởi tạo bốn service:

| Service | Vai trò |
| --- | --- |
| `postgres` | Lưu tài khoản, bệnh nhân, dự đoán, giới hạn đăng nhập và audit log |
| `database-init` | Tạo/cập nhật schema và nạp dữ liệu demo |
| `backend` | Xác thực, API nghiệp vụ, inference và Grad-CAM |
| `frontend` | Phục vụ giao diện và reverse proxy tới backend |

## Khởi chạy nhanh bằng Docker

### Yêu cầu

- Docker Desktop hoặc Docker Engine có Docker Compose.
- Khoảng 4 GB RAM trống để nạp TensorFlow và model.
- File `best_cnn_model.h5` tại thư mục gốc dự án.

### 1. Tạo file môi trường

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Các giá trị mặc định phù hợp để demo cục bộ. Khi triển khai thực tế, tối thiểu
phải đổi:

```env
POSTGRES_PASSWORD=your-strong-database-password
SECRET_KEY=your-long-random-secret
ENVIRONMENT=production
```

### 2. Build và chạy hệ thống

```bash
docker compose up --build
```

Lần chạy đầu có thể mất vài phút do cài TensorFlow, nạp model và warm-up
inference. Khi các container đã sẵn sàng:

| Thành phần | Địa chỉ |
| --- | --- |
| Giao diện web | <http://localhost:8080> |
| Swagger API | <http://localhost:8000/docs> |
| Health check backend | <http://localhost:8000/health> |

### 3. Tài khoản demo

| Vai trò | Username | Email | Mật khẩu |
| --- | --- | --- | --- |
| Admin | `admin` | `admin@example.com` | `Admin@123456` |
| Bác sĩ | `doctor01` | `doctor01@example.com` | `Doctor@123456` |

> [!IMPORTANT]
> Chỉ dùng các tài khoản trên để demo cục bộ. Hãy đổi mật khẩu hoặc xóa tài
> khoản mẫu trước khi dùng hệ thống với dữ liệu thật.

### 4. Dừng hoặc khởi tạo lại

Dừng hệ thống nhưng giữ database:

```bash
docker compose down
```

Xóa volume PostgreSQL và tạo lại toàn bộ dữ liệu demo:

```bash
docker compose down -v
docker compose up --build
```

Lệnh `down -v` xóa toàn bộ dữ liệu hiện có trong database.

## Quy trình sử dụng

### Bác sĩ

1. Đăng nhập tại <http://localhost:8080>.
2. Mở **Bệnh nhân**, chọn hồ sơ hiện có hoặc tạo hồ sơ mới.
3. Mở **Dự đoán MRI**, chọn bệnh nhân và tải ảnh MRI lên.
4. Kiểm tra kết quả phân loại, xác suất và ảnh Grad-CAM.
5. Mở **Lịch sử**, chọn lần dự đoán cần xem.
6. Lưu trạng thái đánh giá AI, kết luận lâm sàng và ghi chú chuyên môn.

### Quản trị viên

1. Mở **Tài khoản** để quản lý người dùng.
2. Theo dõi số liệu tổng hợp tại **Dashboard**.
3. Tra cứu bệnh nhân và lịch sử dự đoán trên toàn hệ thống.
4. Mở **Audit log** để kiểm tra các hành động quan trọng.
5. Dùng nút **Xóa file hết hạn** tại trang lịch sử khi cần dọn storage.

## Mô hình AI

Backend hiện triển khai model CNN trong `best_cnn_model.h5`.

- Input: ảnh RGB kích thước `240 × 240`.
- Model có sẵn lớp `Rescaling(1/255)`, vì vậy backend truyền pixel ở thang
  `0..255`.
- Output: bốn xác suất theo đúng thứ tự:

  ```text
  glioma_tumor
  meningioma_tumor
  no_tumor
  pituitary_tumor
  ```

- Grad-CAM ưu tiên lớp convolution `conv2d_13` và tự tìm lớp Conv2D cuối nếu
  kiến trúc model thay đổi.

Kết quả đánh giá được ghi nhận trong notebook hiện tại:

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 |
| --- | ---: | ---: | ---: | ---: |
| CNN Tuned | 74,97% | 75,51% | 75,16% | 74,38% |
| EfficientNetB0 Tuned | **88,62%** | **88,66%** | **88,74%** | **88,54%** |

`best_tl_model.h5` là model transfer learning phục vụ nghiên cứu và so sánh.
Ứng dụng web hiện vẫn chủ động dùng `best_cnn_model.h5`.

> Accuracy trên tập kiểm thử không đồng nghĩa với hiệu quả lâm sàng trên dữ liệu
> từ bệnh viện, máy chụp hoặc quần thể khác.

## Notebook nghiên cứu

Chạy notebook theo thứ tự:

| Thứ tự | Notebook | Nội dung |
| ---: | --- | --- |
| 1 | `01_EDA.ipynb` | Khám phá phân bố, kích thước và đặc trưng dữ liệu |
| 2 | `02_Preprocessing_v2.ipynb` | Crop ROI, chuẩn hóa và chuẩn bị dữ liệu |
| 3 | `03_Model_v3.ipynb` | Huấn luyện CNN và EfficientNetB0 |
| 4 | `04_Evaluation_v2.ipynb` | Đánh giá metric, confusion matrix, ROC và Grad-CAM |

Cấu trúc dữ liệu notebook mong đợi:

```text
data/
|-- Training/
`-- Testing/

data_processed_roi/
|-- Training/
`-- Testing/
```

Dữ liệu và artifact dung lượng lớn không được commit vào Git. Nguồn lưu trữ
được sử dụng trong dự án:

<https://drive.google.com/drive/folders/11Rmcl51P1w5LY5rlDxv3wDPikEoIuGcb?usp=drive_link>

## API

Prefix chung:

```text
/api/v1
```

| Nhóm | Endpoint chính | Quyền |
| --- | --- | --- |
| Xác thực | `/auth/login`, `/auth/me`, `/auth/logout` | Công khai/đã đăng nhập |
| Dashboard | `/dashboard/statistics` | Doctor, Admin |
| Tài khoản | `/users` | Admin |
| Bệnh nhân | `/patients` | Doctor, Admin |
| Kiểm tra trùng | `/patients/duplicate-check` | Doctor, Admin |
| Dự đoán | `/predictions` | Doctor, Admin |
| Đánh giá AI | `/predictions/{id}/review` | Bác sĩ thực hiện dự đoán |
| Dọn file hết hạn | `/predictions/cleanup-expired-files` | Admin |
| Audit log | `/audit-logs` | Admin |

Swagger tại <http://localhost:8000/docs> cung cấp đầy đủ schema, query parameter
và mẫu request/response.

## Cấu hình

Các biến thường dùng trong `.env`:

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `POSTGRES_USER` | `admin` | Tài khoản PostgreSQL |
| `POSTGRES_PASSWORD` | `admin123` | Mật khẩu PostgreSQL |
| `POSTGRES_DB` | `mydatabase` | Tên database |
| `POSTGRES_PORT` | `5432` | Cổng PostgreSQL trên host |
| `BACKEND_PORT` | `8000` | Cổng backend |
| `FRONTEND_PORT` | `8080` | Cổng giao diện |
| `ENVIRONMENT` | `development` | `development`, `test` hoặc `production` |
| `DEBUG` | `false` | Bật/tắt debug FastAPI |
| `SECRET_KEY` | giá trị demo | Khóa ký JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Thời hạn access token trong Docker |
| `LOGIN_MAX_FAILED_ATTEMPTS` | `5` | Số lần sai tối đa theo tài khoản |
| `LOGIN_IP_MAX_FAILED_ATTEMPTS` | `20` | Số lần sai tối đa theo IP |
| `LOGIN_ATTEMPT_WINDOW_MINUTES` | `15` | Cửa sổ đếm đăng nhập sai |
| `LOGIN_LOCKOUT_MINUTES` | `15` | Thời gian khóa tạm |
| `LOG_LEVEL` | `INFO` | Mức log |
| `LOG_TO_FILE` | `false` | Ghi thêm log vào file |

Sau khi vượt ngưỡng đăng nhập sai, API trả `429 Too Many Requests` cùng header
`Retry-After`.

## Chạy backend trực tiếp

Docker Compose vẫn là cách khuyến nghị để chạy toàn hệ thống. Nếu chỉ phát triển
backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirement.txt
```

Khởi tạo PostgreSQL:

```bash
psql -U admin -d mydatabase -f backend/database/schema.sql
psql -U admin -d mydatabase -f backend/database/seed.sql
```

Chạy API từ thư mục `backend`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Khi chạy trực tiếp, hãy bảo đảm PostgreSQL đang hoạt động và các biến
`DATABASE_URL`, `SECRET_KEY` đã được đặt đúng. Frontend phụ thuộc proxy của
Nginx cho `/api/` và `/storage/`, vì vậy nên dùng Docker Compose nếu cần kiểm
thử đầy đủ giao diện.

## Cấu trúc dự án

```text
Brain-Tumor-Detection-AI/
|-- backend/
|   |-- app/
|   |   |-- api/routes/       # Endpoint FastAPI
|   |   |-- core/             # Cấu hình, bảo mật, request utilities
|   |   |-- db/               # Kết nối SQLAlchemy
|   |   |-- models/           # ORM models
|   |   |-- schemas/          # Pydantic schemas
|   |   `-- services/         # Nghiệp vụ, inference, Grad-CAM
|   |-- database/             # schema.sql, seed.sql, reset.sql
|   `-- dockerfile
|-- frontend/
|   |-- css/
|   |-- img/
|   |-- js/
|   |-- *.html
|   |-- Dockerfile
|   `-- nginx.conf
|-- storage/
|   |-- mri/
|   `-- gradcam/
|-- 01_EDA.ipynb
|-- 02_Preprocessing_v2.ipynb
|-- 03_Model_v3.ipynb
|-- 04_Evaluation_v2.ipynb
|-- best_cnn_model.h5         # Model đang được backend sử dụng
|-- best_tl_model.h5          # Model transfer learning để nghiên cứu
|-- docker-compose.yml
|-- requirement.txt
|-- .env.example
`-- README.md
```

## Xử lý lỗi thường gặp

### Backend không healthy

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f postgres
```

Kiểm tra <http://localhost:8000/health>. Nguyên nhân thường gặp là thiếu/hỏng
`best_cnn_model.h5`, PostgreSQL chưa sẵn sàng, model không tương thích phiên bản
TensorFlow hoặc máy không đủ RAM.

### Không đăng nhập được bằng tài khoản demo

Database volume cũ có thể đang giữ dữ liệu trước đó. Nếu chấp nhận xóa toàn bộ
dữ liệu cục bộ:

```bash
docker compose down -v
docker compose up --build
```

### Ảnh MRI hoặc Grad-CAM không hiển thị

Kiểm tra thư mục `storage/`, quyền ghi của backend và proxy `/storage/` trong
Nginx. Nếu trường `files_deleted` đã là `true`, file ảnh đã hết hạn nhưng lịch
sử kết quả vẫn được giữ.

### API trả 429

Tài khoản hoặc IP đã bị khóa tạm do đăng nhập sai nhiều lần. Chờ hết thời gian
trong header `Retry-After` hoặc kiểm tra các biến `LOGIN_*` trong `.env`.

## Lưu ý khi triển khai

- Đổi `SECRET_KEY`, mật khẩu PostgreSQL và tài khoản demo.
- Giới hạn CORS về đúng domain frontend thực tế.
- Đặt hệ thống sau HTTPS/reverse proxy phù hợp.
- JWT hiện là stateless; đăng xuất xóa token ở trình duyệt nhưng chưa có
  blacklist token phía server.
- MRI là dữ liệu nhạy cảm. Cần bổ sung chính sách đồng ý sử dụng, mã hóa, sao
  lưu, thời hạn lưu trữ và phân quyền phù hợp với nơi triển khai.
- Grad-CAM chỉ là công cụ giải thích trực quan, không chứng minh quan hệ nhân quả
  và không bảo đảm dự đoán chính xác.
