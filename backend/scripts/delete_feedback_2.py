"""删除乱码反馈记录 id=2"""
import sqlite3

DB_PATH = r"d:\BattleFish\MiroFish\backend\instance\sales_twin.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 删除 feedback_record id=2
cur.execute("DELETE FROM feedback_record WHERE id = 2")
print(f"删除 feedback_record: {cur.rowcount} 条")

# 删除关联的 state_change_log（如果有 feedback_record_id 字段）
try:
    cur.execute("DELETE FROM state_change_log WHERE feedback_record_id = 2")
    print(f"删除关联 state_change_log: {cur.rowcount} 条")
except sqlite3.OperationalError as e:
    print(f"state_change_log 无 feedback_record_id 字段: {e}")

conn.commit()

# 验证
cur.execute("SELECT id, substr(feedback_text, 1, 60) FROM feedback_record")
print("\n剩余 feedback_record:")
for r in cur.fetchall():
    print(f"  id={r[0]} text={repr(r[1])}")

conn.close()
