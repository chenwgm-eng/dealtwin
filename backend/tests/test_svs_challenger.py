"""SVS 里程碑决策 / 销售模式 / 关闭复盘 / Challenger 商业指导与检查清单 / 干系人社交风格 接口测试"""

import pytest

from app import db
from app.models.database import (
    MilestoneDecision, ChallengerTeaching, LearningPattern, FeedbackRecord,
)


def _create_project(client, **kwargs):
    """通过 API 创建项目，返回项目ID"""
    payload = {'name': '测试项目'}
    payload.update(kwargs)
    resp = client.post('/api/sales-twin/projects', json=payload)
    assert resp.status_code == 200
    return resp.get_json()['project']['id']


# ===== 里程碑决策 =====
class TestMilestones:
    def test_get_returns_five_placeholders(self, client):
        """GET 返回 5 条 pending 占位（含中文标签）"""
        pid = _create_project(client)
        resp = client.get(f'/api/sales-twin/projects/{pid}/milestones')
        assert resp.status_code == 200
        milestones = resp.get_json()['milestones']
        assert len(milestones) == 5
        assert [m['milestone'] for m in milestones] == ['om10', 'om20', 'om30', 'om40', 'om70']
        for m in milestones:
            assert m['decision'] == 'pending'
            assert m['id'] is None
        labels = {m['milestone']: m['milestone_label'] for m in milestones}
        assert labels['om10'] == 'Bid/No-Go 决策'
        assert labels['om70'] == '赢单/丢单'

    def test_put_upsert_create_then_update(self, client):
        """PUT upsert：先创建后更新，每里程碑仅一条记录"""
        pid = _create_project(client)
        resp = client.put(f'/api/sales-twin/projects/{pid}/milestones/om10', json={
            'decision': 'go', 'strategic_fit': 4, 'revenue_scale': 5,
            'rationale': '战略契合', 'decided_by': '销售总监'
        })
        assert resp.status_code == 200
        md = resp.get_json()['milestone']
        assert md['decision'] == 'go'
        assert md['strategic_fit'] == 4
        assert md['revenue_scale'] == 5
        assert md['decided_at'] is not None
        md_id = md['id']

        # 再次 PUT 同里程碑：更新而非新建
        resp = client.put(f'/api/sales-twin/projects/{pid}/milestones/om10', json={
            'decision': 'no_go', 'rationale': '竞争过于激烈'
        })
        assert resp.status_code == 200
        md2 = resp.get_json()['milestone']
        assert md2['id'] == md_id
        assert md2['decision'] == 'no_go'
        # 未提交的评分字段保持原值
        assert md2['strategic_fit'] == 4
        assert MilestoneDecision.query.filter_by(project_id=pid, milestone='om10').count() == 1

        # GET 全量：om10 为 no_go，其余仍 pending 占位
        resp = client.get(f'/api/sales-twin/projects/{pid}/milestones')
        milestones = resp.get_json()['milestones']
        assert milestones[0]['decision'] == 'no_go'
        assert all(m['decision'] == 'pending' for m in milestones[1:])

    def test_decided_at_written_on_go(self, client):
        """decision=go 时 decided_at 自动写入；回到 pending 时清空"""
        pid = _create_project(client)
        resp = client.put(f'/api/sales-twin/projects/{pid}/milestones/om20', json={'decision': 'go'})
        assert resp.get_json()['milestone']['decided_at'] is not None
        resp = client.put(f'/api/sales-twin/projects/{pid}/milestones/om20', json={'decision': 'pending'})
        assert resp.get_json()['milestone']['decided_at'] is None

    def test_invalid_milestone_returns_400(self, client):
        pid = _create_project(client)
        resp = client.put(f'/api/sales-twin/projects/{pid}/milestones/om99', json={'decision': 'go'})
        assert resp.status_code == 400

    def test_invalid_decision_returns_400(self, client):
        pid = _create_project(client)
        resp = client.put(f'/api/sales-twin/projects/{pid}/milestones/om10', json={'decision': 'maybe'})
        assert resp.status_code == 400

    def test_invalid_score_returns_400(self, client):
        pid = _create_project(client)
        for bad_score in (0, 6, 'abc'):
            resp = client.put(f'/api/sales-twin/projects/{pid}/milestones/om10', json={
                'decision': 'go', 'strategic_fit': bad_score
            })
            assert resp.status_code == 400


