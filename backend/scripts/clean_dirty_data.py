"""清理脏数据：删除项目#1 和反馈记录#2"""
import json
import urllib.request
import urllib.error
import sqlite3
import os

BASE = "http://127.0.0.1:5001/api/sales-twin"
DB_PATH = r"d:\BattleFish\MiroFish\backend\instance\sales_twin.db"

# 1. 删除项目 #1（乱码空壳项目）
print("=== 删除项目 #1 ===")
req = urllib.request.Request(f"{BASE}/projects/1", method='DELETE')
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode('utf-8'))
        print(f"  删除成功: {result}")
except urllib.error.HTTPError as e:
    print(f"  HTTP ERROR {e.code}: {e.read()[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. 验证项目列表
print("\n=== 验证项目列表 ===")
with urllib.request.urlopen(f"{BASE}/projects?page=1&per_page=20", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))
    for p in d.get('items', []):
        print(f"  #{p['id']} name={repr(p.get('name'))} stage={p.get('sales_stage')}")

# 3. 直接 SQL 删除反馈记录 #2（乱码）
print("\n=== 删除反馈记录 #2 ===")
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 先查看
    cur.execute("SELECT id, project_id, substr(feedback_text, 1, 80) FROM feedback_records WHERE id = 2")
    row = cur.fetchone()
    if row:
        print(f"  删除前: id={row[0]} project_id={row[1]} text={repr(row[2])}")
        # 删除关联的 state_change_logs（如果有 feedback_id 字段）
        try:
            cur.execute("DELETE FROM state_change_logs WHERE feedback_id = 2")
            print(f"  删除关联 state_change_logs: {cur.rowcount} 条")
        except sqlite3.OperationalError:
            pass  # 字段可能不存在
        # 删除反馈记录
        cur.execute("DELETE FROM feedback_records WHERE id = 2")
        print(f"  删除 feedback_records: {cur.rowcount} 条")
        conn.commit()
    else:
        print("  反馈记录 #2 不存在")
    conn.close()
else:
    print(f"  数据库文件不存在: {DB_PATH}")

# 4. 验证项目2 的反馈
print("\n=== 验证项目2 的反馈 ===")
with urllib.request.urlopen(f"{BASE}/projects/2/feedback-records", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))
    arr = d if isinstance(d, list) else d.get('feedback_records', d.get('records', []))
    for f in arr:
        print(f"  #{f['id']} text={repr((f.get('feedback_text') or '')[:60])}")
