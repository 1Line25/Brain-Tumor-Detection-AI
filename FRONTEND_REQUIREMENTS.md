# Frontend Requirements — Brain Tumor MRI Classification System

File này mô tả toàn bộ những phần frontend cần có để làm việc tốt với backend và database hiện tại.

Mục tiêu:

- Frontend đơn giản, dễ demo, dùng HTML/CSS/JavaScript thuần.
- Gọi đúng API backend FastAPI.
- Tránh request thừa làm nặng backend/database.
- Hiển thị đầy đủ luồng: đăng nhập, quản lý bệnh nhân, upload MRI, xem kết quả, xem lịch sử.

## 1. Công nghệ frontend

Frontend dùng:

```text
HTML
CSS
JavaScript thuần
Fetch API
```

Không bắt buộc dùng framework như React/Vue vì đây là đồ án cơ bản.

Backend API chạy mặc định tại:

```text
http://localhost:8000/api/v1
```

## 2. Cấu trúc frontend đề xuất

```text
frontend/
├── index.html              # Trang đăng nhập
├── dashboard.html          # Trang tổng quan sau đăng nhập
├── patients.html           # Danh sách/tạo/cập nhật bệnh nhân
├── prediction.html         # Upload MRI và xem kết quả dự đoán
├── history.html            # Lịch sử dự đoán
├── users.html              # Admin quản lý tài khoản
├── audit-logs.html         # Admin xem nhật ký hệ thống
├── css/
│   └── style.css
└── js/
    ├── api.js              # Hàm gọi API chung
    ├── auth.js             # Đăng nhập, logout, current user
    ├── patients.js
    ├── predictions.js
    ├── users.js
    └── audit-logs.js
```

Ghi chú: đây là cấu trúc đề xuất cho giai đoạn sau, chưa bắt buộc phải tạo ngay.

## 3. Quy tắc gọi API để tối ưu backend/database

### 3.1 Luôn phân trang danh sách

Các màn hình danh sách phải dùng:

```text
page
page_size
```

Không gọi API lấy toàn bộ dữ liệu một lần.

Khuyến nghị:

```text
page_size = 10 hoặc 20
```

Áp dụng cho:

```text
GET /patients
GET /predictions
GET /users
GET /audit-logs
```

### 3.2 Không tự động gọi API liên tục

Tránh gọi API theo kiểu mỗi vài giây refresh một lần nếu không cần.

Chỉ gọi khi:

- user mở trang,
- user bấm tìm kiếm,
- user chuyển trang,
- user tạo/cập nhật dữ liệu thành công.

### 3.3 Tìm kiếm nên có nút Search

Không nên gọi API ngay sau mỗi phím gõ.

Nếu muốn tìm kiếm theo input realtime thì cần debounce khoảng:

```text
300ms - 500ms
```

Nhưng với đồ án cơ bản, nên dùng nút:

```text
Tìm kiếm
```

### 3.4 Không upload ảnh quá lớn

Frontend nên kiểm tra trước khi gửi ảnh:

```text
Định dạng: .jpg, .jpeg, .png
Dung lượng tối đa: 10MB
```

Backend đã kiểm tra lại, nhưng frontend kiểm tra trước giúp demo mượt hơn.

### 3.5 Không lưu ảnh MRI trong localStorage

Không lưu ảnh MRI, Grad-CAM hoặc file binary vào:

```text
localStorage
sessionStorage
```

Chỉ lưu JWT token và thông tin user tối thiểu.

## 4. Auth flow

### 4.1 Đăng nhập

Endpoint:

```text
POST /auth/login
```

Request JSON:

```json
{
  "identifier": "admin",
  "password": "Admin@123456"
}
```

