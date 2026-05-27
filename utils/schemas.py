"""数据契约 — 各 Agent 之间的接口格式定义"""

# Research Agent 输出格式
RESEARCH_OUTPUT = {
    "company_name": "公司名",
    "basic_info": {
        "founded": "成立时间",
        "headquarters": "总部",
        "industry": "所属行业",
        "revenue": "营收规模（最近3年）",
        "employees": "员工规模",
        "key_products": ["核心产品/服务列表"],
        "business_segments": ["业务板块"],
        "stock_info": "上市信息（如有）",
    },
    "strategy_moves": [
        {
            "year": "年份",
            "event": "事件描述",
            "type": "类型（投资/并购/组织调整/技术路线/市场扩张/合作）",
            "significance": "重要性说明",
        }
    ],
    "ai_status": {
        "ai_products": ["已公开的AI产品/项目"],
        "ai_labs": ["AI实验室/研究中心"],
        "ai_patents": "AI相关专利/论文概况",
        "ai_investment": "AI投入方向",
        "ai_partnerships": ["AI相关合作"],
    },
    "search_log": [
        {"query": "搜索关键词", "results_count": 10}
    ],
}

# Analysis Agent 输出格式
ANALYSIS_OUTPUT = {
    "company_name": "公司名",
    "business_overview": "公司业务概览（详细分析文本，HTML格式）",
    "strategy_analysis": "近3年关键战略动向分析（详细文本，HTML格式）",
    "ai_analysis": "AI应用现状分析（详细文本，HTML格式）",
    "cooperation_points": [
        {
            "title": "合作切入点标题",
            "description": "详细描述",
            "reason": "推荐理由（结合软通能力）",
            "approach": "建议合作方式",
            "priority": "high/medium/low",
        }
    ],
    "info_gaps": ["信息缺口列表（如有的话）"],
}

# Report Agent 最终输出（传给 PDF 引擎）
REPORT_DATA = {
    "company_name": "公司名",
    "report_date": "2026-05-27",
    "chapters": [
        {
            "title": "公司业务概览",
            "number": "01",
            "sections": [
                {"subtitle": "子节标题", "content": "<p>HTML内容</p>"},
            ],
        }
    ],
    "disclaimer": "免责声明文本",
}