# ===== 销售模式 =====
class TestSalesMode:
    def test_put_valid_sales_mode(self, client):
        pid = _create_project(client)
        resp = client.put(f'/api/sales-twin/projects/{pid}/sales-mode', json={
            'sales_mode': 'value_solution_selling'
        })
        assert resp.status_code == 200
        assert resp.get_json()['project']['sales_mode'] == 'value_solution_selling'

        # null 清除
        resp = client.put(f'/api/sales-twin/projects/{pid}/sales-mode', json={'sales_mode': None})
        assert resp.status_code == 200
        assert resp.get_json()['project']['sales_mode'] is None

    def test_put_invalid_sales_mode(self, client):
        pid = _create_project(client)
        resp = client.put(f'/api/sales-twin/projects/{pid}/sales-mode', json={'sales_mode': 'bad_mode'})
        assert resp.status_code == 400

    def test_project_put_sales_mode(self, client):
        """项目通用 PUT 也支持 sales_mode 枚举校验"""
        pid = _create_project(client)
        resp = client.put(f'/api/sales-twin/projects/{pid}', json={'sales_mode': 'inside_sales'})
        assert resp.status_code == 200
        assert resp.get_json()['project']['sales_mode'] == 'inside_sales'
        resp = client.put(f'/api/sales-twin/projects/{pid}', json={'sales_mode': 'bad_mode'})
        assert resp.status_code == 400


