"""迁移脚本: 为 members 表添加 last_check_time 字段"""
import os
import sqlite3
from config import DATABASE_URL, BASE_DIR


def get_sqlite_path():
    if not DATABASE_URL.startswith("sqlite:///"):
        raise RuntimeError(f"当前不是 SQLite 数据库: {DATABASE_URL}")
    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    if not os.path.isabs(db_path):
        db_path = os.path.join(BASE_DIR, db_path)
    return os.path.abspath(db_path)


def column_exists(conn, table_name, column_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def main():
    db_path = get_sqlite_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"数据库文件不存在: {db_path}")
    print(f"数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        if not column_exists(conn, "members", "last_check_time"):
            conn.execute("ALTER TABLE members ADD COLUMN last_check_time DATETIME")
            conn.commit()
            print("已添加字段: members.last_check_time")
        else:
            print("字段已存在: members.last_check_time")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
