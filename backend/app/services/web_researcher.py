"""
网络调研服务
基于实时联网搜索 + 工商信息抓取 + 公司官网抓取生成目标公司背景调研报告

实时性保证：
- 通过 WebSearchOrchestrator 多 Provider 链式降级实时联网搜索（Tavily → 百度 → 搜狗）
- 通过 BusinessInfoScraper 抓取爱企查工商信息
- 通过 WebsiteScraper 抓取公司官网"关于我们"页面
- LLM 仅用于"基于实时搜索结果生成结构化报告"，不凭空生成
- 所有实时源失败时返回空报告
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from .business_info_scraper import BusinessInfoScraper
from .web_search_providers import SearchResult, WebSearchOrchestrator
from .website_scraper import WebsiteScraper

logger = logging.getLogger(__name__)


class WebResearcher:
    """目标公司背景调研器（基于实时联网搜索）"""

    # 调研报告总长度上限
    MAX_REPORT_LEN = 8000

    def __init__(self, llm_client=None):
        # 延迟初始化 LLM 客户端
        self._llm_client = llm_client

    def _get_llm(self):
        if self._llm_client is None:
            from ..utils.llm_client import LLMClient
            self._llm_client = LLMClient()
        return self._llm_client

    def research_company(self, company_name: str, industry: str = '', extra_keywords: str = '') -> Dict[str, Any]:
        """
        调研目标公司背景信息（基于实时联网搜索 + 工商信息 + 公司官网）

        Args:
            company_name: 客户名称（必填）
            industry: 行业（可选，提升精准度）
            extra_keywords: 额外关键词（可选，如"数字化转型 采购"）

        Returns:
            {
                'company_name': str,
                'success': bool,
                'report': str,           # 调研报告文本（每段附注来源 URL）
                'raw_results': list,     # 原始结构化数据
                'organization': dict,    # 暴露给 API 层自动创建干系人
                'queries': list,         # 调研维度
                'error': str,
                'data_sources': list,    # 数据来源列表，如 ['tavily', 'aiqicha', 'website']
                'search_timestamp': str, # ISO 8601 搜索时间戳
                'is_realtime': bool,     # 是否实时搜索结果
            }
        """
        if not company_name or not company_name.strip():
            return {
                'company_name': company_name,
                'success': False,
                'report': '',
                'raw_results': [],
                'organization': {},
                'queries': [],
                'error': '客户名称为空',
                'data_sources': [],
                'search_timestamp': '',
                'is_realtime': False,
            }

        company_name = company_name.strip()
        search_timestamp = datetime.now().isoformat()
        data_sources: List[str] = []
        is_realtime = False

        try:
            # 调研维度（用于报告展示）
            queries = self._build_research_dimensions(company_name, industry, extra_keywords)

            # 第一步：实时联网搜索
            search_results: List[SearchResult] = []
            try:
                orchestrator = WebSearchOrchestrator()
                search_data = orchestrator.search_with_fallback(
                    f"{company_name} 业务 规模 行业地位", max_results=8
                )
                search_results = search_data.get('results') or []
                providers_used = search_data.get('providers_used') or []
                if search_results:
                    data_sources.extend(providers_used)
                    is_realtime = bool(search_data.get('is_realtime'))
            except Exception as e:
                logger.warning(f"实时联网搜索失败 [{company_name}]: {e}")
                search_results = []

            # 第二步：抓取爱企查工商信息（失败容错，不阻塞）
            business_info: Dict = {}
            try:
                biz_scraper = BusinessInfoScraper()
                business_info = biz_scraper.scrape_aiqicha(company_name) or {}
                if business_info:
                    data_sources.append('aiqicha')
            except Exception as e:
                logger.warning(f"工商信息抓取失败 [{company_name}]: {e}")
                business_info = {}

            # 第三步：抓取公司官网"关于我们"（失败容错，不阻塞）
            about_info: Dict = {}
            try:
                website_scraper = WebsiteScraper()
                about_info = website_scraper.scrape_about_page(company_name) or {}
                if about_info:
                    data_sources.append('website')
            except Exception as e:
                logger.warning(f"公司官网抓取失败 [{company_name}]: {e}")
                about_info = {}

            # 关键判断：所有实时源均无结果时不调用 LLM 凭空生成
            if not search_results and not business_info and not about_info:
                return {
                    'company_name': company_name,
                    'success': False,
                    'report': '',
                    'raw_results': [],
                    'organization': {},
                    'queries': queries,
                    'error': '所有实时源均无结果',
                    'data_sources': [],
                    'search_timestamp': search_timestamp,
                    'is_realtime': False,
                }

            # 第四步：LLM 基于实时搜索结果 + 工商信息 + 官网信息生成结构化调研报告
            llm = self._get_llm()
            prompt = self._build_prompt(
                company_name, industry, extra_keywords,
                search_results=search_results,
                business_info=business_info,
                about_info=about_info,
            )

            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=3500
            )

            if not result or not isinstance(result, dict):
                return {
                    'company_name': company_name,
                    'success': False,
                    'report': '',
                    'raw_results': [],
                    'organization': {},
                    'queries': queries,
                    'error': 'LLM返回格式异常',
                    'data_sources': data_sources,
                    'search_timestamp': search_timestamp,
                    'is_realtime': is_realtime,
                }

            # 把 LLM 结构化结果转成文本报告（每段附注来源 URL）
            report = self._build_report_from_llm(
                result, company_name, industry,
                data_sources=data_sources,
                search_timestamp=search_timestamp,
                is_realtime=is_realtime,
            )

            # raw_results 用结构化数据
            raw_results = self._extract_raw_results(result)

            # 暴露 organization 字段，供 API 层自动创建干系人
            organization = result.get('organization', {})

            return {
                'company_name': company_name,
                'success': True,
                'report': report,
                'raw_results': raw_results,
                'organization': organization,
                'queries': queries,
                'error': '',
                'data_sources': data_sources,
                'search_timestamp': search_timestamp,
                'is_realtime': is_realtime,
            }

        except Exception as e:
            logger.error(f"实时调研公司背景失败 [{company_name}]: {e}")
            return {
                'company_name': company_name,
                'success': False,
                'report': '',
                'raw_results': [],
                'organization': {},
                'queries': [],
                'error': f'调研失败: {str(e)}',
                'data_sources': data_sources,
                'search_timestamp': search_timestamp,
                'is_realtime': is_realtime,
            }

    def _build_research_dimensions(self, company_name: str, industry: str, extra_keywords: str) -> List[str]:
        """构建调研维度（用于报告展示）"""
        dims = [
            f"{company_name} 组织概况与核心职能",
            f"{company_name} 战略方向与数字化举措",
            f"{company_name} 组织架构与关键领导层",
            f"{company_name} 采购/项目动态与预算"
        ]
        if extra_keywords:
            dims.append(f"{company_name} {extra_keywords}")
        return dims[:5]

    def _build_prompt(
        self,
        company_name: str,
        industry: str,
        extra_keywords: str,
        search_results: List[SearchResult],
        business_info: Dict,
        about_info: Dict,
    ) -> str:
        """构建 LLM 调研提示词（基于实时搜索结果，禁止凭空生成）"""
        # 上下文
        context_parts = []
        if industry:
            context_parts.append(f"行业: {industry}")
        if extra_keywords:
            context_parts.append(f"关注重点: {extra_keywords}")
        context = '\n'.join(context_parts) if context_parts else '（无额外上下文）'

        # 实时搜索结果文本（编号列出 title/url/content）
        search_block_lines: List[str] = []
        for idx, r in enumerate(search_results, start=1):
            title = (r.title or '').strip() or '(无标题)'
            url = (r.url or '').strip() or '(无URL)'
            content = (r.content or '').strip() or '(无内容)'
            search_block_lines.append(
                f"[{idx}] 标题: {title}\n    URL: {url}\n    内容: {content}"
            )
        search_block = '\n'.join(search_block_lines) if search_block_lines else '（无实时搜索结果）'

        # 工商信息
        business_block_lines: List[str] = []
        if business_info:
            field_labels = {
                'legal_representative': '法定代表人',
                'registered_capital': '注册资本',
                'establish_date': '成立日期',
                'enterprise_type': '企业类型',
                'business_scope': '经营范围',
                'registered_address': '注册地址',
                'unified_credit_code': '统一社会信用代码',
                'shareholders': '主要股东',
            }
            for field, label in field_labels.items():
                val = business_info.get(field)
                if val:
                    business_block_lines.append(f"- {label}: {val}")
            source_url = business_info.get('source_url')
            if source_url:
                business_block_lines.append(f"- 来源URL: {source_url}")
        business_block = '\n'.join(business_block_lines) if business_block_lines else '（无工商信息）'

        # 官网"关于我们"文本（限制长度避免 LLM 上下文超限）
        about_block_lines: List[str] = []
        if about_info:
            about_text = (about_info.get('about_text') or '').strip()
            if about_text:
                if len(about_text) > 4000:
                    about_text = about_text[:4000] + '...(截断)'
                about_block_lines.append(about_text)
            source_url = about_info.get('source_url')
            if source_url:
                about_block_lines.append(f"来源URL: {source_url}")
        about_block = '\n'.join(about_block_lines) if about_block_lines else '（无官网信息）'

        return f"""你是一位资深B2B销售调研分析师。以下是从互联网实时搜索到的信息，请仅基于这些信息生成"{company_name}"的结构化调研报告，不要凭空生成未在搜索结果中出现的内容。

