"""LLM prompt 模板复用模块

提取 SVS 商机计划生成路由中重复出现的 prompt 公共骨架，保持各路由向后兼容。
"""


def build_svs_opportunity_prompt(context, section_name, field_name, methodology,
                                 sections_spec, word_count):
    """构造 SVS 商机计划部分生成 prompt（4 个商机计划路由共用）

    Args:
        context: 项目上下文文本（由 _build_project_context 生成）
        section_name: 商机计划部分名（如"客户背景与需求"）
        field_name: JSON 输出字段名（如"customer_background"）
        methodology: 生成要求中的方法论描述（如"基于SVS的3-3-3分析法"）
        sections_spec: 写作要求中的小节列表多行字符串（不带末尾换行）
        word_count: 字数要求（如"300-500字"）

    Returns:
        完整 prompt 字符串
    """
    return f"""你是B2B销售数字孪生系统的销售策略顾问，精通SVS（Solution Value Selling）与Challenge Sales方法论。请基于以下项目信息，生成商机计划中的"{section_name}"部分。

{context}

# 生成要求
请生成"{section_name}"部分，{methodology}。

# 输出格式
严格输出以下JSON结构：
{{
  "{field_name}": "在这里写入真实的{section_name}内容"
}}

# {field_name} 写作要求
- 字数：{word_count}
- 必须用分点排版，使用"【】"标记小节标题，使用"•"做要点列表
{sections_spec}

- 内容必须具体、基于上方项目信息，禁止空话套话
- 禁止把上面的写作要求作为内容返回，必须写真实的分析内容
- 语言为中文
- 只输出JSON，不要其他内容"""
