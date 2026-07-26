"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
import logging
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        content = message.content

        # 部分模型（如LongCat、MiniMax）可能将内容放在 reasoning_content 字段，
        # 或者 content 为 None 时需要从其他字段获取
        if not content:
            # 尝试从 reasoning_content 获取
            reasoning = getattr(message, 'reasoning_content', None)
            if reasoning:
                logger.info("LLM content为空，使用reasoning_content字段")
                content = reasoning
            else:
                # 尝试从 refusal 获取
                refusal = getattr(message, 'refusal', None)
                if refusal:
                    content = refusal
                else:
                    logger.warning(f"LLM返回内容为空，message字段: {dir(message)}")
                    raise ValueError("LLM返回内容为空(content=None)，模型可能不支持当前请求格式")

        # 移除 <think> 思考内容（部分模型会包含）
        if isinstance(content, str):
            content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        else:
            content = str(content).strip()
        
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )

        # 清理markdown代码块标记
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            # 尝试提取JSON部分（有些模型在JSON前后添加了额外文本）
            json_match = re.search(r'\{[\s\S]*\}', cleaned_response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned_response[:500]}")
