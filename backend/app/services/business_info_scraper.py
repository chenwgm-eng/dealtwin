"""
工商信息抓取模块

通过爱企查/天眼查搜索公司名称，抓取公司工商详情页，并使用 LLM 抽取结构化
工商注册信息（法定代表人、注册资本、成立日期、企业类型、经营范围、注册地址、
统一社会信用代码、股东信息等）。

约束：
- 所有网络请求均带反爬策略（UA、Referer、请求间隔、robots.txt 检查）
- 所有公开方法均在 Config.BUSINESS_INFO_SCRAPING_ENABLED=False 时直接返回空
- 所有公开方法均吞掉异常，返回空字典，不向上层抛出
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple
from urllib.parse import quote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from ..config import Config
from ..utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class BusinessInfoScraper:
    """工商信息抓取器（爱企查为主，天眼查为备用）"""

    # Chrome UA（反爬）
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )

    # HTML 内容大小上限（100KB，避免抓取超大页面）
    MAX_HTML_SIZE = 100 * 1024

    # LLM 输入文本长度上限（避免超出上下文）
    MAX_LLM_TEXT_LEN = 8000

    # 爱企查配置
    AIQICHA_HOME = 'https://aiqicha.baidu.com/'
    AIQICHA_SEARCH_URL = 'https://aiqicha.baidu.com/s?q={company_name}'
    # 爱企查详情页 URL 匹配模式（子串匹配，大小写不敏感）
    AIQICHA_DETAIL_PATTERNS: Tuple[str, ...] = (
        'aiqicha.baidu.com/company_detail_',
        'aiqicha.baidu.com/detail/',
    )

    # 天眼查配置
    TIANYANCHA_HOME = 'https://www.tianyancha.com/'
    TIANYANCHA_SEARCH_URL = 'https://www.tianyancha.com/search?key={company_name}'
    # 天眼查详情页 URL 匹配模式
    TIANYANCHA_DETAIL_PATTERNS: Tuple[str, ...] = (
        'tianyancha.com/company/',
    )

    # 工商信息抽取 prompt 模板（{{ }} 经 .format() 后变为单层 { }）
    PROMPT_TEMPLATE = """你是工商信息抽取助手。请从以下网页文本中抽取"{company_name}"的工商注册信息。

网页内容（已去除标签的纯文本）：
{html_text}

请返回 JSON 对象，格式如下：
{{
  "legal_representative": "法定代表人姓名",
  "registered_capital": "注册资本（含币种）",
  "establish_date": "成立日期 YYYY-MM-DD",
  "enterprise_type": "企业类型",
  "business_scope": "经营范围",
  "registered_address": "注册地址",
  "unified_credit_code": "统一社会信用代码",
  "shareholders": "主要股东信息（字符串描述）"
}}

