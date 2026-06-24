# Backend — Brain Tumor MRI Classification System

Backend dùng FastAPI để quản lý tài khoản, bệnh nhân, upload ảnh MRI, chạy model EfficientNetB0 `best_tl_model.h5`, tạo Grad-CAM và lưu lịch sử dự đoán vào PostgreSQL.

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
best_tl_model.h5
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
top_conv
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

Khi chạy `docker compose up`, service `database-init` tự động chạy
`schema.sql` và `seed.sql` trước khi backend khởi động. Không cần chạy lệnh
khởi tạo database thủ công.

Nếu muốn reset database rồi tạo lại từ đầu:

```bash
docker compose down -v
docker compose up --build
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

Phạm vi dữ liệu:

- Admin có thể xem và quản lý toàn bộ hồ sơ.
- Chỉ admin có thể xem danh sách đầy đủ tài khoản trong hệ thống.
- Doctor chỉ có thể xem, cập nhật và tạo dự đoán cho bệnh nhân do chính tài
  khoản đó tạo.
- Doctor chỉ xem được các lần dự đoán do chính mình thực hiện.
- Khi doctor yêu cầu ID ngoài phạm vi, API trả `404` để không tiết lộ tài
  nguyên đó có tồn tại hay không.

Giới hạn đăng nhập:

- Sau 5 lần sai cho cùng tài khoản trong 15 phút, tài khoản bị khóa tạm 15
  phút.
- Sau 20 lần sai từ cùng IP trong 15 phút, IP bị khóa tạm 15 phút.
- API trả `429 Too Many Requests` và header `Retry-After` khi đang bị khóa.
- Bộ đếm được lưu trong PostgreSQL nên không mất khi backend restart.

Audit log ghi các sự kiện:

- đăng nhập thành công, sai thông tin, bị rate limit và đăng xuất;
- tạo, cập nhật, khóa, mở khóa và reset mật khẩu tài khoản;
- tạo, xem chi tiết và cập nhật bệnh nhân;
- dự đoán thành công/thất bại, xem chi tiết kết quả và dọn file hết hạn.

Mỗi log HTTP lưu actor nếu xác định được, IP, user-agent, entity liên quan và
metadata đã loại bỏ password/token.

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

## Chạy test backend

Test dùng SQLite in-memory nên không cần tạo PostgreSQL test riêng:

```bash
pip install -r backend/requirements-dev.txt
pytest backend/tests -q
```

## Cấu hình log

Mặc định backend ghi log tiếng Việt ra stdout để xem bằng Docker:

```bash
docker compose logs -f backend
```

Có thể cấu hình trong `.env`:

```text
LOG_LEVEL=INFO
LOG_TO_FILE=false
```

Chỉ bật `LOG_TO_FILE=true` khi thật sự cần lưu thêm `logs/app.log`, vì Docker
đã thu thập stdout và việc ghi hai nơi sẽ tạo thêm disk I/O.
