/**
 * 销售阶段统一枚举（全系统唯一来源）
 * 基于五阶段销售模型与里程碑定义
 *
 * 阶段映射（旧版 → 新版）：
 * - discovery    → suspect      OM10 Bid/No-Go
 * - qualification→ identity     OM20 Go/No-Go
 * - proposal     → define       OM30 策略评审 / OM40 投标批准
 * - negotiation  → confirm      OM40 → OM70 赢单/丢单
 * - closed_won   → closed_won   OM70 Won（保留）
 * - closed_lost  → closed_lost  OM70 Lost（保留）
 */
export const SALES_STAGES = [
  { value: 'suspect', label: '线索', desc: '客户编排、商机识别，OM10 Bid/No-Go 决策' },
  { value: 'identity', label: '商机确认', desc: '干系人识别、需求确认，OM20 Go/No-Go 决策' },
  { value: 'define', label: '方案定义', desc: '方案设计、投标策略，OM30 策略评审 / OM40 投标批准' },
  { value: 'confirm', label: '商务确认', desc: '商务谈判、合同签署，OM70 赢单/丢单' },
  { value: 'closed_won', label: '赢单', desc: 'OM70 Won，已签约' },
  { value: 'closed_lost', label: '丢单', desc: 'OM70 Lost，已关闭' },
]

// value → label 映射
export const STAGE_LABELS = SALES_STAGES.reduce((acc, s) => {
  acc[s.value] = s.label
  return acc
}, {})

// value → desc 映射
export const STAGE_DESCRIPTIONS = SALES_STAGES.reduce((acc, s) => {
  acc[s.value] = s.desc
  return acc
}, {})

// 活跃阶段（非终态）
export const ACTIVE_STAGES = SALES_STAGES.filter(s => !s.value.startsWith('closed_'))

// 终态阶段
export const CLOSED_STAGES = SALES_STAGES.filter(s => s.value.startsWith('closed_'))

// 旧版 → 新版阶段映射（用于前端兼容旧数据展示与数据迁移参考）
// 注意：后端迁移脚本 backend/scripts/migrate_sales_stage_to_five.py 已包含独立映射表
// 此常量保留供前端在遇到历史数据时做兼容展示，或未来需要在前端做数据校正时使用
export const LEGACY_STAGE_MAPPING = {
  discovery: 'suspect',
  qualification: 'identity',
  proposal: 'define',
  negotiation: 'confirm',
  closed_won: 'closed_won',
  closed_lost: 'closed_lost',
}