# ===== 关闭复盘 =====
class TestCloseReview:
    def test_non_final_stage_rejected(self, client):
        """非终态（suspect）项目拒绝填写关闭复盘"""
        pid = _create_project(client)
        resp = client.put(f'/api/sales-twin/projects/{pid}/close-review', json={
            'close_reason_category': 'price'
        })
        assert resp.status_code == 400

    def test_closed_lost_creates_failure_pattern(self, client):
        """closed_lost 项目复盘成功，沉淀 failure_pattern 学习模式"""
        pid = _create_project(client)
        client.put(f'/api/sales-twin/projects/{pid}', json={'sales_stage': 'closed_lost'})
        resp = client.put(f'/api/sales-twin/projects/{pid}/close-review', json={
            'close_reason_category': 'price',
            'close_reason_detail': '报价高于竞争对手',
            'lessons_learned': '应更早进行价值量化沟通'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['project']['close_reason_category'] == 'price'
        assert data['project']['close_reason_detail'] == '报价高于竞争对手'
        assert data['project']['lessons_learned'] == '应更早进行价值量化沟通'
        pattern = data['pattern']
        assert pattern['pattern_type'] == 'failure_pattern'
        assert pattern['name'] == 'failure_pattern-price'
        assert pattern['status'] == 'candidate'
        assert pattern['evidence_count'] == 1
        # 数据库中确实写入
        assert LearningPattern.query.filter_by(name='failure_pattern-price').first() is not None

    def test_closed_won_creates_success_pattern(self, client):
        """closed_won 项目沉淀 success_pattern"""
        pid = _create_project(client)
        client.put(f'/api/sales-twin/projects/{pid}', json={'sales_stage': 'closed_won'})
        resp = client.put(f'/api/sales-twin/projects/{pid}/close-review', json={
            'close_reason_category': 'relationship',
            'lessons_learned': '高层关系是关键'
        })
        assert resp.status_code == 200
        assert resp.get_json()['pattern']['pattern_type'] == 'success_pattern'

    def test_duplicate_category_accumulates_evidence(self, client):
        """同 category 重复提交时 evidence_count 累加并更新 recommended_play"""
        pid = _create_project(client)
        client.put(f'/api/sales-twin/projects/{pid}', json={'sales_stage': 'closed_lost'})
        client.put(f'/api/sales-twin/projects/{pid}/close-review', json={
            'close_reason_category': 'competition', 'lessons_learned': '第一次教训'
        })
        resp = client.put(f'/api/sales-twin/projects/{pid}/close-review', json={
            'close_reason_category': 'competition', 'lessons_learned': '第二次教训'
        })
        assert resp.status_code == 200
        pattern = resp.get_json()['pattern']
        assert pattern['evidence_count'] == 2
        assert pattern['recommended_play'] == '第二次教训'
        assert LearningPattern.query.filter_by(name='failure_pattern-competition').count() == 1

    def test_invalid_category_returns_400(self, client):
        pid = _create_project(client)
        client.put(f'/api/sales-twin/projects/{pid}', json={'sales_stage': 'closed_lost'})
        resp = client.put(f'/api/sales-twin/projects/{pid}/close-review', json={
            'close_reason_category': 'bad_category'
        })
        assert resp.status_code == 400


# ===== Challenger 检查清单 =====
class TestChallengerChecklist:
    EXPECTED_KEYS = {
        'procurement_verified', 'stakeholder_alignment',
        'commercial_insight', 'powerful_ask', 'verifiable_action',
    }

    def test_structure(self, client):
        """返回 5 项、key 齐全、字段结构完整"""
        pid = _create_project(client)
        resp = client.get(f'/api/sales-twin/projects/{pid}/challenger-checklist')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['items']) == 5
        assert {item['key'] for item in data['items']} == self.EXPECTED_KEYS
        for item in data['items']:
            assert isinstance(item['label'], str) and item['label']
            assert isinstance(item['passed'], bool)
            assert 'detail' in item
            assert 'suggestion' in item
        # 空项目全部不通过
        assert data['passed_count'] == 0

    def test_procurement_verified_passes_with_feedback(self, client):
        """录入拜访反馈后，采购进展验证项通过"""
        pid = _create_project(client)
        db.session.add(FeedbackRecord(project_id=pid, feedback_text='客户反馈：方案基本认可'))
        db.session.commit()
        resp = client.get(f'/api/sales-twin/projects/{pid}/challenger-checklist')
        items = {i['key']: i for i in resp.get_json()['items']}
        assert items['procurement_verified']['passed'] is True
        assert resp.get_json()['passed_count'] == 1


# ===== Challenger 商业指导话术 =====
FAKE_TEACHING_CONTENT = {
    'warmer': '热身话术',
    'reframe': '您以为问题是成本，真正的问题是流程',
    'rational_drowning': '每年因流程低效损失约300万',
    'emotional_impact': '想象一下年底审计时的窘境',
    'new_way': '以数据驱动的全新流程',
    'our_solution': '我方平台正好支撑这一新方法',
    'call_to_action': '建议下周安排技术对接',
    'powerful_ask': {'why': '验证价值', 'when': '本周内', 'who': '技术总监', 'what': '安排POC试点'},
    'validation_factors': ['客户主动索要方案', '客户介绍决策人', '客户确认预算'],
    'tailoring_note': '对方为推动型，直奔结果',
}


@pytest.fixture
def mock_llm(monkeypatch):
    """mock 商业指导生成器的 LLM 调用，返回固定内容"""
    from app.services.challenger_teaching_generator import ChallengerTeachingGenerator
    monkeypatch.setattr(
        ChallengerTeachingGenerator, '_call_llm',
        lambda self, prompt: dict(FAKE_TEACHING_CONTENT)
    )


class TestChallengerTeachings:
    def test_post_generate_success(self, client, mock_llm):
        """mock LLM 后 POST 生成成功（201），name 自动生成"""
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={})
        assert resp.status_code == 201
        teaching = resp.get_json()['teaching']
        assert teaching['status'] == 'generated'
        assert teaching['name'].startswith('商业指导-')
        assert teaching['project_id'] == pid
        content = teaching['teaching_content']
        assert content['reframe'] == '您以为问题是成本，真正的问题是流程'
        assert content['powerful_ask']['what'] == '安排POC试点'
        assert content['validation_factors'] == ['客户主动索要方案', '客户介绍决策人', '客户确认预算']

    def test_post_with_stakeholder_and_name(self, client, mock_llm):
        """指定目标干系人与名称"""
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/stakeholders', json={
            'name': '李四', 'social_style': 'analytical'
        })
        sid = resp.get_json()['stakeholder']['id']
        resp = client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={
            'stakeholder_id': sid, 'name': '李四专属话术'
        })
        assert resp.status_code == 201
        teaching = resp.get_json()['teaching']
        assert teaching['name'] == '李四专属话术'
        assert teaching['stakeholder_id'] == sid
        assert teaching['stakeholder_name'] == '李四'

    def test_post_llm_failure_returns_502(self, client, monkeypatch):
        """LLM 不可用时返回 502"""
        from app.services.challenger_teaching_generator import ChallengerTeachingGenerator

        def _raise(self, prompt):
            raise RuntimeError('LLM服务不可用：连接超时')

        monkeypatch.setattr(ChallengerTeachingGenerator, '_call_llm', _raise)
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={})
        assert resp.status_code == 502
        assert 'LLM' in resp.get_json()['error']
        # 失败不落库
        assert ChallengerTeaching.query.filter_by(project_id=pid).count() == 0

    def test_get_list_and_detail(self, client, mock_llm):
        """GET 列表（时间倒序）与详情"""
        pid = _create_project(client)
        client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={'name': '第一份'})
        resp = client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={'name': '第二份'})
        tid = resp.get_json()['teaching']['id']

        resp = client.get(f'/api/sales-twin/projects/{pid}/challenger-teachings')
        assert resp.status_code == 200
        teachings = resp.get_json()['teachings']
        assert len(teachings) == 2
        assert teachings[0]['name'] == '第二份'  # 最新的在前

        resp = client.get(f'/api/sales-twin/challenger-teachings/{tid}')
        assert resp.status_code == 200
        assert resp.get_json()['teaching']['name'] == '第二份'

    def test_put_update(self, client, mock_llm):
        """PUT 更新 name 与 teaching_content 内字段（合并式）"""
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={})
        tid = resp.get_json()['teaching']['id']

        resp = client.put(f'/api/sales-twin/challenger-teachings/{tid}', json={
            'name': '改名后',
            'teaching_content': {'reframe': '改后的重构观点'}
        })
        assert resp.status_code == 200
        teaching = resp.get_json()['teaching']
        assert teaching['name'] == '改名后'
        assert teaching['teaching_content']['reframe'] == '改后的重构观点'
        # 未提交的字段保持原值
        assert teaching['teaching_content']['warmer'] == '热身话术'

    def test_delete(self, client, mock_llm):
        """DELETE 返回 204，删除后详情 404"""
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={})
        tid = resp.get_json()['teaching']['id']
        resp = client.delete(f'/api/sales-twin/challenger-teachings/{tid}')
        assert resp.status_code == 204
        resp = client.get(f'/api/sales-twin/challenger-teachings/{tid}')
        assert resp.status_code == 404


