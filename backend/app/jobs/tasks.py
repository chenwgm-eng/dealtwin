"""DealTwin Agent 后台定时任务

三个核心任务：
1. daily_project_health_scan — 每日商机盲区静默扫描
2. weekly_strategy_evaluation — 每周量化策略复盘与模式提取
3. daily_customer_news_fetch — 每日客户网络情报拉取

注意：job 函数脱离 HTTP 请求生命周期，所有 db 操作必须包裹在 app.app_context() 中。
所有任务执行记录持久化到 AgentJobRun 表，盲区扫描结果持久化到 BlindSpotReport 表，
客户情报快照持久化到 CustomerIntelSnapshot 表。
"""
import json
import logging
from datetime import datetime

from app.extensions import scheduler

logger = logging.getLogger("dealtwin_cron")


def _get_app():
    """获取 scheduler 绑定的 Flask app 实例"""
    # Flask-APScheduler 在 init_app 时将 app 保存为 scheduler.app
    return scheduler.app


def _start_job_run(job_id: str):
    """创建 AgentJobRun 记录，返回 (run_record, started_at) 供结束时更新"""
    from app import db
    from app.models.database import AgentJobRun
    started_at = datetime.utcnow()
    run = AgentJobRun(
        job_id=job_id,
        started_at=started_at,
        status='failed',  # 默认失败，成功时更新
    )
    db.session.add(run)
    db.session.commit()
    return run


def _finish_job_run(run, status: str, summary: str = '', items_processed: int = 0,
                    items_succeeded: int = 0, error_message: str = ''):
    """更新 AgentJobRun 记录为完成状态"""
    from app import db
    try:
        run.finished_at = datetime.utcnow()
        run.status = status
        run.summary = summary
        run.items_processed = items_processed
        run.items_succeeded = items_succeeded
        run.error_message = error_message
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"[Cron] 更新 AgentJobRun 失败: {e}")


# =====================================================================
# Job 1: 每日商机盲区扫描
# =====================================================================
def daily_project_health_scan():
    """每日凌晨 2 点：扫描所有活跃项目的盲区

    遍历非 closed_won/closed_lost 阶段的项目，调用 BlindSpotDetector.scan_project
    生成最新盲区报告并持久化到 BlindSpotReport（scan_source='cron'）。
    """
    logger.info("[Cron] 开启每日商机盲区扫描...")

    from app.models.database import Project
    from app.services.blind_spot_detector import BlindSpotDetector

    app = _get_app()
    with app.app_context():
        run = _start_job_run('Daily_Health_Scan')
        try:
            active_projects = Project.query.filter(
                ~Project.sales_stage.in_(['closed_won', 'closed_lost'])
            ).all()
            detector = BlindSpotDetector()
            scanned = 0
            total_findings = 0
            failed = 0
            for proj in active_projects:
                try:
                    result = detector.scan_project(proj.id, scan_source='cron')
                    scanned += 1
                    findings = result.get('findings', []) if isinstance(result, dict) else []
                    total_findings += len(findings)
                    if findings:
                        logger.info(
                            f"[Cron] 项目 {proj.name}(id={proj.id}) 发现 {len(findings)} 条盲区"
                        )
                except Exception as e:
                    failed += 1
                    logger.error(f"[Cron] 项目 {proj.id} 扫描失败: {e}")

            status = 'success' if failed == 0 else ('partial' if scanned > 0 else 'failed')
            summary = f"扫描 {scanned} 个项目，发现 {total_findings} 条盲区"
            if failed:
                summary += f"，{failed} 个项目失败"
            _finish_job_run(run, status, summary,
                            items_processed=len(active_projects), items_succeeded=scanned)
            logger.info(f"[Cron] 盲区扫描完成：{summary}")
        except Exception as e:
            _finish_job_run(run, 'failed', error_message=str(e))
            logger.error(f"[Cron] 每日盲区扫描任务异常: {e}", exc_info=True)


