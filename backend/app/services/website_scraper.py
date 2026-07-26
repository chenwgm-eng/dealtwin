"""
公司官网抓取模块

通过 WebSearchOrchestrator 找到公司官网 URL，抓取首页与"管理团队""关于我们"
等子页面，并使用 LLM 从 HTML 文本中抽取结构化人员信息。

约束：
- 所有网络请求均带反爬策略（UA、Referer、请求间隔、robots.txt 检查）
- 所有公开方法均在 Config.WEBSITE_SCRAPING_ENABLED=False 时直接返回空
- 所有公开方法均吞掉异常，返回空列表/空字典，不向上层抛出
"""

from __future__ import annotations

import logging
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from ..config import Config
from ..utils.llm_client import LLMClient
from .web_search_providers import WebSearchOrchestrator, SearchResult

logger = logging.getLogger(__name__)


class WebsiteScraper:
    """公司官网抓取器"""

    # Chrome UA（反爬）
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
    # 搜索引擎首页作为 Referer（反爬）
    REFERER = 'https://www.baidu.com/'

    # 排除的域名（搜索引擎自身 + 社交平台 + 站点聚合）
    EXCLUDED_DOMAINS = {
        'baidu.com', 'sogou.com', 'bing.com', 'google.com',
        'tavily.com', 'zhihu.com', 'weibo.com', 'douyin.com',
        'tiktok.com', 'facebook.com', 'twitter.com', 'x.com',
        'linkedin.com', 'youtube.com', 'github.com', 'csdn.net',
        'sohu.com', 'sina.com.cn', 'qq.com', '163.com',
    }

    # 团队页链接文本关键字（中英文）
    TEAM_LINK_KEYWORDS = [
        '管理团队', '领导班子', '核心团队', '团队介绍', '高管团队',
        '关于我们', '公司简介', '公司介绍', '公司概况', '企业简介',
        'About Us', 'About', 'Team', 'Leadership', 'Management',
    ]

    # 关于页链接文本关键字（中英文）
    ABOUT_LINK_KEYWORDS = [
        '关于我们', '公司简介', '公司介绍', '公司概况', '企业简介',
        'About Us', 'About', 'Company',
    ]

    # HTML 内容大小上限（100KB，避免抓取超大页面）
    MAX_HTML_SIZE = 100 * 1024

    # 单次抓取团队页数量上限（避免过度抓取）
    MAX_TEAM_PAGES = 3

    # LLM 抽取人员上限
    MAX_PERSONNEL_PER_PAGE = 20

    # LLM 输入文本长度上限（避免超出上下文）
    MAX_LLM_TEXT_LEN = 8000

    # 人员抽取 prompt 模板（{{ }} 经 .format() 后变为单层 { }）
    PROMPT_TEMPLATE = """你是企业人员信息抽取助手。请从以下 HTML 文本中抽取"{company_name}"公司的管理团队成员信息。

HTML 内容（已去除标签的纯文本）：
{html_text}

请返回 JSON 对象，格式如下：
{{
  "personnel": [
    {{
      "name": "姓名",
      "position": "职位（如董事长、总经理、CEO 等）",
      "bio": "简介（如有）"
    }}
  ]
}}

注意：
- 只输出 JSON 对象，不要其他文字
- 只抽取明确的人员信息（姓名+职位），不要编造
- 若 HTML 中无人员信息，返回 {{"personnel": []}}
- 最多抽取 20 人"""

    # robots.txt 缓存：{域名: bool}，类属性跨实例共享
    _robots_cache: Dict[str, bool] = {}

    def find_official_website(self, company_name: str) -> Optional[str]:
        """
        通过 WebSearchOrchestrator 搜索"{公司名} 官网"，识别公司主域名 URL。

        识别策略：
        1. 优先返回域名中含公司名关键字（英文名/拼音片段）的结果
        2. 排除搜索引擎自身与社交平台域名
        3. 退化为首个未排除的 URL
        """
        if not Config.WEBSITE_SCRAPING_ENABLED:
            return None
        if not company_name or not company_name.strip():
            return None

        company_name = company_name.strip()
        try:
            orchestrator = WebSearchOrchestrator()
            search_data = orchestrator.search_with_fallback(
                f"{company_name} 官网", max_results=5
            )
            results: List[SearchResult] = search_data.get('results') or []
        except Exception as e:
            logger.warning(f"搜索公司官网失败 [{company_name}]: {e}")
            return None

        # 公司名核心关键字（去后缀 + 英文 token），用于优先匹配
        core_keywords = self._extract_company_keywords(company_name)

        # 第一轮：优先匹配含公司名关键字的域名
        for r in results:
            url = (r.url or '').strip()
            if not url or self._is_excluded_url(url):
                continue
            url_lower = url.lower()
            for kw in core_keywords:
                if kw and kw.lower() in url_lower:
                    return url

        # 第二轮：返回首个未排除的 URL
        for r in results:
            url = (r.url or '').strip()
            if not url or self._is_excluded_url(url):
                continue
            return url

        return None

    def scrape_team_page(self, company_name: str) -> List[Dict]:
        """
        抓取公司管理团队页面，返回人员信息列表。

        流程：找官网 -> 抓首页 -> 识别团队页链接 -> 抓团队页 -> LLM 抽取人员 -> 去重
        """
        if not Config.WEBSITE_SCRAPING_ENABLED:
            return []
        if not company_name or not company_name.strip():
            return []

        company_name = company_name.strip()
        try:
            # 1. 找官网
            official_url = self.find_official_website(company_name)
            if not official_url:
                return []

            # 2. 抓取首页 HTML
            homepage_html = self._fetch_html(official_url)
            if not homepage_html:
                return []

            # 3. 识别团队页链接
            team_links = self._extract_links_by_keywords(
                homepage_html, official_url, self.TEAM_LINK_KEYWORDS
            )
            if not team_links:
                return []

            # 4. 抓取团队页内容（最多 MAX_TEAM_PAGES 个），LLM 抽取人员
            all_personnel: List[Dict] = []
            seen_names: set = set()
            for page_url in team_links[: self.MAX_TEAM_PAGES]:
                page_html = self._fetch_html(page_url)
                if not page_html:
                    continue
                personnel = self.extract_personnel_from_html(
                    page_html, company_name, page_url
                )
                for p in personnel:
                    name = (p.get('name') or '').strip()
                    if not name or name in seen_names:
                        continue
                    seen_names.add(name)
                    all_personnel.append(p)
            return all_personnel
        except Exception as e:
            logger.warning(f"抓取团队页失败 [{company_name}]: {e}")
            return []

    def scrape_about_page(self, company_name: str) -> Dict:
        """
        抓取公司"关于我们/公司简介"页面，返回正文文本。

        流程：找官网 -> 抓首页 -> 识别关于页链接 -> 抓关于页 -> 提取正文文本
        """
        if not Config.WEBSITE_SCRAPING_ENABLED:
            return {}
        if not company_name or not company_name.strip():
            return {}

        company_name = company_name.strip()
        try:
            official_url = self.find_official_website(company_name)
            if not official_url:
                return {}

            homepage_html = self._fetch_html(official_url)
            if not homepage_html:
                return {}

            about_links = self._extract_links_by_keywords(
                homepage_html, official_url, self.ABOUT_LINK_KEYWORDS
            )
            if not about_links:
                return {}

            about_url = about_links[0]
            about_html = self._fetch_html(about_url)
            if not about_html:
                return {}

            soup = BeautifulSoup(about_html, 'html.parser')
            about_text = soup.get_text(' ', strip=True)
            return {
                'company_name': company_name,
                'about_text': about_text,
                'source_url': about_url,
                'source_provider': 'website',
            }
        except Exception as e:
            logger.warning(f"抓取关于页失败 [{company_name}]: {e}")
            return {}

    def extract_personnel_from_html(
        self, html_text: str, company_name: str, source_url: str
    ) -> List[Dict]:
        """使用 LLM 从 HTML 文本中抽取管理团队成员信息"""
        if not Config.WEBSITE_SCRAPING_ENABLED:
            return []
        if not html_text:
            return []

        # 去除 HTML 标签得到纯文本
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            plain_text = soup.get_text(' ', strip=True)
        except Exception as e:
            logger.warning(f"HTML 解析失败: {e}")
            return []

        if not plain_text.strip():
            return []

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
            logger.warning(f"LLM 抽取人员信息失败 [{company_name}]: {e}")
            return []

        if not isinstance(result, dict):
            return []

        personnel_list = result.get('personnel') or []
        if not isinstance(personnel_list, list):
            return []

        output: List[Dict] = []
        for item in personnel_list:
            if not isinstance(item, dict):
                continue
            name = (item.get('name') or '').strip()
            if not name:
                continue
            output.append({
                'name': name,
                'position': (item.get('position') or '').strip(),
                'bio': (item.get('bio') or '').strip(),
                'source_url': source_url,
                'source_provider': 'website',
            })
            if len(output) >= self.MAX_PERSONNEL_PER_PAGE:
                break
        return output

    # ====================== 内部辅助方法 ======================

    def _fetch_html(self, url: str) -> Optional[str]:
        """抓取 URL 的 HTML 内容，带反爬策略、robots.txt 检查与大小限制"""
        if not url:
            return None
        # robots.txt 检查
        if not self._check_robots(url):
            logger.info(f"robots.txt 禁止抓取: {url}")
            return None
        # 反爬：请求间隔
        time.sleep(Config.WEB_SEARCH_REQUEST_INTERVAL)
        headers = {
            'User-Agent': self.USER_AGENT,
            'Referer': self.REFERER,
        }
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

    def _is_excluded_url(self, url: str) -> bool:
        """判断 URL 是否属于应排除的域名（搜索引擎/社交平台）"""
        try:
            netloc = urlparse(url).netloc.lower()
            if not netloc:
                return True
            for excluded in self.EXCLUDED_DOMAINS:
                if excluded in netloc:
                    return True
            return False
        except Exception:
            return True

    def _extract_company_keywords(self, company_name: str) -> List[str]:
        """
        从公司名中提取核心关键字（去后缀 + 英文 token）。

        用于优先匹配官网域名（如"Alibaba Group"->["Alibaba Group", "Alibaba"]）。
        中文公司名无拼音库时退化为原名匹配，依赖 _is_excluded_url 兜底。
        """
        # 常见公司名后缀（中英文）
        suffixes = [
            '股份有限公司', '有限责任公司', '有限公司', '集团',
            '总公司', '分公司', '控股集团', '公司',
            'Co., Ltd', 'Co.,Ltd', 'Ltd', 'Inc', 'Corp',
            'Corporation', 'Group', 'Company',
        ]
        core = company_name
        for suf in suffixes:
            if core.endswith(suf):
                core = core[: -len(suf)]
                break
        core = core.strip()

        keywords: List[str] = []
        if core:
            keywords.append(core)
        # 提取连续的 ASCII 字母片段作为英文关键字（≥3 字符）
        for tok in re.findall(r'[A-Za-z][A-Za-z0-9\-]+', company_name):
            if len(tok) >= 3 and tok not in keywords:
                keywords.append(tok)
        return keywords

    def _extract_links_by_keywords(
        self, homepage_html: str, base_url: str, keywords: List[str]
    ) -> List[str]:
        """从首页 HTML 中识别链接文本匹配关键字的 URL（保持顺序去重）"""
        try:
            soup = BeautifulSoup(homepage_html, 'html.parser')
        except Exception as e:
            logger.warning(f"首页 HTML 解析失败: {e}")
            return []

        links: List[str] = []
        seen: set = set()
        for a in soup.find_all('a'):
            href = (a.get('href') or '').strip()
            if not href or href.startswith('#'):
                continue
            if href.lower().startswith(('javascript:', 'mailto:', 'tel:')):
                continue
            text = a.get_text(strip=True)
            if not text:
                continue
            if not self._match_link_text(text, keywords):
                continue
            full_url = urljoin(base_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            links.append(full_url)
        return links

    def _match_link_text(self, text: str, keywords: List[str]) -> bool:
        """判断链接文本是否命中关键字（中文大小写敏感，英文不敏感）"""
        text_lower = text.lower()
        for kw in keywords:
            if not kw:
                continue
            # 中文关键字直接包含匹配
            if kw in text:
                return True
            # 英文关键字大小写不敏感匹配
            if kw.isascii() and kw.lower() in text_lower:
                return True
        return False