## 调研目标
{context}

## 实时搜索结果（来自互联网）
{search_block}

## 工商信息（来自爱企查）
{business_block}

## 公司官网"关于我们"内容
{about_block}

## 调研要求
请从以下4个维度分析"{company_name}"，**只输出搜索结果中明确出现的信息**，不确定的内容标注"待确认"。如果搜索结果未覆盖某维度，对应字段返回空数组或空字符串，不要编造。

### 维度1：组织概况与核心职能
- 组织性质（政府机关/事业单位/国企/民企/外企）
- 主要职能和业务范围
- 服务的对象群体
- 规模量级（人员/分支机构）

### 维度2：战略方向与数字化举措
- 近年公开的战略举措或重点工程
- 数字化转型方向（如果有）
- 政策驱动因素（如果是政府/事业单位）

### 维度3：组织架构与关键决策层
- 主要部门设置
- 关键决策岗位（如局长/主任/CXO/总监等，**不要编造具体人名**，只列出职位）
- 采购决策链常见环节

### 维度4：采购/项目动态
- 常见采购品类
- 典型项目模式（如总包/集成/咨询等）
- 预算规模量级（如果能推断）

## 输出格式（严格JSON）
{{
  "company_name": "{company_name}",
  "company_type": "组织性质",
  "confidence": "high|medium|low",
  "overview": {{
    "functions": ["职能1", "职能2"],
    "service_targets": "服务对象",
    "scale": "规模描述"
  }},
  "strategy": {{
    "initiatives": ["战略举措1", "战略举措2"],
    "digital_direction": "数字化方向",
    "policy_drivers": ["政策因素1"]
  }},
  "organization": {{
    "departments": ["部门1", "部门2"],
    "key_positions": ["关键决策岗位1", "关键决策岗位2"],
    "decision_chain": ["环节1", "环节2", "环节3"]
  }},
  "procurement": {{
    "categories": ["采购品类1"],
    "project_models": ["项目模式1"],
    "budget_scale": "预算规模量级"
  }},
  "notes": "其他补充说明或不确定性声明",
  "_sources": ["引用的来源URL1", "引用的来源URL2"]
}}

