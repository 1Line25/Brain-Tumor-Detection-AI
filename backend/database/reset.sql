-- ============================================================
-- Brain Tumor MRI Classification System
-- Reset database schema
-- ============================================================
-- Mục đích:
-- - Xóa sạch bảng/type/function cũ để chạy lại schema.sql và seed.sql.
-- - Hữu ích khi test/demo nhiều lần và muốn quay về trạng thái ban đầu.
--
-- Cách chạy:
-- psql -U admin -d mydatabase -f backend/database/reset.sql
-- psql -U admin -d mydatabase -f backend/database/schema.sql
-- psql -U admin -d mydatabase -f backend/database/seed.sql
--
-- CẢNH BÁO:
-- File này sẽ xóa toàn bộ dữ liệu trong các bảng của hệ thống.
-- Chỉ dùng cho môi trường học tập/demo/test.
-- ============================================================


-- ============================================================
-- 1. DROP TABLES
-- ============================================================
-- Xóa bảng theo thứ tự ngược quan hệ khóa ngoại.

DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS predictions CASCADE;
DROP TABLE IF EXISTS patients CASCADE;
DROP TABLE IF EXISTS login_throttles CASCADE;
DROP TABLE IF EXISTS users CASCADE;


-- ============================================================
-- 2. DROP ENUM TYPES
-- ============================================================
-- Xóa các enum type sau khi bảng đã bị xóa.

DROP TYPE IF EXISTS audit_action CASCADE;
DROP TYPE IF EXISTS prediction_status CASCADE;
DROP TYPE IF EXISTS prediction_review_status CASCADE;
DROP TYPE IF EXISTS tumor_class CASCADE;
DROP TYPE IF EXISTS patient_sex CASCADE;
DROP TYPE IF EXISTS user_role CASCADE;


-- ============================================================
-- 3. DROP FUNCTIONS
-- ============================================================
-- Xóa function trigger updated_at.

DROP FUNCTION IF EXISTS set_updated_at() CASCADE;


-- ============================================================
-- DONE
-- ============================================================
-- Database đã được reset.
-- Hãy chạy tiếp schema.sql rồi seed.sql để có lại bảng và dữ liệu mẫu.
