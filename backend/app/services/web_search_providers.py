"""
多 Provider 链式降级实时搜索模块

支持多个搜索 provider（Tavily API、百度、搜狗、LLM 知识库），
按 Config.WEB_SEARCH_PROVIDERS 配置顺序链式降级：
首个返回非空结果的 provider 即终止。

- tavily：实时搜索 API，需 API Key
- baidu/sogou：直接抓取搜索结果页（简化解析，反爬受限）
- llm_knowledge：基于 LLM 训练数据兜底（非实时，is_realtime=False）
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from ..config import Config
from ..utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """单条搜索结果"""
    title: str
    url: str
    content: str
    source_provider: str  # tavily/baidu/sogou/llm_knowledge
    fetched_at: str  # ISO 8601 时间戳
    is_realtime: bool  # True=实时搜索, False=LLM 训练数据


class WebSearchProvider(ABC):
    """搜索 Provider 抽象基类"""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """执行搜索，返回结果列表（失败返回空列表，不抛异常）"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查 provider 是否可用"""
        ...


class TavilySearchProvider(WebSearchProvider):
    """Tavily API 搜索 provider（实时）"""

    SEARCH_URL = 'https://api.tavily.com/search'
    TIMEOUT = 30  # Tavily 固定 30s 超时

    def is_available(self) -> bool:
        return bool(Config.TAVILY_API_KEY)

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.is_available():
            return []
        payload = {
            'api_key': Config.TAVILY_API_KEY,
            'query': query,
            'search_depth': 'advanced',
            'max_results': max_results,
            'include_answer': True,
            'include_raw_content': False,
        }
        try:
            resp = requests.post(self.SEARCH_URL, json=payload, timeout=self.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"Tavily 搜索失败: {e}")
            return []

        results: List[SearchResult] = []
        now = datetime.now().isoformat()

        # Tavily answer 字段作为特殊摘要结果
        answer = data.get('answer')
        if answer:
            results.append(SearchResult(
                title='Tavily 摘要',
                url='',
                content=answer,
                source_provider='tavily',
                fetched_at=now,
                is_realtime=True,
            ))

        # 实际搜索结果（Tavily 已在 payload 中按 max_results 限制）
        for item in data.get('results') or []:
            results.append(SearchResult(
                title=item.get('title', ''),
                url=item.get('url', ''),
                content=item.get('content', ''),
                source_provider='tavily',
                fetched_at=now,
                is_realtime=True,
            ))

        return results