注意：
- 只输出 JSON 对象，不要其他文字
- 只抽取明确出现在网页中的信息，不要编造
- 找不到的字段留空字符串 ""
- 若网页中无任何工商信息，所有字段返回空字符串"""

    # 返回字段白名单（用于规范化 LLM 结果）
    RESULT_FIELDS: Tuple[str, ...] = (
        'legal_representative',
        'registered_capital',
        'establish_date',
        'enterprise_type',
        'business_scope',
        'registered_address',
        'unified_credit_code',
        'shareholders',
    )

    # robots.txt 缓存：{域名: bool}，类属性跨实例共享
    _robots_cache: Dict[str, bool] = {}

    def scrape_aiqicha(self, company_name: str) -> Dict:
        """
        抓取爱企查工商信息。

        流程：抓搜索结果页 -> 识别详情页 URL -> 抓详情页 -> LLM 抽取工商信息
        """
        if not Config.BUSINESS_INFO_SCRAPING_ENABLED:
            return {}
        if not company_name or not company_name.strip():
            return {}

        company_name = company_name.strip()
        try:
            # 1. 抓取搜索结果页
            search_url = self.AIQICHA_SEARCH_URL.format(
                company_name=quote(company_name)
            )
            search_html = self._fetch_html(search_url, referer=self.AIQICHA_HOME)
            if not search_html:
                return {}

            # 2. 识别详情页 URL
            detail_url = self._find_detail_url(
                search_html, search_url, self.AIQICHA_DETAIL_PATTERNS
            )
            if not detail_url:
                logger.info(f"爱企查未找到详情页 URL [{company_name}]")
                return {}

            # 3. 抓取详情页
            detail_html = self._fetch_html(detail_url, referer=self.AIQICHA_HOME)
            if not detail_html:
                return {}

            # 4. LLM 抽取工商信息
            info = self._extract_business_info_with_llm(detail_html, company_name)
            if not info:
                return {}

            info['source_provider'] = 'aiqicha'
            info['source_url'] = detail_url
            return info
        except Exception as e:
            logger.warning(f"爱企查抓取失败 [{company_name}]: {e}")
            return {}

    def scrape_tianyancha(self, company_name: str) -> Dict:
        """
        抓取天眼查工商信息（备用）。

        流程：抓搜索结果页 -> 识别详情页 URL -> 抓详情页 -> LLM 抽取工商信息
        """
        if not Config.BUSINESS_INFO_SCRAPING_ENABLED:
            return {}
        if not company_name or not company_name.strip():
            return {}

        company_name = company_name.strip()
        try:
            # 1. 抓取搜索结果页
            search_url = self.TIANYANCHA_SEARCH_URL.format(
                company_name=quote(company_name)
            )
            search_html = self._fetch_html(search_url, referer=self.TIANYANCHA_HOME)
            if not search_html:
                return {}

            # 2. 识别详情页 URL
            detail_url = self._find_detail_url(
                search_html, search_url, self.TIANYANCHA_DETAIL_PATTERNS
            )
            if not detail_url:
                logger.info(f"天眼查未找到详情页 URL [{company_name}]")
                return {}

            # 3. 抓取详情页
            detail_html = self._fetch_html(detail_url, referer=self.TIANYANCHA_HOME)
            if not detail_html:
                return {}

            # 4. LLM 抽取工商信息
            info = self._extract_business_info_with_llm(detail_html, company_name)
            if not info:
                return {}

            info['source_provider'] = 'tianyancha'
            info['source_url'] = detail_url
            return info
        except Exception as e:
            logger.warning(f"天眼查抓取失败 [{company_name}]: {e}")
            return {}

    def _extract_business_info_with_llm(
        self, html_text: str, company_name: str
    ) -> Dict:
        """使用 LLM 从 HTML 文本中抽取工商注册信息"""
        if not html_text:
            return {}

        # 去除 HTML 标签得到纯文本
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            plain_text = soup.get_text(' ', strip=True)
        except Exception as e:
            logger.warning(f"HTML 解析失败: {e}")
            return {}

        if not plain_text.strip():
            return {}

        # 限制文本长度，避免超出 LLM 上下文
        if len(plain_text) > self.MAX_LLM_TEXT_LEN:
            plain_text = plain_text[: self.MAX_LLM_TEXT_LEN]

        prompt = self.PROMPT_TEMPLATE.format(
            company_name=company_name, html_text=plain_text
        )

        try:
            llm = LLMClient()
            result = llm.chat_json(
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
        except Exception as e:
            logger.warning(f"LLM 抽取工商信息失败 [{company_name}]: {e}")
            return {}

        if not isinstance(result, dict):
            return {}

        # 规范化字段，确保所有字段都存在且为字符串
        info: Dict = {}
        for field in self.RESULT_FIELDS:
            val = result.get(field)
            info[field] = val.strip() if isinstance(val, str) else ''
        return info

    # ====================== 内部辅助方法 ======================

    def _fetch_html(self, url: str, referer: str = '') -> Optional[str]:
        """抓取 URL 的 HTML 内容，带反爬策略、robots.txt 检查与大小限制"""
        if not url:
            return None
        # robots.txt 检查
        if not self._check_robots(url):
            logger.info(f"robots.txt 禁止抓取: {url}")
            return None
        # 反爬：请求间隔
        time.sleep(Config.WEB_SEARCH_REQUEST_INTERVAL)
        headers = {'User-Agent': self.USER_AGENT}
        if referer:
            headers['Referer'] = referer
        try:
            resp = requests.get(
                url, headers=headers, timeout=Config.WEB_SEARCH_TIMEOUT
            )
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
        except Exception as e:
            logger.warning(f"抓取 HTML 失败 [{url}]: {e}")
            return None

        html = resp.text or ''
        # 限制 HTML 大小（按 UTF-8 字节计）
        if len(html.encode('utf-8')) > self.MAX_HTML_SIZE:
            # 中文 UTF-8 占 3 字节，按字符截断更安全（保守取 /3）
            max_chars = self.MAX_HTML_SIZE // 3
            html = html[:max_chars]
            logger.info(f"HTML 过大，已截断: {url}")
        return html

    def _check_robots(self, url: str) -> bool:
        """检查 robots.txt 是否允许抓取该 URL（按域名缓存结果）"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if not domain:
                return False
            if domain in self._robots_cache:
                return self._robots_cache[domain]
            robots_url = f"{parsed.scheme}://{domain}/robots.txt"
            allowed = True  # 默认允许
            try:
                # 用 requests + 自定义 UA 抓取 robots.txt（与现有 provider 一致）
                resp = requests.get(
                    robots_url,
                    headers={'User-Agent': self.USER_AGENT},
                    timeout=Config.WEB_SEARCH_TIMEOUT,
                )
                if resp.status_code == 200:
                    rp = RobotFileParser()
                    rp.parse(resp.text.splitlines())
                    allowed = rp.can_fetch('*', url)
                # 404/其他状态码：默认允许
            except Exception as e:
                logger.debug(f"robots.txt 读取失败 [{domain}]，默认允许: {e}")
                allowed = True
            self._robots_cache[domain] = allowed
            return allowed
        except Exception as e:
            logger.warning(f"robots.txt 检查异常 [{url}]: {e}")
            return True

    def _find_detail_url(
        self, search_html: str, base_url: str, patterns: Tuple[str, ...]
    ) -> Optional[str]:
        """
        从搜索结果页 HTML 中识别匹配模式的详情页 URL。

        用 BeautifulSoup 解析所有 <a> 标签的 href，按给定模式子串匹配（大小写不敏感）。
        相对 URL 通过 urljoin 转为绝对 URL；返回首个匹配项，保持搜索结果顺序。
        """
        try:
            soup = BeautifulSoup(search_html, 'html.parser')
        except Exception as e:
            logger.warning(f"搜索结果页 HTML 解析失败: {e}")
            return None

        seen: set = set()
        for a in soup.find_all('a'):
            href = (a.get('href') or '').strip()
            if not href or href.startswith('#'):
                continue
            if href.lower().startswith(('javascript:', 'mailto:', 'tel:')):
                continue
            full_url = urljoin(base_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            url_lower = full_url.lower()
            for pat in patterns:
                if pat.lower() in url_lower:
                    return full_url
        return None