# ===== 干系人社交风格 =====
class TestStakeholderSocialStyle:
    def test_post_valid_social_style(self, client):
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/stakeholders', json={
            'name': '王五', 'social_style': 'expressive'
        })
        assert resp.status_code == 200
        assert resp.get_json()['stakeholder']['social_style'] == 'expressive'

    def test_post_invalid_social_style(self, client):
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/stakeholders', json={
            'name': '王五', 'social_style': 'unknown_style'
        })
        assert resp.status_code == 400

    def test_put_valid_social_style(self, client):
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/stakeholders', json={'name': '赵六'})
        sid = resp.get_json()['stakeholder']['id']
        resp = client.put(f'/api/sales-twin/stakeholders/{sid}', json={'social_style': 'amiable'})
        assert resp.status_code == 200
        assert resp.get_json()['stakeholder']['social_style'] == 'amiable'

    def test_put_invalid_social_style(self, client):
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/stakeholders', json={'name': '赵六'})
        sid = resp.get_json()['stakeholder']['id']
        resp = client.put(f'/api/sales-twin/stakeholders/{sid}', json={'social_style': 'unknown_style'})
        assert resp.status_code == 400


# ===== 代码审查修复回归 =====
class TestReviewFixes:
    def test_put_project_sales_mode_null_clears(self, client):
        """通用项目 PUT 传 JSON null 清除 sales_mode（不再误判 400）"""
        pid = _create_project(client)
        client.put(f'/api/sales-twin/projects/{pid}', json={'sales_mode': 'inside_sales'})
        resp = client.put(f'/api/sales-twin/projects/{pid}', json={'sales_mode': None})
        assert resp.status_code == 200
        assert resp.get_json()['project']['sales_mode'] is None

    def test_put_stakeholder_social_style_null_clears(self, client):
        """干系人 PUT 传 JSON null 清除 social_style（不再误判 400）"""
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/stakeholders', json={
            'name': '钱七', 'social_style': 'driver'
        })
        sid = resp.get_json()['stakeholder']['id']
        resp = client.put(f'/api/sales-twin/stakeholders/{sid}', json={'social_style': None})
        assert resp.status_code == 200
        assert resp.get_json()['stakeholder']['social_style'] is None

    def test_close_review_partial_submit_keeps_fields(self, client):
        """关闭复盘部分提交（仅改 category）不清空已有 detail/lessons"""
        pid = _create_project(client)
        client.put(f'/api/sales-twin/projects/{pid}', json={'sales_stage': 'closed_lost'})
        client.put(f'/api/sales-twin/projects/{pid}/close-review', json={
            'close_reason_category': 'price',
            'close_reason_detail': '报价偏高',
            'lessons_learned': '应先做价值量化'
        })
        resp = client.put(f'/api/sales-twin/projects/{pid}/close-review', json={
            'close_reason_category': 'competition'
        })
        assert resp.status_code == 200
        project = resp.get_json()['project']
        assert project['close_reason_category'] == 'competition'
        assert project['close_reason_detail'] == '报价偏高'
        assert project['lessons_learned'] == '应先做价值量化'

    def test_close_review_writes_state_change_log(self, client):
        """关闭复盘写入 StateChangeLog（审计链完整）"""
        from app.models.database import StateChangeLog
        pid = _create_project(client)
        client.put(f'/api/sales-twin/projects/{pid}', json={'sales_stage': 'closed_won'})
        client.put(f'/api/sales-twin/projects/{pid}/close-review', json={
            'close_reason_category': 'relationship'
        })
        log = StateChangeLog.query.filter_by(
            project_id=pid, attribute_name='close_reason_category'
        ).first()
        assert log is not None
        assert log.new_value == 'relationship'
        assert log.change_source == 'manual_edit'

    def test_post_teaching_cross_project_stakeholder_404(self, client, mock_llm):
        """绑定其他项目的干系人生成话术 → 404（归属校验）"""
        pid_a = _create_project(client)
        pid_b = _create_project(client, name='另一个项目')
        resp = client.post(f'/api/sales-twin/projects/{pid_b}/stakeholders', json={'name': '外部人'})
        sid_b = resp.get_json()['stakeholder']['id']
        resp = client.post(f'/api/sales-twin/projects/{pid_a}/challenger-teachings', json={
            'stakeholder_id': sid_b
        })
        assert resp.status_code == 404
        assert ChallengerTeaching.query.filter_by(project_id=pid_a).count() == 0

    def test_checklist_verifiable_action_with_stakeholder_ids(self, client):
        """仅通过 stakeholder_ids JSON 数组关联干系人的待办，可验证行动项应通过"""
        from app.models.database import OpportunityTask
        pid = _create_project(client)
        db.session.add(OpportunityTask(
            project_id=pid, task_type='follow_up', title='推进POC',
            status='in_progress', stakeholder_ids='[1, 2]'
        ))
        db.session.commit()
        resp = client.get(f'/api/sales-twin/projects/{pid}/challenger-checklist')
        items = {i['key']: i for i in resp.get_json()['items']}
        assert items['verifiable_action']['passed'] is True

    def test_put_teaching_content_non_dict_400(self, client, mock_llm):
        """teaching_content 传非对象 → 400（不再静默忽略）"""
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={})
        tid = resp.get_json()['teaching']['id']
        resp = client.put(f'/api/sales-twin/challenger-teachings/{tid}', json={
            'teaching_content': 'not a dict'
        })
        assert resp.status_code == 400

    def test_put_teaching_content_normalized(self, client, mock_llm):
        """teaching_content 更新后结构被归一化（powerful_ask 覆盖为字符串会被重置为四要素结构）"""
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={})
        tid = resp.get_json()['teaching']['id']
        resp = client.put(f'/api/sales-twin/challenger-teachings/{tid}', json={
            'teaching_content': {'powerful_ask': '随便一个字符串', 'unknown_field': '脏字段'}
        })
        assert resp.status_code == 200
        content = resp.get_json()['teaching']['teaching_content']
        assert isinstance(content['powerful_ask'], dict)
        assert 'unknown_field' not in content

    def test_delete_stakeholder_nulls_teaching_ref(self, client, mock_llm):
        """删除干系人后，其名下话术 stakeholder_id 置空（保留为通用话术）"""
        pid = _create_project(client)
        resp = client.post(f'/api/sales-twin/projects/{pid}/stakeholders', json={'name': '孙八'})
        sid = resp.get_json()['stakeholder']['id']
        resp = client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={
            'stakeholder_id': sid
        })
        tid = resp.get_json()['teaching']['id']
        client.delete(f'/api/sales-twin/stakeholders/{sid}')
        teaching = ChallengerTeaching.query.get(tid)
        assert teaching is not None
        assert teaching.stakeholder_id is None

    def test_delete_project_cascades_svs_records(self, client, mock_llm):
        """删除项目时级联删除里程碑决策与商业指导（不留孤儿行）"""
        pid = _create_project(client)
        client.put(f'/api/sales-twin/projects/{pid}/milestones/om10', json={'decision': 'go'})
        client.post(f'/api/sales-twin/projects/{pid}/challenger-teachings', json={})
        client.delete(f'/api/sales-twin/projects/{pid}')
        assert MilestoneDecision.query.filter_by(project_id=pid).count() == 0
        assert ChallengerTeaching.query.filter_by(project_id=pid).count() == 0