class _HtmlScrapeProvider(WebSearchProvider):
    """HTML 抓取型 provider 基类（百度/搜狗共用反爬与解析逻辑）"""

    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
    SEARCH_URL = ''
    ROBOTS_URL = ''
    REFERER = ''
    SOURCE_PROVIDER = ''
    # 自身域名过滤关键字；命中且不含跳转路径时视为内部链接
    _INTERNAL_DOMAIN = ''
    _INTERNAL_KEEP_PATH = ''  # 跳转链接路径片段（如 /link），不在过滤范围
    _robots_cache: Optional[bool] = None

    def _check_robots(self) -> bool:
        """检查 robots.txt 是否允许抓取搜索路径（结果缓存到类属性）"""
        cls = type(self)
        if cls._robots_cache is not None:
            return cls._robots_cache
        allowed = False
        try:
            resp = requests.get(
                self.ROBOTS_URL,
                headers={'User-Agent': self.USER_AGENT},
                timeout=Config.WEB_SEARCH_TIMEOUT,
            )
            resp.raise_for_status()
            rp = RobotFileParser()
            rp.parse(resp.text.splitlines())
            allowed = rp.can_fetch('*', self.SEARCH_URL)
        except Exception as e:
            logger.warning(f"{cls.__name__} robots.txt 检查失败，默认不允许: {e}")
            allowed = False
        cls._robots_cache = allowed
        return allowed

    def _is_enabled_by_config(self) -> bool:
        """子类实现：Config 开关"""
        raise NotImplementedError

    def is_available(self) -> bool:
        if not self._is_enabled_by_config():
            return False
        return self._check_robots()

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.is_available():
            return []
        # 反爬：请求间隔
        time.sleep(Config.WEB_SEARCH_REQUEST_INTERVAL)
        headers = {
            'User-Agent': self.USER_AGENT,
            'Referer': self.REFERER,
        }
        params = self._build_params(query)
        try:
            resp = requests.get(
                self.SEARCH_URL, params=params, headers=headers,
                timeout=Config.WEB_SEARCH_TIMEOUT,
            )
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
        except Exception as e:
            logger.warning(f"{type(self).__name__} 搜索请求失败: {e}")
            return []

        return self._parse_html(resp.text, max_results)

    def _build_params(self, query: str) -> Dict[str, str]:
        """子类实现：构建查询参数"""
        raise NotImplementedError

    def _parse_html(self, html: str, max_results: int) -> List[SearchResult]:
        """简化解析：抓取 <a> 标签，过滤内部链接，摘要用父容器 get_text()"""
        results: List[SearchResult] = []
        now = datetime.now().isoformat()
        try:
            soup = BeautifulSoup(html, 'html.parser')
            seen_urls: set = set()
            for a in soup.find_all('a'):
                href = (a.get('href') or '').strip()
                if not href or href.startswith('#') or href.lower().startswith('javascript'):
                    continue
                # 过滤搜索引擎自身内部链接（保留 /link 或 /inter 跳转链接）
                if self._INTERNAL_DOMAIN in href and self._INTERNAL_KEEP_PATH not in href:
                    continue
                if href in seen_urls:
                    continue
                title = a.get_text(strip=True)
                if not title:
                    continue
                parent = a.parent
                content = parent.get_text(' ', strip=True) if parent is not None else ''
                results.append(SearchResult(
                    title=title,
                    url=href,
                    content=content,
                    source_provider=self.SOURCE_PROVIDER,
                    fetched_at=now,
                    is_realtime=True,
                ))
                seen_urls.add(href)
                if len(results) >= max_results:
                    break
        except Exception as e:
            logger.warning(f"{type(self).__name__} 搜索结果解析失败: {e}")
            return []
        return results


class BaiduSearchProvider(_HtmlScrapeProvider):
    """百度搜索结果页抓取 provider（实时，简化解析）"""

    SEARCH_URL = 'https://www.baidu.com/s'
    ROBOTS_URL = 'https://www.baidu.com/robots.txt'
    REFERER = 'https://www.baidu.com/'
    SOURCE_PROVIDER = 'baidu'
    _INTERNAL_DOMAIN = 'baidu.com'
    _INTERNAL_KEEP_PATH = '/link'  # 百度搜索结果跳转链接形如 www.baidu.com/link?url=...
    _robots_cache: Optional[bool] = None

    def _is_enabled_by_config(self) -> bool:
        return Config.BAIDU_SEARCH_ENABLED

    def _build_params(self, query: str) -> Dict[str, str]:
        # 参数已由 requests 自动 urlencode
        return {'wd': query}


class SogouSearchProvider(_HtmlScrapeProvider):
    """搜狗搜索结果页抓取 provider（实时，简化解析）"""

    SEARCH_URL = 'https://www.sogou.com/web'
    ROBOTS_URL = 'https://www.sogou.com/robots.txt'
    REFERER = 'https://www.sogou.com/'
    SOURCE_PROVIDER = 'sogou'
    _INTERNAL_DOMAIN = 'sogou.com'
    _INTERNAL_KEEP_PATH = '/inter'  # 搜狗搜索结果跳转链接形如 sogou.com/inter/redirect
    _robots_cache: Optional[bool] = None

    def _is_enabled_by_config(self) -> bool:
        return Config.SOGOU_SEARCH_ENABLED

    def _build_params(self, query: str) -> Dict[str, str]:
        return {'query': query}


