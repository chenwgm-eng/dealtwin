"""SalesTwin 系统 API 全面测试脚本 v2 - 修正路径与嵌套"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:5001/api/sales-twin"


def get(path, label):
    print(f"\n{'='*60}")
    print(f"[{label}] GET {path}")
    print('='*60)
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"  HTTP ERROR {e.code}: {e.read()[:200]}")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def post(path, payload, label):
    print(f"\n{'='*60}")
    print(f"[{label}] POST {path}")
    print('='*60)
    try:
        req = urllib.request.Request(
            f"{BASE}{path}",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"  HTTP ERROR {e.code}: {e.read()[:300]}")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main():
    # 1. 项目列表
    d = get("/projects?page=1&per_page=5", "项目列表分页")
    if d:
        print(f"  分页: total={d.get('total')} page={d.get('page')} per_page={d.get('per_page')} has_next={d.get('has_next')}")
        print(f"  items: {len(d.get('items', []))} | projects(兼容): {len(d.get('projects', []))}")
        for p in d.get('items', []):
            print(f"    #{p['id']} {p['name']} | stage={p['sales_stage']} | cust={p.get('customer_name')}")

    # 2. 项目详情（嵌套在 'project' 字段下）
    d = get("/projects/2", "项目2 详情")
    if d:
        p = d.get('project', d)
        print(f"  name={p.get('name')}")
        print(f"  sales_stage={p.get('sales_stage')}")
        print(f"  customer_name={p.get('customer_name')}")
        print(f"  industry={p.get('industry')!r}")
        print(f"  budget={p.get('budget')} certainty={p.get('budget_certainty')}")
        print(f"  graph_project_id={p.get('graph_project_id')}")
        print(f"  value_proposition 长度={len(p.get('value_proposition') or '')}")
        print(f"  business_pain_points 长度={len(p.get('business_pain_points') or '')}")
        print(f"  competitive_analysis 长度={len(p.get('competitive_analysis') or '')}")

    # 3. 干系人
    d = get("/projects/2/stakeholders", "项目2 干系人")
    if d is not None:
        arr = d if isinstance(d, list) else d.get('stakeholders', d.get('items', []))
        print(f"  干系人总数: {len(arr)}")
        for s in arr[:15]:
            print(f"    #{s.get('id')} {s.get('name')} | pos={s.get('position')} | role={s.get('buyer_role')} | level={s.get('level')} | sup={s.get('support_level')} dec={s.get('decision_power')} urg={s.get('urgency')} | reports_to={s.get('reports_to_id')}")

    # 4. 任务
    d = get("/projects/2/tasks", "项目2 任务")
    if d is not None:
        arr = d if isinstance(d, list) else d.get('tasks', d.get('items', []))
        print(f"  任务总数: {len(arr)}")
        for t in arr[:15]:
            src = t.get('source_action') or {}
            src_str = f"src={src.get('action_type')}/{src.get('priority_score')}" if isinstance(src, dict) else f"src={src}"
            print(f"    #{t.get('id')} [{t.get('status')}] pri={t.get('priority')} | {t.get('title','')[:50]} | due={t.get('due_date')} | {src_str}")

    # 5. 阶段交付物
    d = get("/projects/2/stage-deliverables", "项目2 阶段交付物")
    if d:
        print(f"  当前阶段: {d.get('current_stage')}")
        print(f"  完成率: {d.get('completion_rate')}%")
        print(f"  核心目标: {d.get('core_objective')}")
        for grp in d.get('deliverables', []):
            print(f"  [{grp.get('key')}] {grp.get('name')}:")
            for it in grp.get('items', []):
                flag = []
                if it.get('is_completed'): flag.append('手动完成')
                if it.get('auto_status') == 'completed': flag.append('自动完成')
                if it.get('is_optional'): flag.append('可选')
                attach_count = len(it.get('attachments') or [])
                if attach_count: flag.append(f'{attach_count}附件')
                print(f"    - {it.get('key')}: {it.get('name')} | effective={it.get('effective_completed')} | auto_reason={(it.get('auto_reason') or '-')[:50]} | {'/'.join(flag) or '未完成'}")

    # 6. 反馈记录列表（正确路径：feedback-records）
    d = get("/projects/2/feedback-records", "项目2 反馈记录")
    if d is not None:
        arr = d if isinstance(d, list) else d.get('feedback_records', d.get('items', d.get('records', [])))
        print(f"  反馈总数: {len(arr)}")
        for f in arr[:5]:
            print(f"    #{f.get('id')} changes={f.get('total_changes')} | summary={(f.get('parse_summary') or '')[:50]} | text={(f.get('feedback_text') or '')[:60]}")

    # 7. 状态变更日志
    d = get("/projects/2/state-logs", "项目2 状态变更日志")
    if d is not None:
        arr = d if isinstance(d, list) else d.get('logs', d.get('items', []))
        print(f"  日志总数: {len(arr)}")
        for l in arr[:5]:
            print(f"    #{l.get('id')} [{l.get('change_source')}] {l.get('entity_type')}/{l.get('attribute')} | {l.get('old_value')} -> {l.get('new_value')} | {(l.get('reasoning') or '')[:40]}")

    # 8. 客户列表
    d = get("/customers", "客户列表")
    if d is not None:
        arr = d if isinstance(d, list) else d.get('customers', d.get('items', []))
        print(f"  客户总数: {len(arr)}")
        for c in arr[:10]:
            print(f"    #{c.get('id')} {c.get('name')} | industry={c.get('industry')} | core_products={c.get('core_products')}")

    # 9. 客户详情（嵌套在 'customer' 下）
    d = get("/customers/1", "客户1 详情")
    if d:
        c = d.get('customer', d)
        print(f"  name={c.get('name')}")
        print(f"  industry={c.get('industry')}")
        print(f"  unified_credit_code={c.get('unified_credit_code')}")
        contacts = c.get('contacts') or []
        print(f"  联系人数: {len(contacts)}")
        for ct in contacts[:8]:
            print(f"    - #{ct.get('id')} {ct.get('name')} | pos={ct.get('position')} | dep={ct.get('department')} | interaction_status={ct.get('interaction_status')}")
        children = c.get('children') or []
        print(f"  子公司数: {len(children)}")

    # 10. 客户组织图谱
    d = get("/customers/1/org-graph", "客户1 组织图谱")
    if d:
        print(f"  顶层字段: {list(d.keys())}")
        nodes = d.get('nodes') or []
        edges = d.get('edges') or []
        print(f"  节点数: {len(nodes)} | 边数: {len(edges)}")
        for n in nodes[:5]:
            print(f"    {n}")

    # 11. Dashboard
    d = get("/dashboard", "Dashboard")
    if d:
        print(f"  顶层字段: {list(d.keys())}")
        m = d.get('metrics', {})
        print(f"  metrics: {json.dumps(m, ensure_ascii=False)[:500] if m else 'empty'}")
        ins = d.get('llm_insights')
        print(f"  llm_insights 类型: {type(ins).__name__}")
        if ins:
            print(f"  llm_insights 长度: {len(str(ins))}")
            print(f"  llm_insights 预览: {str(ins)[:500]}")
        ai = d.get('attention_items')
        print(f"  attention_items 数: {len(ai) if isinstance(ai, list) else ai}")

    # 12. 阶段检查（POST 方法）
    d = post("/projects/2/stage-check", {"stage": "define"}, "项目2 阶段检查(POST, stage=define)")
    if d:
        print(f"  顶层字段: {list(d.keys())}")
        print(f"  ready: {d.get('ready')}")
        print(f"  completion_rate: {d.get('completion_rate')}")
        blockers = d.get('blockers', [])
        print(f"  阻塞项数: {len(blockers)}")
        for b in blockers[:5]:
            print(f"    - {b}")

    # 13. 阶段时间线
    d = get("/projects/2/stage-timeline", "项目2 阶段时间线")
    if d:
        print(f"  顶层字段: {list(d.keys())}")
        stages = d.get('stages') or d.get('timeline') or []
        print(f"  阶段数: {len(stages)}")
        for s in stages[:8]:
            print(f"    - {s}")

    # 14. 会议计划
    d = get("/projects/2/meeting-plans", "项目2 会议计划")
    if d is not None:
        arr = d if isinstance(d, list) else d.get('meeting_plans', d.get('items', []))
        print(f"  会议总数: {len(arr)}")
        for m in arr[:5]:
            print(f"    #{m.get('id')} [{m.get('status')}] | stakeholder={m.get('stakeholder_id')} | type={m.get('visit_type')} | purpose={(m.get('meeting_purpose') or '')[:40]}")

    # 15. 推荐 suggestions
    d = get("/projects/2/suggestions", "项目2 推荐 suggestions")
    if d is not None:
        arr = d if isinstance(d, list) else d.get('suggestions', d.get('items', []))
        print(f"  推荐数: {len(arr)}")
        for s in arr[:5]:
            print(f"    #{s.get('id')} [{s.get('type') or s.get('suggestion_type')}] | {str(s)[:100]}")

    # 16. 干系人 contacts 关联
    d = get("/projects/2/stakeholders/contacts", "项目2 干系人-联系人关联")
    if d is not None:
        arr = d if isinstance(d, list) else d.get('contacts', d.get('items', d.get('links', [])))
        print(f"  关联数: {len(arr)}")
        for l in arr[:5]:
            print(f"    {l}")

    # 17. 项目图谱信息
    d = get("/projects/2/graph", "项目2 图谱信息")
    if d:
        print(f"  顶层字段: {list(d.keys())}")
        print(f"  graph_id: {d.get('graph_id') or d.get('id')}")
        print(f"  graph_project_id: {d.get('graph_project_id')}")

    # 18. 关系列表
    d = get("/projects/2/relationships", "项目2 干系人关系")
    if d is not None:
        arr = d if isinstance(d, list) else d.get('relationships', d.get('items', []))
        print(f"  关系数: {len(arr)}")
        for r in arr[:5]:
            print(f"    {r}")

    # 19. 胜率
    d = get("/projects/2/win-rate", "项目2 胜率")
    if d:
        print(f"  顶层字段: {list(d.keys())}")
        print(f"  win_rate: {d.get('win_rate')}")
        print(f"  factors: {d.get('factors')}")


if __name__ == '__main__':
    main()