只输出JSON，不要输出其他内容。"""

    def _build_report_from_llm(
        self,
        result: Dict,
        company_name: str,
        industry: str,
        data_sources: List[str],
        search_timestamp: str,
        is_realtime: bool,
    ) -> str:
        """把 LLM 结构化结果转成文本报告（顶部展示来源/时间/实时标签，每段附注来源 URL）"""
        # 收集引用来源 URL（去重保持顺序）
        sources: List[str] = []
        seen: set = set()
        for url in result.get('_sources') or []:
            if isinstance(url, str) and url and url not in seen:
                seen.add(url)
                sources.append(url)

        lines: List[str] = []
        lines.append(f"# {company_name} 背景调研报告")
        if industry:
            lines.append(f"行业: {industry}")

        confidence = result.get('confidence', 'medium')
        confidence_label = {'high': '高', 'medium': '中', 'low': '低'}.get(confidence, '中')
        lines.append(f"信息置信度: {confidence_label}")

        # 顶部数据来源/时间/实时标签
        sources_label = ' + '.join(data_sources) if data_sources else '（无）'
        lines.append(f"数据来源: {sources_label} + 工商信息 + 公司官网")
        lines.append(f"搜索时间: {search_timestamp}")
        lines.append("实时搜索: 是" if is_realtime else "实时搜索: 否（基于历史数据）")
        lines.append("")

        def _append_sources_annotation():
            """每段内容后附注来源 URL（从 result._sources 中提取）"""
            if sources:
                lines.append("来源参考:")
                for s in sources:
                    lines.append(f"  - {s}")
                lines.append("")

        # 组织概况
        overview = result.get('overview', {})
        if overview:
            lines.append("## 组织概况与核心职能")
            functions = overview.get('functions', [])
            if functions:
                lines.append(f"核心职能: {', '.join(functions)}")
            if overview.get('service_targets'):
                lines.append(f"服务对象: {overview['service_targets']}")
            if overview.get('scale'):
                lines.append(f"规模: {overview['scale']}")
            lines.append("")
            _append_sources_annotation()

        # 战略方向
        strategy = result.get('strategy', {})
        if strategy:
            lines.append("## 战略方向与数字化举措")
            initiatives = strategy.get('initiatives', [])
            if initiatives:
                lines.append("战略举措:")
                for init in initiatives:
                    lines.append(f"  - {init}")
            if strategy.get('digital_direction'):
                lines.append(f"数字化方向: {strategy['digital_direction']}")
            policy_drivers = strategy.get('policy_drivers', [])
            if policy_drivers:
                lines.append(f"政策驱动: {', '.join(policy_drivers)}")
            lines.append("")
            _append_sources_annotation()

        # 组织架构
        organization = result.get('organization', {})
        if organization:
            lines.append("## 组织架构与关键决策层")
            departments = organization.get('departments', [])
            if departments:
                lines.append(f"主要部门: {', '.join(departments)}")
            key_positions = organization.get('key_positions', [])
            if key_positions:
                lines.append("关键决策岗位:")
                for pos in key_positions:
                    lines.append(f"  - {pos}")
            decision_chain = organization.get('decision_chain', [])
            if decision_chain:
                lines.append(f"采购决策链: {' → '.join(decision_chain)}")
            lines.append("")
            _append_sources_annotation()

        # 采购动态
        procurement = result.get('procurement', {})
        if procurement:
            lines.append("## 采购/项目动态")
            categories = procurement.get('categories', [])
            if categories:
                lines.append(f"采购品类: {', '.join(categories)}")
            project_models = procurement.get('project_models', [])
            if project_models:
                lines.append(f"项目模式: {', '.join(project_models)}")
            if procurement.get('budget_scale'):
                lines.append(f"预算规模: {procurement['budget_scale']}")
            lines.append("")
            _append_sources_annotation()

        # 补充说明
        notes = result.get('notes')
        if notes:
            lines.append("## 补充说明")
            lines.append(notes)
            lines.append("")

        report = '\n'.join(lines)

        if len(report) > self.MAX_REPORT_LEN:
            report = report[:self.MAX_REPORT_LEN] + '\n\n...(调研报告已截断)'

        return report

    def _extract_raw_results(self, result: Dict) -> List[Dict]:
        """从LLM结果提取结构化数据"""
        raw = []
        for section_key, section_label in [
            ('overview', '组织概况'),
            ('strategy', '战略方向'),
            ('organization', '组织架构'),
            ('procurement', '采购动态')
        ]:
            section = result.get(section_key, {})
            if section:
                raw.append({
                    'dimension': section_label,
                    'data': section
                })
        return raw
