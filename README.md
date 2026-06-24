# Brain Tumor Detection AI

Hệ thống hỗ trợ phân loại ảnh MRI não bằng mô hình học sâu EfficientNetB0, kết hợp
quản lý bệnh nhân, lịch sử dự đoán, phân quyền người dùng và bản đồ Grad-CAM giải
thích vùng ảnh mà mô hình tập trung.

> **Lưu ý y khoa:** Dự án phục vụ mục đích học tập và nghiên cứu. Kết quả của mô
> hình không thay thế chẩn đoán, kết luận hoặc chỉ định điều trị của bác sĩ.

## Nội dung

- [Tổng quan](#tổng-quan)
- [Tính năng](#tính-năng)
- [Mô hình AI](#mô-hình-ai)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Yêu cầu](#yêu-cầu)
- [Khởi chạy nhanh bằng Docker](#khởi-chạy-nhanh-bằng-docker)
- [Tài khoản demo](#tài-khoản-demo)
- [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
- [Chạy backend cục bộ](#chạy-backend-cục-bộ)
- [Huấn luyện và đánh giá mô hình](#huấn-luyện-và-đánh-giá-mô-hình)
- [Cấu hình](#cấu-hình)
- [API và health check](#api-và-health-check)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Dữ liệu và model](#dữ-liệu-và-model)
- [Xử lý lỗi thường gặp](#xử-lý-lỗi-thường-gặp)
- [Bảo mật và giới hạn](#bảo-mật-và-giới-hạn)

## Tổng quan

Hệ thống nhận ảnh MRI định dạng JPG, JPEG hoặc PNG và phân loại thành một trong
bốn nhóm:

| Nhãn hệ thống | Ý nghĩa |
| --- | --- |
| `glioma_tumor` | U thần kinh đệm |
| `meningioma_tumor` | U màng não |
| `pituitary_tumor` | U tuyến yên |
| `no_tumor` | Không phát hiện u |

Dự án bao gồm cả quy trình nghiên cứu mô hình và ứng dụng web:

- notebook khám phá, tiền xử lý, huấn luyện và đánh giá dữ liệu;
- backend FastAPI chạy inference bằng EfficientNetB0;
- PostgreSQL lưu tài khoản, bệnh nhân, dự đoán và audit log;
- frontend HTML/CSS/JavaScript phục vụ bác sĩ và quản trị viên;
- Nginx chuyển tiếp API và ảnh MRI/Grad-CAM;
- Docker Compose khởi chạy toàn bộ hệ thống.

## Tính năng

### Dành cho bác sĩ

- Đăng nhập bằng username hoặc email.
- Tạo và cập nhật bệnh nhân do mình quản lý.
- Chỉ xem dữ liệu bệnh nhân và lịch sử dự đoán thuộc phạm vi được cấp.
- Tải ảnh MRI lên để chạy phân loại.
- Xem lớp dự đoán, độ tin cậy và ảnh Grad-CAM.
- Xem lại lịch sử dự đoán.

### Dành cho quản trị viên

- Xem danh sách toàn bộ tài khoản; bác sĩ không có quyền này.
- Tạo, cập nhật, khóa, mở khóa và đặt lại mật khẩu tài khoản.
- Xem dữ liệu bệnh nhân và dự đoán trên toàn hệ thống.
- Xem audit log.
- Dọn các file MRI và Grad-CAM đã hết thời hạn lưu.

### An toàn và vận hành

- JWT authentication và mật khẩu băm bằng Argon2.
- Rate limit đăng nhập theo cả tài khoản và địa chỉ IP.
- Audit log cho đăng nhập, tài khoản, bệnh nhân và dự đoán.
- Giới hạn ảnh tải lên mặc định 10 MB.
- File MRI và Grad-CAM mặc định hết hạn sau 24 giờ.
- Health check kiểm tra cả PostgreSQL và khả năng inference của model.
- Lần inference thất bại được lưu để truy vết nhưng API trả trạng thái lỗi, không
  giả làm kết quả thành công.

## Mô hình AI

Backend sử dụng model `best_tl_model.h5` dựa trên **EfficientNetB0**, nhận tensor
RGB kích thước `240 × 240`.

Kết quả đánh giá hiện có:

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 |
| --- | ---: | ---: | ---: | ---: |
| CNN Tuned | 0.7497 | 0.7551 | 0.7516 | 0.7438 |
| EfficientNetB0 Tuned | **0.8862** | **0.8866** | **0.8874** | **0.8854** |

EfficientNetB0 là model có kết quả tốt nhất và cũng là model được triển khai
trong backend. Grad-CAM được tạo từ lớp convolution phù hợp để minh họa vùng ảnh
ảnh hưởng tới dự đoán.

## Kiến trúc hệ thống

```text
Trình duyệt
    |
    v
Nginx frontend :8080
    |-- /                 -> HTML, CSS, JavaScript
    |-- /api/*            -> FastAPI :8000
    `-- /storage/*        -> ảnh MRI và Grad-CAM
                              |
                              +-- EfficientNetB0
                              +-- PostgreSQL :5432
                              `-- storage/
```

Các thành phần Docker:

| Service | Vai trò |
| --- | --- |
| `postgres` | Lưu dữ liệu nghiệp vụ |
| `database-init` | Tạo schema và nạp dữ liệu demo |
| `backend` | API, xác thực, inference và Grad-CAM |
| `frontend` | Nginx và giao diện web |

## Yêu cầu

### Cách khuyến nghị

- Docker Desktop hoặc Docker Engine có Docker Compose.
- Ít nhất khoảng 4 GB RAM trống để nạp TensorFlow và model.
- File `best_tl_model.h5` nằm ở thư mục gốc dự án.

### Khi chạy Python trực tiếp

- Python 3.11.
- PostgreSQL 16 hoặc phiên bản tương thích.
- Các thư viện trong `requirement.txt`.

Frontend dùng HTML, CSS và JavaScript thuần, không cần cài npm package. Giao diện
sử dụng font Inter từ Google Fonts.

## Khởi chạy nhanh bằng Docker

Đây là cách chạy đầy đủ và ít cấu hình nhất.

### 1. Chuẩn bị dự án

Đảm bảo file model tồn tại:

```text
Brain-Tumor-Detection-AI/
  best_tl_model.h5
  docker-compose.yml
  requirement.txt
```

### 2. Tạo file môi trường

Trên Linux/macOS:

```bash
cp .env.example .env
```

Trên PowerShell:

```powershell
Copy-Item .env.example .env
```

Trước khi triển khai thật, phải đổi ít nhất:

```env
POSTGRES_PASSWORD=your-strong-database-password
SECRET_KEY=your-long-random-secret
ENVIRONMENT=production
```

### 3. Build và khởi động

```bash
docker compose up --build
```

Lần khởi động đầu có thể chậm do cài TensorFlow và warm-up model. Khi các service
đã healthy, truy cập:

| Thành phần | Địa chỉ |
| --- | --- |
| Giao diện | <http://localhost:8080> |
| Swagger API | <http://localhost:8000/docs> |
| Health check | <http://localhost:8000/health> |

### 4. Xem log

```bash
docker compose logs -f
```

Hoặc chỉ xem một thành phần:

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
docker compose logs -f database-init
```

### 5. Dừng hệ thống

```bash
docker compose down
```

Lệnh trên giữ nguyên dữ liệu PostgreSQL. Muốn xóa database và khởi tạo lại từ
đầu:

```bash
docker compose down -v
docker compose up --build
```

## Tài khoản demo

Database tự tạo hai tài khoản:

| Vai trò | Username | Email | Mật khẩu |
| --- | --- | --- | --- |
| Admin | `admin` | `admin@example.com` | `Admin@123456` |
| Bác sĩ | `doctor01` | `doctor01@example.com` | `Doctor@123456` |

> Chỉ sử dụng các mật khẩu này để demo cục bộ. Hãy đổi hoặc xóa tài khoản mẫu
> trước khi đưa hệ thống lên môi trường có người dùng thật.

## Hướng dẫn sử dụng

### Quy trình dành cho bác sĩ

1. Mở <http://localhost:8080> và đăng nhập bằng tài khoản bác sĩ.
2. Vào **Bệnh nhân** để chọn bệnh nhân có sẵn hoặc tạo hồ sơ mới.
3. Mở **Chẩn đoán**, chọn bệnh nhân và tải ảnh MRI lên.
4. Nhấn thực hiện chẩn đoán và chờ model xử lý.
5. Kiểm tra lớp dự đoán, độ tin cậy, ảnh MRI gốc và Grad-CAM.
6. Mở **Lịch sử** để xem lại các lần dự đoán.

Ảnh hợp lệ:

- JPG, JPEG hoặc PNG;
- dung lượng không vượt quá 10 MB theo cấu hình mặc định;
- nên là ảnh MRI não rõ ràng và đúng vùng khảo sát.

### Quy trình dành cho admin

1. Đăng nhập bằng tài khoản admin.
2. Vào **Tài khoản** để xem và quản lý toàn bộ tài khoản.
3. Vào **Bệnh nhân** hoặc **Lịch sử** để kiểm tra dữ liệu toàn hệ thống.
4. Vào **Audit log** để theo dõi các hành động quan trọng.
5. Dùng API dọn file hết hạn khi cần.

## Chạy backend cục bộ

Docker vẫn là cách được khuyến nghị cho toàn hệ thống. Nếu cần phát triển riêng
backend:

### 1. Tạo môi trường Python

```bash
python -m venv .venv
```

Kích hoạt trên PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Kích hoạt trên Linux/macOS:

```bash
source .venv/bin/activate
```

### 2. Cài thư viện

```bash
pip install -r requirement.txt
```

File duy nhất này chia dependency thành bốn nhóm: dùng chung, backend, frontend
và train model.

### 3. Chuẩn bị PostgreSQL

Tạo database theo thông tin trong `.env`, sau đó chạy:

```bash
psql -U admin -d mydatabase -f backend/database/schema.sql
psql -U admin -d mydatabase -f backend/database/seed.sql
```

### 4. Chạy API

Từ thư mục `backend`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend mặc định đọc model tại `best_tl_model.h5` ở thư mục gốc và lưu ảnh vào
`storage/`.

> Frontend dựa vào Nginx để proxy `/api/` và `/storage/`. Vì vậy, để dùng giao
> diện hoàn chỉnh, nên chạy bằng Docker Compose thay vì mở trực tiếp file HTML.

## Huấn luyện và đánh giá mô hình

Chạy notebook theo thứ tự:

| Thứ tự | Notebook | Mục đích |
| ---: | --- | --- |
| 1 | `01_EDA.ipynb` | Khám phá phân bố, kích thước và đặc trưng ảnh |
| 2 | `02_Preprocessing_v2.ipynb` | Crop ROI, chuẩn hóa và chuẩn bị dữ liệu |
| 3 | `03_Model_v3.ipynb` | Huấn luyện CNN và EfficientNetB0 |
| 4 | `04_Evaluation_v2.ipynb` | Đánh giá, confusion matrix, ROC và Grad-CAM |

Có thể mở notebook bằng Jupyter:

```bash
jupyter notebook
```

Nếu môi trường chưa có Jupyter, có thể chạy notebook bằng Google Colab. Việc
huấn luyện nên dùng GPU.

Kết quả huấn luyện hiện tại nằm trong `colab_tuned_results_20260621/`, gồm:

- biểu đồ lịch sử huấn luyện;
- bảng so sánh CNN và EfficientNetB0;
- confusion matrix;
- kết quả test dạng JSON;
- metric validation theo từng giai đoạn.

## Cấu hình

Các biến thường dùng trong `.env`:

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `POSTGRES_USER` | `admin` | Tài khoản PostgreSQL |
| `POSTGRES_PASSWORD` | `admin123` | Mật khẩu PostgreSQL |
| `POSTGRES_DB` | `mydatabase` | Tên database |
| `POSTGRES_PORT` | `5432` | Cổng PostgreSQL trên máy host |
| `BACKEND_PORT` | `8000` | Cổng backend |
| `FRONTEND_PORT` | `8080` | Cổng frontend |
| `ENVIRONMENT` | `development` | Môi trường chạy |
| `DEBUG` | `false` | Bật/tắt debug |
| `SECRET_KEY` | giá trị demo | Khóa ký JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Thời hạn access token trong Docker |
| `LOGIN_MAX_FAILED_ATTEMPTS` | `5` | Số lần sai tối đa theo tài khoản |
| `LOGIN_IP_MAX_FAILED_ATTEMPTS` | `20` | Số lần sai tối đa theo IP |
| `LOGIN_ATTEMPT_WINDOW_MINUTES` | `15` | Cửa sổ đếm lần đăng nhập sai |
| `LOGIN_LOCKOUT_MINUTES` | `15` | Thời gian khóa tạm |
| `LOG_LEVEL` | `INFO` | Mức log |
| `LOG_TO_FILE` | `false` | Có ghi log ra file hay không |

Sau 5 lần sai với cùng tài khoản hoặc 20 lần sai từ cùng IP trong cửa sổ mặc
định 15 phút, API khóa tạm và trả `429 Too Many Requests` cùng header
`Retry-After`.

## API và health check

Toàn bộ API nghiệp vụ có prefix:

```text
/api/v1
```

Nhóm endpoint chính:

| Nhóm | Đường dẫn | Quyền |
| --- | --- | --- |
| Xác thực | `/api/v1/auth` | Công khai/đã đăng nhập |
| Tài khoản | `/api/v1/users` | Admin |
| Bệnh nhân | `/api/v1/patients` | Bác sĩ và admin |
| Dự đoán | `/api/v1/predictions` | Bác sĩ và admin |
| Audit log | `/api/v1/audit-logs` | Admin |

Tài liệu chi tiết và mẫu request có tại Swagger:

```text
http://localhost:8000/docs
```

Health check:

```text
GET http://localhost:8000/health
```

Hệ thống chỉ trả `"status": "ok"` khi:

- kết nối PostgreSQL thành công;
- file model tồn tại;
- model load đúng cấu trúc;
- warm-up inference thành công.

Nếu một thành phần chưa sẵn sàng, health check trả `"status": "degraded"` và
frontend Docker sẽ chờ backend healthy.

## Cấu trúc dự án

```text
Brain-Tumor-Detection-AI/
|-- 01_EDA.ipynb
|-- 02_Preprocessing_v2.ipynb
|-- 03_Model_v3.ipynb
|-- 04_Evaluation_v2.ipynb
|-- backend/
|   |-- app/                 # FastAPI, model service và nghiệp vụ
|   |-- database/            # schema.sql và seed.sql
|   |-- dockerfile
|   `-- scripts/
|-- frontend/
|   |-- css/
|   |-- img/
|   |-- js/
|   |-- *.html
|   |-- Dockerfile
|   `-- nginx.conf
|-- colab_tuned_results_20260621/
|-- storage/
|   |-- mri/
|   `-- gradcam/
|-- best_tl_model.h5
|-- docker-compose.yml
|-- requirement.txt
|-- .env.example
`-- README.md
```

## Dữ liệu và model

Dữ liệu MRI và model có thể có dung lượng lớn. Cấu trúc dùng cho notebook:

```text
data/
|-- Training/
`-- Testing/

data_processed_roi/
|-- Training/
`-- Testing/
```

Nguồn file ngoài của dự án:

<https://drive.google.com/drive/folders/11Rmcl51P1w5LY5rlDxv3wDPikEoIuGcb?usp=drive_link>

Sau khi huấn luyện lại, model triển khai phải:

- được lưu với tên `best_tl_model.h5`;
- nhận ảnh RGB kích thước `240 × 240`;
- xuất bốn xác suất theo đúng thứ tự:
  `glioma_tumor`, `meningioma_tumor`, `no_tumor`, `pituitary_tumor`.

Nếu thứ tự nhãn thay đổi, phải cập nhật đồng thời cấu hình backend để tránh trả
kết quả sai tên lớp.

## Xử lý lỗi thường gặp

### Backend không healthy

Kiểm tra:

```bash
docker compose logs backend
docker compose logs postgres
curl http://localhost:8000/health
```

Nguyên nhân thường gặp:

- thiếu hoặc hỏng `best_tl_model.h5`;
- PostgreSQL chưa sẵn sàng;
- model không tương thích phiên bản TensorFlow;
- máy không đủ RAM để load model.

### Frontend chưa mở được sau khi khởi động

Frontend đợi backend healthy. Lần build đầu và warm-up TensorFlow có thể mất một
khoảng thời gian. Theo dõi:

```bash
docker compose ps
docker compose logs -f backend
```

### Ảnh MRI hoặc Grad-CAM không hiển thị

Kiểm tra thư mục `storage/`, quyền ghi của Docker và proxy `/storage/` trong
Nginx. Không đổi thủ công đường dẫn ảnh đã lưu trong database.

### Không đăng nhập được bằng tài khoản demo

Nếu đã thay đổi database trước đó, seed có thể không khôi phục mật khẩu cũ. Để
khởi tạo lại hoàn toàn dữ liệu demo:

```bash
docker compose down -v
docker compose up --build
```

Lệnh này xóa toàn bộ dữ liệu PostgreSQL hiện tại.

### API trả 429

Tài khoản hoặc IP đang bị khóa tạm do thử sai liên tục. Chờ hết thời gian trong
header `Retry-After`, hoặc kiểm tra cấu hình rate limit trong `.env`.

## Bảo mật và giới hạn

- Đổi `SECRET_KEY`, mật khẩu PostgreSQL và tài khoản demo khi triển khai thật.
- Chỉ cho phép domain frontend thực tế trong CORS.
- Nên đặt hệ thống sau HTTPS và reverse proxy phù hợp.
- JWT hiện là stateless; đăng xuất xóa token phía trình duyệt nhưng không tạo
  blacklist token ở server.
- Ảnh MRI là dữ liệu nhạy cảm. Cần bổ sung chính sách lưu trữ, mã hóa, sao lưu,
  đồng ý sử dụng và phân quyền phù hợp với quy định tại nơi triển khai.
- Grad-CAM chỉ là công cụ giải thích trực quan, không chứng minh quan hệ nhân quả
  và không bảo đảm dự đoán đúng.
- Accuracy 88,62% trên tập đánh giá không đồng nghĩa với hiệu quả lâm sàng trên
  bệnh viện, máy chụp hoặc quần thể khác.
