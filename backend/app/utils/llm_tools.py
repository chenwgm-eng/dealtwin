"""
LLM工具调用支持
- web_search：通过多 Provider 链式降级实时联网搜索（Tavily → 百度 → 搜狗 → LLM 兜底）
- 工具调用循环：模型决策 → 后端执行 → 结果回传 → 模型生成最终答案
"""

import json
import logging
from typing import Optional, Dict, Any, List

from ..config import Config

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 5) -> str:
    """通过多 Provider 链式降级实时联网搜索，返回带来源信息的格式化文本

    链式降级顺序：Tavily → 百度 → 搜狗 → LLM 训练数据兜底。
    首个返回非空结果的 provider 即终止。每条结果附 [来源: provider] URL 前缀，
    供 LLM 在工具调用循环中阅读和溯源。

    Args:
        query: 搜索查询词
        max_results: 最大结果数

    Returns:
        格式化的搜索结果文本（供LLM阅读），包含来源标签
    """
    try:
        # 延迟导入避免循环依赖
        from ..services.web_search_providers import WebSearchOrchestrator

        orchestrator = WebSearchOrchestrator()
        fallback = orchestrator.search_with_fallback(query, max_results=max_results)
        results = fallback.get('results') or []
        providers_used = fallback.get('providers_used') or []
        is_realtime = bool(fallback.get('is_realtime'))

        if not results:
            return "未找到相关信息（所有搜索 provider 均无结果）"

        parts = []
        # 顶部元信息：来源 provider + 实时性
        provider_label = "、".join(providers_used) if providers_used else "未知"
        realtime_label = "实时搜索" if is_realtime else "基于历史数据（非实时）"
        parts.append(f"【搜索元信息】来源: {provider_label} | {realtime_label}")

        # 各条搜索结果
        for i, r in enumerate(results, 1):
            title = r.title or ""
            url = r.url or ""
            content = r.content or ""
            source = r.source_provider or ""
            source_prefix = f"[来源: {source}]"
            url_part = f"URL: {url}" if url else "URL: (无)"
            parts.append(f"【结果{i}】{source_prefix} {title}\n{url_part}\n{content}")

        return "\n\n".join(parts)
    except Exception as e:
        logger.error(f"web_search 执行失败: {e}")
        return f"搜索失败: {str(e)[:200]}"


# 工具定义（OpenAI兼容格式）
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索网络信息，获取最新的事实数据。用于查询公司工商注册信息、产品信息、新闻动态等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词，如'北京三快科技有限公司 工商注册信息'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# 工具名 → 执行函数映射
TOOL_EXECUTORS = {
    "web_search": lambda args: web_search(args.get("query", "")),
}


def chat_with_tools(
    messages: List[Dict[str, Any]],
    llm_client,
    temperature: float = 0.4,
    max_tokens: int = 3000,
    max_tool_rounds: int = 5,
) -> Dict[str, Any]:
    """带工具调用的LLM对话循环

    流程：
    1. 发送messages + tools给LLM
    2. 若LLM返回tool_calls，执行对应工具，把结果作为tool消息追加到messages
    3. 再次调用LLM，让其基于工具结果继续生成
    4. 重复直到LLM不再调用工具或达到max_tool_rounds

    Args:
        messages: 初始消息列表
        llm_client: LLMClient实例
        temperature: 温度
        max_tokens: 最大tokens
        max_tool_rounds: 最大工具调用轮次

    Returns:
        {
            "content": str,           # 最终文本内容
            "tool_calls_made": int,   # 实际工具调用次数
            "tool_results": list,     # 各轮工具结果（用于调试）
        }
    """
    tool_calls_made = 0
    tool_results = []

    for _ in range(max_tool_rounds + 1):
        resp = llm_client.client.chat.completions.create(
            model=llm_client.model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = resp.choices[0]
        msg = choice.message

        # 若无工具调用，返回最终内容
        if not getattr(msg, "tool_calls", None):
            return {
                "content": msg.content or "",
                "tool_calls_made": tool_calls_made,
                "tool_results": tool_results,
            }

        # 把assistant的工具调用消息追加到历史
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in msg.tool_calls
            ]
        })

        # 执行每个工具调用，把结果作为tool消息追加
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                fn_args = {}

            executor = TOOL_EXECUTORS.get(fn_name)
            if executor:
                result = executor(fn_args)
            else:
                result = f"工具 {fn_name} 不存在"

            tool_results.append({"name": fn_name, "args": fn_args, "result": result[:500]})
            tool_calls_made += 1

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    # 达到最大轮次仍有工具调用，做一次无工具调用收尾
    # 明确指示LLM：工具调用已达上限，必须基于已有信息直接输出最终答案
    final_messages = list(messages) + [{
        "role": "user",
        "content": "工具调用次数已达上限。请基于已获取的搜索结果直接输出最终答案，不要再尝试调用工具。如果某些字段没有查到，留空字符串即可。"
    }]
    resp = llm_client.client.chat.completions.create(
        model=llm_client.model,
        messages=final_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    final_content = resp.choices[0].message.content or ""
    # 清理LongCat模型可能输出的伪工具调用标签
    import re
    final_content = re.sub(r'<longcat_tool_call>[\s\S]*?</longcat_tool_call>', '', final_content).strip()
    return {
        "content": final_content,
        "tool_calls_made": tool_calls_made,
        "tool_results": tool_results,
    }
