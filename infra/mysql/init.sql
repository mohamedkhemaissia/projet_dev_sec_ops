CREATE DATABASE IF NOT EXISTS user_service_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS course_service_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON user_service_db.* TO 'tms_user'@'%';
GRANT ALL PRIVILEGES ON course_service_db.* TO 'tms_user'@'%';

FLUSH PRIVILEGES;