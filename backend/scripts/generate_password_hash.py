from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path


# Cho phép chạy script từ root project:
# python backend/scripts/generate_password_hash.py
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import get_password_hash  # noqa: E402


def main() -> None:
    """
    Sinh password hash đúng chuẩn backend đang dùng.

    Mục đích:
    - Không lưu password thô trong seed.sql.
    - Tạo hash để dán vào cột users.password_hash.
    """

    parser = argparse.ArgumentParser(
        description="Generate password hash for database seed.sql"
    )
    parser.add_argument(
        "--password",
        help="Password cần hash. Nếu bỏ trống, script sẽ hỏi qua terminal.",
    )

    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")

    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    print(get_password_hash(password))


if __name__ == "__main__":
    main()
