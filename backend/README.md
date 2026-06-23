# Backend — Brain Tumor MRI Classification System

Backend dùng FastAPI để quản lý tài khoản, bệnh nhân, upload ảnh MRI, chạy model `best_cnn_model.h5`, tạo Grad-CAM và lưu lịch sử dự đoán vào PostgreSQL.

## Công nghệ sử dụng

- FastAPI
- PostgreSQL
- SQLAlchemy
- TensorFlow/Keras
- OpenCV, Pillow, NumPy
- Docker

## Cấu trúc chính

```text
backend/
├── app/
│   ├── api/          # Router API và dependency phân quyền
│   ├── core/         # Config, security, JWT, password hash
│   ├── db/           # Kết nối PostgreSQL
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas request/response
│   ├── services/     # Logic nghiệp vụ
│   └── main.py       # FastAPI app chính
├── database/
│   ├── reset.sql     # Xóa schema cũ
│   ├── schema.sql    # Tạo bảng/index/constraint
│   └── seed.sql      # Dữ liệu mẫu demo
├── scripts/
│   └── generate_password_hash.py
└── dockerfile
```

## Model AI

Backend dùng trực tiếp file model ở root project:

```text
best_cnn_model.h5
```

Không dùng folder `model/`.

Các label được cấu hình theo notebook train:

```text
glioma_tumor
meningioma_tumor
no_tumor
pituitary_tumor
```

Input size:

```text
240x240
```

Grad-CAM dùng Conv2D cuối:

```text
conv2d_13
```

## Chạy bằng Docker

Ở root project, chạy:

```bash
docker compose up --build
```

Backend chạy tại:

```text
http://localhost:8000
```

Health check:

```text
GET http://localhost:8000/health
```

Swagger UI:

```text
http://localhost:8000/docs
```

## Khởi tạo database

Sau khi `docker compose up` chạy PostgreSQL, tạo bảng:

```bash
docker exec -it brain_tumor_postgres psql -U admin -d mydatabase -f /database/schema.sql
```

Nạp dữ liệu mẫu:

```bash
docker exec -it brain_tumor_postgres psql -U admin -d mydatabase -f /database/seed.sql
```

Nếu muốn reset database rồi tạo lại từ đầu:

```bash
docker exec -it brain_tumor_postgres psql -U admin -d mydatabase -f /database/reset.sql
docker exec -it brain_tumor_postgres psql -U admin -d mydatabase -f /database/schema.sql
docker exec -it brain_tumor_postgres psql -U admin -d mydatabase -f /database/seed.sql
```

## Lưu ý về seed.sql

File `seed.sql` không lưu password thô. Trước khi chạy seed, cần thay:

```text
__REPLACE_WITH_ARGON2_HASH__
```

bằng password hash thật.

Sinh hash bằng:

```bash
python backend/scripts/generate_password_hash.py --password Admin@123456
```

Sau đó copy kết quả vào `seed.sql`.

Tài khoản demo dự kiến:

```text
Admin:
username: admin
email: admin@example.com
password: Admin@123456

Doctor:
username: doctor01
email: doctor01@example.com
password: Doctor@123456
```

## API chính

Base URL:

```text
http://localhost:8000/api/v1
```

Nhóm endpoint:

```text
/auth          đăng nhập, xem user hiện tại
/users         admin quản lý tài khoản
/patients      quản lý hồ sơ bệnh nhân
/predictions   upload MRI, chạy model, xem lịch sử
/audit-logs    admin xem nhật ký thao tác
```

## Storage

Ảnh MRI và Grad-CAM được lưu tại root project:

```text
storage/
├── mri/
└── gradcam/
```

Database chỉ lưu đường dẫn file, không lưu ảnh binary.

File MRI/Grad-CAM được đánh dấu hết hạn sau 24 giờ. Có thể xóa file hết hạn bằng endpoint:

```text
POST /api/v1/predictions/cleanup-expired-files
```

Record lịch sử trong database vẫn được giữ lại.

## Ghi chú bảo mật

- Không lưu password thô.
- JWT dùng để xác thực API.
- Role hiện có:
  - `admin`
  - `doctor`
- Admin quản lý tài khoản và xem audit log.
- Doctor tạo bệnh nhân, upload MRI và xem lịch sử dự đoán.

## Lệnh chạy local không dùng Docker

Cài dependency:

```bash
pip install -r requirement.txt
```

Chạy backend từ folder `backend`:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Lưu ý: local cần PostgreSQL đang chạy và `DATABASE_URL` trỏ đúng database.
