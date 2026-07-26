"""查数据库表结构并清理乱码反馈"""
import sqlite3
import os

DB_PATH = r"d:\BattleFish\MiroFish\backend\instance\sales_twin.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 列出所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("=== 所有表 ===")
for t in tables:
    print(f"  {t}")

# 找反馈相关表
print("\n=== 反馈相关表 ===")
for t in tables:
    if 'feedback' in t.lower() or 'record' in t.lower():
        cur.execute(f"PRAGMA table_info({t})")
        cols = cur.fetchall()
        print(f"\n  表 {t}:")
        for c in cols:
            print(f"    {c[1]} ({c[2]})")

# 查 feedback_record 表内容（如果是这个名字）
for t in tables:
    if 'feedback' in t.lower():
        print(f"\n=== 表 {t} 内容 ===")
        cur.execute(f"SELECT * FROM {t}")
        rows = cur.fetchall()
        # 获取列名
        col_names = [d[0] for d in cur.description]
        print(f"列名: {col_names}")
        for r in rows:
            # 找 feedback_text 列
            text_idx = None
            for i, cn in enumerate(col_names):
                if 'text' in cn.lower():
                    text_idx = i
                    break
            if text_idx is not None:
                print(f"  id={r[0]} text={repr(str(r[text_idx])[:80])}")
            else:
                print(f"  id={r[0]}")

conn.close()