Response:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "username": "admin",
    "role": "admin"
  }
}
```

Frontend cần lưu:

```text
access_token
user.role
user.full_name
```

### 4.2 Gửi token khi gọi API

Mọi API cần đăng nhập phải gửi header:

```text
Authorization: Bearer <access_token>
```

### 4.3 Kiểm tra phiên đăng nhập

Endpoint:

```text
GET /auth/me
```

Dùng khi mở lại trang để biết token còn hợp lệ không.

Nếu backend trả `401`, frontend chuyển về trang login.

## 5. Role frontend

Hệ thống có 2 role:

```text
admin
doctor
```

### Admin được thấy

- Dashboard
- Quản lý user
- Quản lý bệnh nhân
- Upload MRI/dự đoán
- Lịch sử dự đoán
- Audit logs
- Cleanup expired files

### Doctor được thấy

- Dashboard
- Quản lý bệnh nhân
- Upload MRI/dự đoán
- Lịch sử dự đoán

Doctor không nên thấy:

- Users management
- Audit logs
- Cleanup expired files

Backend vẫn kiểm tra quyền, nhưng frontend ẩn menu giúp giao diện rõ hơn.

## 6. Patients UI

### 6.1 Danh sách bệnh nhân

Endpoint:

```text
GET /patients?page=1&page_size=20&keyword=BN001
```

Hiển thị các cột:

```text
Mã bệnh nhân
Họ tên
Ngày sinh
Giới tính
Số điện thoại
Ngày tạo
Hành động
```

Hành động:

- Xem chi tiết
- Cập nhật
- Chọn để dự đoán MRI

### 6.2 Tạo bệnh nhân

Endpoint:

```text
POST /patients
```

Request JSON:

```json
{
  "patient_code": "BN003",
  "full_name": "Le Van C",
  "date_of_birth": "1995-04-10",
  "sex": "male",
  "phone_number": "0900000003",
  "notes": "Bệnh nhân mới."
}
```

Frontend không gửi:

```text
created_by
```

Backend tự lấy từ user đang đăng nhập.

### 6.3 Cập nhật bệnh nhân

Endpoint:

```text
PATCH /patients/{patient_id}
```

Không cho sửa `patient_code` trên giao diện cơ bản.

## 7. Prediction UI

### 7.1 Upload MRI

Endpoint:

```text
POST /predictions
```

Content-Type:

```text
multipart/form-data
```

Form fields:

```text
patient_id: UUID
mri_image: file jpg/png
```

Frontend cần kiểm tra:

```text
patient_id không rỗng
file đã chọn
file là jpg/png
file <= 10MB
```

### 7.2 Hiển thị kết quả

Sau khi upload thành công, hiển thị:

```text
Loại u dự đoán
Độ tin cậy
Xác suất từng class
Ảnh Grad-CAM
Thời điểm ảnh bị xóa
```

Mapping label nên hiển thị thân thiện:

| Label backend | Tên hiển thị |
|---|---|
| `glioma_tumor` | Glioma |
| `meningioma_tumor` | Meningioma |
| `no_tumor` | Không có u |
| `pituitary_tumor` | Pituitary |

### 7.3 Không gọi prediction nhiều lần

Khi user bấm nút dự đoán:

- disable nút submit,
- hiển thị loading,
- chỉ enable lại khi request xong.

Việc này tránh gửi trùng nhiều request, làm nặng model/backend.

## 8. Prediction history UI

Endpoint:

```text
GET /predictions?page=1&page_size=20
```

Filter nên có:

```text
patient_id
doctor_id
predicted_class
prediction_status
```

Hiển thị:

```text
Ngày dự đoán
Bệnh nhân
Bác sĩ
Loại u
Confidence
Trạng thái
Ảnh đã xóa chưa
Chi tiết
```

Nếu `files_deleted = true`, frontend nên hiển thị:

```text
Ảnh MRI/Grad-CAM đã được xóa sau 24 giờ
```

Không báo lỗi giao diện nếu ảnh không còn tồn tại.

## 9. Users UI dành cho admin

Endpoint chính:

```text
GET /users
POST /users
PATCH /users/{user_id}
POST /users/{user_id}/activate
POST /users/{user_id}/deactivate
POST /users/{user_id}/reset-password
```

Frontend cần có:

- danh sách user,
- tạo user,
- khóa/mở khóa,
- reset password.

Không bao giờ hiển thị:

```text
password_hash
```

## 10. Audit logs UI dành cho admin

Endpoint:

```text
GET /audit-logs?page=1&page_size=20
```

Filter:

```text
actor_id
action
entity_type
entity_id
```

Hiển thị:

```text
Thời gian
Người thực hiện
Hành động
Đối tượng
IP
Metadata
```

Audit logs chỉ nên load khi admin mở trang, không auto refresh liên tục.

## 11. Cleanup expired files

Endpoint:

```text
POST /predictions/cleanup-expired-files
```

Chỉ admin được dùng.

Frontend có thể đặt nút:

```text
Xóa ảnh hết hạn
```

Sau khi bấm, hiển thị message backend trả về.

Không nên gọi endpoint này tự động liên tục.

## 12. Xử lý lỗi frontend

Frontend nên xử lý các HTTP status:

| Status | Cách xử lý |
|---|---|
| 400 | Hiển thị lỗi nhập liệu/file |
| 401 | Token hết hạn, quay về login |
| 403 | Không đủ quyền |
| 404 | Không tìm thấy dữ liệu |
| 500 | Lỗi hệ thống, thử lại sau |

Không hiển thị stack trace hoặc lỗi kỹ thuật dài cho người dùng.

## 13. Tối ưu hiển thị ảnh

Khi hiển thị MRI/Grad-CAM:

- dùng kích thước preview vừa phải,
- không render ảnh quá lớn toàn màn hình ngay,
- nếu ảnh đã bị xóa sau 24 giờ thì hiển thị placeholder.

Gợi ý:

```text
Preview: max-width 400px
```

## 14. LocalStorage/sessionStorage

Cho phép lưu:

```text
access_token
user role
user full_name
```

Không lưu:

```text
password
MRI file
Grad-CAM file
patient sensitive data quá nhiều
```

## 15. Thứ tự làm frontend đề xuất

```text
1. Login page
2. API helper js/api.js
3. Dashboard layout/menu theo role
4. Patients page
5. Prediction upload page
6. Prediction history page
7. Users page cho admin
8. Audit logs page cho admin
9. Hoàn thiện CSS và loading/error states
```

## 16. Checklist trước khi demo

- Đăng nhập admin được.
- Đăng nhập doctor được.
- Tạo bệnh nhân mới được.
- Upload MRI và nhận kết quả được.
- Grad-CAM hiển thị được.
- Lịch sử dự đoán có phân trang.
- Doctor không thấy menu admin.
- Admin xem được users và audit logs.
- File quá lớn hoặc sai định dạng bị chặn trước khi gửi.
- Nếu ảnh đã bị xóa, giao diện không bị crash.

## 17. Ghi chú để backend/database nhẹ hơn

- Luôn dùng phân trang.
- Không gọi API lặp liên tục.
- Không upload trùng nhiều lần.
- Không lưu ảnh vào database.
- Không lấy audit logs nếu user không phải admin.
- Không request history quá nhiều bản ghi một lần.
- Không hiển thị full metadata nếu không cần.