class LLMKnowledgeProvider(WebSearchProvider):
    """基于 LLM 训练数据的兜底 provider（非实时，is_realtime=False）"""

    # 适配说明：LLMClient.chat_json 内部使用 response_format={"type":"json_object"}，
    # 要求 LLM 返回 JSON 对象而非数组。因此将结果数组包装在 {"results": [...]} 对象中，
    # 再在 search() 中提取 results 字段。这是对原 prompt 模板（要求 JSON 数组）的必要适配。
    PROMPT_TEMPLATE = """你是信息检索助手。请基于你的训练数据，回答以下查询，并模拟搜索引擎返回多条结果。

查询：{query}

请返回 JSON 对象（最多 {max_results} 条结果），格式如下：
{{
  "results": [
    {{
      "title": "结果标题",
      "url": "可能的来源 URL（如已知）",
      "content": "结果摘要（100-200字）"
    }}
  ]
}}

注意：
- 只输出 JSON 对象，不要其他文字
- 内容必须基于训练数据，不要编造不存在的 URL
- 若不知道，返回 {{"results": []}}"""

    def is_available(self) -> bool:
        # 兜底 provider 总是可用
        return True

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        prompt = self.PROMPT_TEMPLATE.format(query=query, max_results=max_results)
        try:
            llm = LLMClient()
            result = llm.chat_json(
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
        except Exception as e:
            logger.warning(f"LLM 知识库搜索失败: {e}")
            return []

        # chat_json 返回 dict，提取 results 数组；兼容 LLM 偶发返回 list 的情况
        if isinstance(result, list):
            items = result
        elif isinstance(result, dict):
            items = result.get('results') or []
        else:
            logger.warning(f"LLM 知识库返回类型异常: {type(result).__name__}")
            return []

        results: List[SearchResult] = []
        now = datetime.now().isoformat()
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append(SearchResult(
                title=item.get('title', ''),
                url=item.get('url', ''),
                content=item.get('content', ''),
                source_provider='llm_knowledge',
                fetched_at=now,
                is_realtime=False,
            ))
            if len(results) >= max_results:
                break
        return results


PROVIDER_REGISTRY = {
    'tavily': TavilySearchProvider,
    'baidu': BaiduSearchProvider,
    'sogou': SogouSearchProvider,
    'llm_knowledge': LLMKnowledgeProvider,
}


class WebSearchOrchestrator:
    """多 Provider 链式降级搜索编排器"""

    def __init__(self):
        self._providers: List[WebSearchProvider] = []
        self._provider_names: List[str] = []
        for name in Config.WEB_SEARCH_PROVIDERS:
            cls = PROVIDER_REGISTRY.get(name)
            if cls is None:
                logger.warning(f"未知搜索 provider: {name}，已跳过")
                continue
            self._providers.append(cls())
            self._provider_names.append(name)

    def search_with_fallback(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        按配置顺序链式降级搜索，首个返回非空结果的 provider 即终止。

        Returns:
            {
                'results': List[SearchResult],
                'providers_used': List[str],  # 实际产出结果的 provider 名（链式降级下最多 1 个）
                'is_realtime': bool,          # any(r.is_realtime for r in results)
            }
        """
        for name, provider in zip(self._provider_names, self._providers):
            try:
                if not provider.is_available():
                    continue
                results = provider.search(query, max_results)
            except Exception as e:
                logger.warning(f"provider {name} 执行异常: {e}")
                continue
            if results:
                return {
                    'results': results,
                    'providers_used': [name],
                    'is_realtime': any(r.is_realtime for r in results),
                }
        return {'results': [], 'providers_used': [], 'is_realtime': False}

    @classmethod
    def get_provider(cls, name: str) -> Optional[WebSearchProvider]:
        """获取单个 provider 实例（供其他模块复用）"""
        provider_cls = PROVIDER_REGISTRY.get(name)
        return provider_cls() if provider_cls else None
