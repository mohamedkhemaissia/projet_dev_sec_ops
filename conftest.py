"""Shared environment values used only by the automated test suite."""

import os


TEST_ENVIRONMENT = {
    "SECRET_KEY": "test-only-secret-key-at-least-32-characters",
    "JWT_SECRET_KEY": "test-only-jwt-key-at-least-32-characters",
    "MYSQL_ROOT_PASSWORD": "test-only-root-password",
    "MYSQL_PASSWORD": "test-only-mysql-password",
    "DEFAULT_ADMIN_PASSWORD": "TestOnlyAdminPassword123!",
    "FRONTEND_SECRET_KEY": "test-only-frontend-key-at-least-32-characters",
}

for variable_name, test_value in TEST_ENVIRONMENT.items():
    os.environ.setdefault(variable_name, test_value)
