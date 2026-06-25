-- ============================================================
-- Brain Tumor MRI Classification System
-- Seed data
-- ============================================================
-- Mục đích:
-- - Thêm dữ liệu mẫu ban đầu cho đồ án/demo.
-- - Không lưu password thô trong database.
--
-- Chạy sau schema.sql:
-- psql -U admin -d mydatabase -f backend/database/schema.sql
-- psql -U admin -d mydatabase -f backend/database/seed.sql
--
-- QUAN TRỌNG:
-- Trước khi chạy file này, hãy thay giá trị __REPLACE_WITH_ARGON2_HASH__
-- bằng hash được tạo từ backend.
--
-- Ví dụ tạo hash sau khi đã cài dependency:
-- python -c "from app.core.security import get_password_hash; print(get_password_hash('Admin@123456'))"
--
-- Tài khoản demo dự kiến:
-- username: admin
-- email   : admin@example.com
-- password: Admin@123456
-- ============================================================


-- ============================================================
-- 1. ADMIN DEFAULT USER
-- ============================================================
-- Dùng UUID cố định để dữ liệu demo có thể tham chiếu ổn định.

INSERT INTO users (
    id,
    username,
    email,
    password_hash,
    full_name,
    role,
    is_active
)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'admin',
    'admin@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$/b+X0tp7zzlnzFlrbQ3BWA$I0s0Z/GyvAinOUikunu9UmHxk+v+YIYeTnTaLT/CTJE',
    'System Administrator',
    'admin',
    TRUE
)
ON CONFLICT (username) DO UPDATE
SET
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    role = EXCLUDED.role,
    is_active = TRUE;


-- ============================================================
-- 2. DEMO DOCTOR USER
-- ============================================================
-- Nếu không cần bác sĩ demo, có thể xóa block này.
-- Nhớ thay password_hash trước khi chạy nếu muốn đăng nhập bằng tài khoản này.
--
-- username: doctor01
-- email   : doctor01@example.com
-- password: Doctor@123456

INSERT INTO users (
    id,
    username,
    email,
    password_hash,
    full_name,
    role,
    is_active
)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    'doctor01',
    'doctor01@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$F+K8915r7d1bS6nVGqO09g$P67zKaEtzpQeMskL/qzaPK018yD3lsErTPd2Pe3355c',
    'Demo Doctor',
    'doctor',
    TRUE
)
ON CONFLICT (username) DO UPDATE
SET
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    role = EXCLUDED.role,
    is_active = TRUE;


-- ============================================================
-- 3. DEMO PATIENTS
-- ============================================================
-- Dữ liệu bệnh nhân mẫu để frontend có dữ liệu hiển thị ngay khi demo.

INSERT INTO patients (
    id,
    patient_code,
    full_name,
    date_of_birth,
    sex,
    phone_number,
    notes,
    created_by
)
VALUES
(
    '10000000-0000-0000-0000-000000000001',
    'BN001',
    'Nguyen Van A',
    '1990-01-15',
    'male',
    '0900000001',
    'Bệnh nhân demo cho đồ án.',
    '00000000-0000-0000-0000-000000000002'
),
(
    '10000000-0000-0000-0000-000000000002',
    'BN002',
    'Tran Thi B',
    '1988-06-20',
    'female',
    '0900000002',
    'Bệnh nhân demo thứ hai.',
    '00000000-0000-0000-0000-000000000002'
)
ON CONFLICT (patient_code) DO UPDATE
SET
    full_name = EXCLUDED.full_name,
    date_of_birth = EXCLUDED.date_of_birth,
    sex = EXCLUDED.sex,
    phone_number = EXCLUDED.phone_number,
    notes = EXCLUDED.notes;


-- Seed chèn mã bệnh nhân tường minh nên cần đưa sequence tới số kế tiếp.
SELECT setval(
    'patient_code_seq',
    GREATEST(
        COALESCE(
            (
                SELECT MAX(SUBSTRING(patient_code FROM 3)::BIGINT)
                FROM patients
                WHERE patient_code ~ '^BN[0-9]{1,18}$'
            ),
            0
        ) + 1,
        1
    ),
    FALSE
);


-- ============================================================
-- DONE
-- ============================================================
-- Sau khi chạy seed.sql, database có:
-- - 1 admin mẫu
-- - 1 bác sĩ mẫu
-- - 2 bệnh nhân mẫu
--
