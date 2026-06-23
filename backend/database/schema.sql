-- ============================================================
-- Brain Tumor MRI Classification System
-- Manual PostgreSQL schema
-- ============================================================
-- Mục đích:
-- - Tạo database schema bằng SQL tay, dễ đọc/dễ giải thích cho đồ án.
-- - Không dùng Alembic migration.
-- - Backend FastAPI/SQLAlchemy sẽ làm việc với các bảng được tạo ở đây.
--
-- Cách chạy ví dụ:
-- psql -U admin -d mydatabase -f backend/database/schema.sql
-- ============================================================


-- Cần extension này để PostgreSQL tự sinh UUID bằng gen_random_uuid().
-- Dù backend cũng có thể tự sinh UUID, để default ở DB giúp insert SQL tay dễ hơn.
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ============================================================
-- 1. ENUM TYPES
-- ============================================================
-- Dùng DO block để tránh lỗi nếu enum đã tồn tại.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('admin', 'doctor');
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'patient_sex') THEN
        CREATE TYPE patient_sex AS ENUM ('male', 'female', 'other', 'unknown');
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tumor_class') THEN
        -- Thứ tự label phải khớp class_indices lúc train model:
        -- glioma_tumor=0, meningioma_tumor=1, no_tumor=2, pituitary_tumor=3
        CREATE TYPE tumor_class AS ENUM (
            'glioma_tumor',
            'meningioma_tumor',
            'no_tumor',
            'pituitary_tumor'
        );
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'prediction_status') THEN
        CREATE TYPE prediction_status AS ENUM ('success', 'failed');
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audit_action') THEN
        CREATE TYPE audit_action AS ENUM (
            'login',
            'logout',
            'create_user',
            'update_user',
            'deactivate_user',
            'create_patient',
            'update_patient',
            'create_prediction',
            'delete_expired_files'
        );
    END IF;
END $$;


-- ============================================================
-- 2. UPDATED_AT TRIGGER FUNCTION
-- ============================================================
-- Hàm này tự cập nhật updated_at mỗi khi UPDATE một record.
-- Nhờ vậy dù cập nhật bằng backend hay SQL tay, updated_at vẫn đúng.

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 3. USERS TABLE
-- ============================================================
-- Lưu tài khoản admin và bác sĩ.
-- Không xóa user vật lý để giữ lịch sử prediction/audit.

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) NOT NULL,

    role user_role NOT NULL DEFAULT 'doctor',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_users_username_min_length
        CHECK (char_length(username) >= 3),

    CONSTRAINT ck_users_full_name_min_length
        CHECK (char_length(full_name) >= 2)
);


CREATE INDEX IF NOT EXISTS ix_users_role_is_active
ON users (role, is_active);


DROP TRIGGER IF EXISTS trg_users_set_updated_at ON users;
CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- 4. PATIENTS TABLE
-- ============================================================
-- Lưu hồ sơ bệnh nhân.
-- Tách riêng khỏi predictions để tránh lặp thông tin bệnh nhân nhiều lần.

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    patient_code VARCHAR(40) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    date_of_birth DATE NULL,
    sex patient_sex NOT NULL DEFAULT 'unknown',
    phone_number VARCHAR(20) NULL,
    notes TEXT NULL,

    created_by UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_patients_created_by_users
        FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_patients_patient_code_min_length
        CHECK (char_length(patient_code) >= 3),

    CONSTRAINT ck_patients_full_name_min_length
        CHECK (char_length(full_name) >= 2)
);


CREATE INDEX IF NOT EXISTS ix_patients_created_by
ON patients (created_by);


CREATE INDEX IF NOT EXISTS ix_patients_created_by_created_at
ON patients (created_by, created_at);


CREATE INDEX IF NOT EXISTS ix_patients_patient_code
ON patients (patient_code);


DROP TRIGGER IF EXISTS trg_patients_set_updated_at ON patients;
CREATE TRIGGER trg_patients_set_updated_at
BEFORE UPDATE ON patients
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- 5. PREDICTIONS TABLE
-- ============================================================
-- Lưu lịch sử upload MRI và kết quả model.
-- DB chỉ lưu đường dẫn file, không lưu ảnh binary để nhẹ database.

CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    patient_id UUID NOT NULL,
    doctor_id UUID NOT NULL,

    mri_image_path VARCHAR(500) NOT NULL,
    gradcam_image_path VARCHAR(500) NULL,

    predicted_class tumor_class NULL,
    confidence DOUBLE PRECISION NULL,
    probabilities JSONB NULL,

    status prediction_status NOT NULL DEFAULT 'success',
    error_message TEXT NULL,

    -- Sau thời điểm này, worker/API cleanup sẽ xóa file MRI và Grad-CAM.
    -- Record trong DB vẫn giữ lại để xem lịch sử.
    expires_at TIMESTAMPTZ NOT NULL,
    files_deleted BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_predictions_patient_id_patients
        FOREIGN KEY (patient_id)
        REFERENCES patients(id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_predictions_doctor_id_users
        FOREIGN KEY (doctor_id)
        REFERENCES users(id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_predictions_confidence_range
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),

    CONSTRAINT ck_predictions_failed_has_error
        CHECK (status != 'failed' OR error_message IS NOT NULL)
);


CREATE INDEX IF NOT EXISTS ix_predictions_patient_id
ON predictions (patient_id);


CREATE INDEX IF NOT EXISTS ix_predictions_doctor_id
ON predictions (doctor_id);


CREATE INDEX IF NOT EXISTS ix_predictions_status
ON predictions (status);


CREATE INDEX IF NOT EXISTS ix_predictions_expires_at
ON predictions (expires_at);


CREATE INDEX IF NOT EXISTS ix_predictions_files_deleted
ON predictions (files_deleted);


CREATE INDEX IF NOT EXISTS ix_predictions_patient_created_at
ON predictions (patient_id, created_at);


CREATE INDEX IF NOT EXISTS ix_predictions_doctor_created_at
ON predictions (doctor_id, created_at);


-- Index phục vụ cleanup: tìm record hết hạn mà chưa xóa file.
CREATE INDEX IF NOT EXISTS ix_predictions_cleanup
ON predictions (files_deleted, expires_at);


DROP TRIGGER IF EXISTS trg_predictions_set_updated_at ON predictions;
CREATE TRIGGER trg_predictions_set_updated_at
BEFORE UPDATE ON predictions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- 6. AUDIT_LOGS TABLE
-- ============================================================
-- Lưu nhật ký thao tác hệ thống.
-- actor_id có thể NULL nếu hành động do hệ thống tự chạy, ví dụ cleanup file.

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    actor_id UUID NULL,
    action audit_action NOT NULL,

    entity_type VARCHAR(50) NULL,
    entity_id VARCHAR(80) NULL,

    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(300) NULL,

    -- JSONB linh hoạt cho metadata như predicted_class/confidence/patient_code.
    -- Không lưu password/token vào field này.
    metadata_json JSONB NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_audit_logs_actor_id_users
        FOREIGN KEY (actor_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);


CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id
ON audit_logs (actor_id);


CREATE INDEX IF NOT EXISTS ix_audit_logs_action
ON audit_logs (action);


CREATE INDEX IF NOT EXISTS ix_audit_logs_entity_type
ON audit_logs (entity_type);


CREATE INDEX IF NOT EXISTS ix_audit_logs_entity_id
ON audit_logs (entity_id);


CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_created_at
ON audit_logs (actor_id, created_at);


CREATE INDEX IF NOT EXISTS ix_audit_logs_action_created_at
ON audit_logs (action, created_at);


CREATE INDEX IF NOT EXISTS ix_audit_logs_entity
ON audit_logs (entity_type, entity_id);


DROP TRIGGER IF EXISTS trg_audit_logs_set_updated_at ON audit_logs;
CREATE TRIGGER trg_audit_logs_set_updated_at
BEFORE UPDATE ON audit_logs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- DONE
-- ============================================================
-- Sau khi chạy file này, database đã sẵn sàng cho backend FastAPI.
