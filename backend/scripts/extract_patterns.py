"""Pattern 提取批处理脚本 — 定期汇总推荐日志与结果，生成 LearningPattern
用法: python scripts/extract_patterns.py
"""
import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models.database import AIRecommendationLog, AIRecommendationOutcome, LearningPattern


def extract_patterns():
    """从历史推荐中提取成功/失败模式"""
    app = create_app()
    with app.app_context():
        # 获取所有有 outcome 的推荐日志
        logs = AIRecommendationLog.query.all()
        if not logs:
            print("无推荐日志，跳过")
            return

        # 按因子区间分组统计
        # 简化实现：按 stage + is_exploration 分组
        groups = {}
        for log in logs:
            outcome = AIRecommendationOutcome.query.filter_by(recommendation_id=log.id).first()
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

        # 生成 pattern
        for key, stats in groups.items():
            if stats['total'] < 3:
                continue  # 样本不足

            success_rate = stats['stage_advanced'] / stats['total']
            stage, mode = key.rsplit('_', 1)

            pattern_type = 'success_pattern' if success_rate >= 0.5 else 'failure_pattern'
            name = f"{stage}阶段_{mode == 'explore' and '探索' or '利用'}策略"

            trigger_conditions = json.dumps({
                'stage': stage,
                'is_exploration': mode == 'explore'
            })

            # 检查是否已存在同名 pattern
            existing = LearningPattern.query.filter_by(name=name).first()
            if existing:
                existing.evidence_count = stats['total']
                existing.success_rate = success_rate
                existing.updated_at = datetime.utcnow()
                print(f"更新模式: {name} (样本={stats['total']}, 胜率={success_rate:.1%})")
            else:
                p = LearningPattern(
                    pattern_type=pattern_type,
                    name=name,
                    trigger_conditions_json=trigger_conditions,
                    recommended_play=f"在{stage}阶段采用{mode == 'explore' and '探索性' or '利用性'}策略",
                    evidence_count=stats['total'],
                    success_rate=success_rate,
                    status='candidate'
                )
                db.session.add(p)
                print(f"新增模式: {name} (样本={stats['total']}, 胜率={success_rate:.1%})")

        db.session.commit()
        print("Pattern 提取完成")


if __name__ == '__main__':
    extract_patterns()