# =====================================================================
# Job 2: 每周量化策略复盘与模式提取
# =====================================================================
def weekly_strategy_evaluation():
    """每周五 23:59：从历史推荐结果中提取成功/失败模式

    复用 backend/scripts/extract_patterns.py 的核心逻辑：按 stage + is_exploration
    分组统计，生成 LearningPattern 候选项供总监在「智能进化」页面审批。
    """
    logger.info("[Cron] 开启每周量化策略提取...")

    from app import db
    from app.models.database import (
        AIRecommendationLog, AIRecommendationOutcome, LearningPattern,
    )

    app = _get_app()
    with app.app_context():
        run = _start_job_run('Weekly_Learning_Eval')
        try:
            logs = AIRecommendationLog.query.all()
            if not logs:
                _finish_job_run(run, 'success', summary='无推荐日志，跳过模式提取')
                logger.info("[Cron] 无推荐日志，跳过模式提取")
                return

            # 按 stage + is_exploration 分组统计
            groups = {}
            for log in logs:
                outcome = AIRecommendationOutcome.query.filter_by(
                    recommendation_id=log.id
                ).first()
                if not outcome or outcome.is_adopted is None:
                    continue

                key = f"{log.stage_at_generation or 'unknown'}_{'explore' if log.is_exploration else 'exploit'}"
                if key not in groups:
                    groups[key] = {'total': 0, 'adopted': 0, 'executed': 0, 'stage_advanced': 0}
                groups[key]['total'] += 1
                if outcome.is_adopted:
                    groups[key]['adopted'] += 1
                if outcome.is_executed:
                    groups[key]['executed'] += 1
                if outcome.triggered_stage_advance:
                    groups[key]['stage_advanced'] += 1

            created = 0
            updated = 0
            for key, stats in groups.items():
                if stats['total'] < 3:
                    continue  # 样本不足

                success_rate = stats['stage_advanced'] / stats['total']
                stage, mode = key.rsplit('_', 1)
                pattern_type = 'success_pattern' if success_rate >= 0.5 else 'failure_pattern'
                name = f"{stage}阶段_{mode == 'explore' and '探索' or '利用'}策略"
                trigger_conditions = json.dumps({
                    'stage': stage,
                    'is_exploration': mode == 'explore',
                }, ensure_ascii=False)

                existing = LearningPattern.query.filter_by(name=name).first()
                if existing:
                    existing.evidence_count = stats['total']
                    existing.success_rate = success_rate
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    p = LearningPattern(
                        pattern_type=pattern_type,
                        name=name,
                        trigger_conditions_json=trigger_conditions,
                        recommended_play=f"在{stage}阶段采用{mode == 'explore' and '探索性' or '利用性'}策略",
                        evidence_count=stats['total'],
                        success_rate=success_rate,
                        status='candidate',
                    )
                    db.session.add(p)
                    created += 1

            db.session.commit()
            summary = f"处理 {len(logs)} 条推荐日志，新增 {created} 条候选模式，更新 {updated} 条"
            _finish_job_run(run, 'success', summary,
                            items_processed=len(logs), items_succeeded=created + updated)
            logger.info(f"[Cron] 模式提取完成：{summary}")
        except Exception as e:
            db.session.rollback()
            _finish_job_run(run, 'failed', error_message=str(e))
            logger.error(f"[Cron] 每周策略复盘失败: {e}", exc_info=True)


# =====================================================================
# Job 3: 每日客户网络情报拉取
# =====================================================================
def daily_customer_news_fetch():
    """每日凌晨 4 点：拉取活跃项目关联客户的最新网络情报

    遍历活跃项目关联的 customer，调用 WebResearcher.research_company 刷新调研报告。
    - 若项目无 customer_id 则跳过（使用 customer_name 作为 fallback）
    - 每个客户最多 1 次调用，避免重复
    - 调用失败不影响其他客户
    - 报告持久化到 CustomerIntelSnapshot（source='cron'），可追溯历史变化
    """
    logger.info("[Cron] 开启每日客户情报拉取...")

    from app import db
    from app.models.database import Project, Customer, CustomerIntelSnapshot
    from app.services.web_researcher import WebResearcher

    app = _get_app()
    with app.app_context():
        run = _start_job_run('Daily_News_Fetch')
        try:
            active_projects = Project.query.filter(
                ~Project.sales_stage.in_(['closed_won', 'closed_lost'])
            ).all()

            # 收集去重后的客户（按 customer_id 优先，否则按 customer_name）
            seen_ids = set()
            seen_names = set()
            pending = []  # [(customer_id_or_none, name, industry)]
            for proj in active_projects:
                if proj.customer_id and proj.customer_id not in seen_ids:
                    seen_ids.add(proj.customer_id)
                    cust = Customer.query.get(proj.customer_id)
                    if cust:
                        pending.append((cust.id, cust.name, cust.industry or proj.industry or ''))
                elif proj.customer_name and proj.customer_name not in seen_names:
                    seen_names.add(proj.customer_name)
                    pending.append((None, proj.customer_name, proj.industry or ''))

            if not pending:
                _finish_job_run(run, 'success', summary='无活跃客户，跳过情报拉取')
                logger.info("[Cron] 无活跃客户，跳过情报拉取")
                return

            researcher = WebResearcher()
            success = 0
            failed = 0
            for customer_id, name, industry in pending:
                try:
                    result = researcher.research_company(
                        company_name=name,
                        industry=industry or '',
                        extra_keywords='最新动态 新闻',
                    )
                    if result.get('success'):
                        # 持久化情报快照
                        snapshot = CustomerIntelSnapshot(
                            customer_id=customer_id,
                            customer_name=name,
                            industry=industry or None,
                            report_text=result.get('report', '')[:8000],
                            source='cron',
                        )
                        db.session.add(snapshot)
                        success += 1
                    else:
                        failed += 1
                        logger.warning(
                            f"[Cron] 客户 {name} 情报拉取失败: {result.get('error', '未知错误')}"
                        )
                except Exception as e:
                    failed += 1
                    logger.error(f"[Cron] 客户 {name} 情报拉取异常: {e}")

            db.session.commit()
            status = 'success' if failed == 0 else ('partial' if success > 0 else 'failed')
            summary = f"拉取 {len(pending)} 个客户情报，成功 {success}，失败 {failed}"
            _finish_job_run(run, status, summary,
                            items_processed=len(pending), items_succeeded=success)
            logger.info(f"[Cron] 情报拉取完成：{summary}")
        except Exception as e:
            db.session.rollback()
            _finish_job_run(run, 'failed', error_message=str(e))
            logger.error(f"[Cron] 每日情报拉取任务异常: {e}", exc_info=True)