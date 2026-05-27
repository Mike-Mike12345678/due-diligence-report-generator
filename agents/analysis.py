"""Analysis Agent - depth analysis of Research Agent output"""

import json
from pathlib import Path

from jinja2 import Template
from rich.console import Console

from utils.llm_client import LLMClient
from utils.search_client import SearchClient

console = Console()

ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
KNOWLEDGE_DIR = ROOT_DIR / "knowledge"


class AnalysisAgent:
    """深度分析 Agent：对 Research Agent 输出进行业务、战略、AI 维度的分析"""

    def __init__(self, config: dict):
        self.config = config
        self.llm = LLMClient(config)
        self.searcher = SearchClient(config)
        self.verbose = config.get("pipeline", {}).get("verbose", False)
        self.prompts = self._load_prompts()
        self.softcom_profile = self._load_softcom_profile()

    def _load_prompts(self) -> dict:
        """从 prompts/analysis.md 加载各子 prompt，按 --- 分隔"""
        prompt_file = PROMPTS_DIR / "analysis.md"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt 模板不存在: {prompt_file}")
        text = prompt_file.read_text(encoding="utf-8")
        sections = text.split("---")
        prompts = {}
        keywords = {
            "业务概览": "business_overview",
            "战略动向": "strategy",
            "AI 应用": "ai_analysis",
            "合作切入点": "cooperation",
            "信息缺口": "info_gaps",
        }
        for section in sections:
            for kw, key in keywords.items():
                if kw in section and key not in prompts:
                    prompts[key] = section.strip()
                    break
        return prompts

    def _load_softcom_profile(self) -> str:
        """加载软通能力描述文件"""
        profile_path = KNOWLEDGE_DIR / "softcom_profile.md"
        if profile_path.exists():
            return profile_path.read_text(encoding="utf-8")
        return (
            "软通计算信息技术（集团）股份有限公司是中国领先的软件与信息技术服务商。"
            "核心能力包括：数字化转型咨询、软件工程服务、AI 与大数据解决方案、"
            "云计算与基础设施服务、企业应用开发与运维。"
            "服务覆盖金融、制造、能源、零售、医疗等多个行业。"
        )

    def run(self, research_data: dict) -> dict:
        """执行完整分析流程，返回 ANALYSIS_OUTPUT 格式的结果"""
        company = research_data.get("company_name", "未知公司")
        console.rule(f"[bold blue]Analysis Agent — {company}")

        console.print("[bold cyan]Step 1/5[/] 业务概览分析...")
        business_overview = self._analyze_business_overview(research_data)

        console.print("[bold cyan]Step 2/5[/] 战略动向分析...")
        strategy_analysis = self._analyze_strategy(research_data)

        console.print("[bold cyan]Step 3/5[/] AI 应用分析...")
        ai_analysis = self._analyze_ai(research_data)

        console.print("[bold cyan]Step 4/5[/] 合作切入点生成...")
        cooperation_points = self._generate_cooperation_points(
            research_data, business_overview, strategy_analysis, ai_analysis
        )

        console.print("[bold cyan]Step 5/5[/] 信息缺口检查...")
        info_gaps = self._check_info_gaps(research_data)

        result = {
            "company_name": company,
            "business_overview": business_overview,
            "strategy_analysis": strategy_analysis,
            "ai_analysis": ai_analysis,
            "cooperation_points": cooperation_points,
            "info_gaps": info_gaps,
        }

        console.print("[bold green]Analysis Agent 完成[/]")
        return result

    def _analyze_business_overview(self, data: dict) -> str:
        """业务概览分析 — 返回 HTML 文本"""
        prompt_template = self.prompts.get("business_overview", "")
        if not prompt_template:
            return "<p>缺少业务概览分析 prompt 模板</p>"
        rendered = Template(prompt_template).render(
            company_name=data.get("company_name", ""),
            basic_info=self._format_json(data.get("basic_info", {})),
        )
        messages = [
            {"role": "system", "content": "你是资深商业分析师，擅长企业业务分析。请用中文回复。"},
            {"role": "user", "content": rendered},
        ]
        return self.llm.chat(messages, model=self.llm.model_advanced)

    def _analyze_strategy(self, data: dict) -> str:
        """战略动向分析 — 返回 HTML 文本"""
        prompt_template = self.prompts.get("strategy", "")
        if not prompt_template:
            return "<p>缺少战略分析 prompt 模板</p>"
        moves = data.get("strategy_moves", [])
        rendered = Template(prompt_template).render(
            company_name=data.get("company_name", ""),
            strategy_moves=self._format_json(moves) if moves else "暂无战略事件数据",
        )
        messages = [
            {"role": "system", "content": "你是战略分析专家，擅长从企业事件中提炼战略逻辑。请用中文回复。"},
            {"role": "user", "content": rendered},
        ]
        return self.llm.chat(messages, model=self.llm.model_advanced)

    def _analyze_ai(self, data: dict) -> str:
        """AI 应用分析 — 返回 HTML 文本"""
        prompt_template = self.prompts.get("ai_analysis", "")
        if not prompt_template:
            return "<p>缺少 AI 分析 prompt 模板</p>"
        ai_status = data.get("ai_status", {})
        rendered = Template(prompt_template).render(
            company_name=data.get("company_name", ""),
            ai_status=self._format_json(ai_status) if ai_status else "暂无 AI 相关数据",
        )
        messages = [
            {"role": "system", "content": "你是 AI 产业分析专家，熟悉企业 AI 转型。请用中文回复。"},
            {"role": "user", "content": rendered},
        ]
        return self.llm.chat(messages, model=self.llm.model_advanced)

    def _generate_cooperation_points(self, data: dict, business_overview: str,
                                      strategy_analysis: str, ai_analysis: str) -> list:
        """合作切入点生成 — 返回 JSON 列表"""
        prompt_template = self.prompts.get("cooperation", "")
        if not prompt_template:
            return []
        rendered = Template(prompt_template).render(
            company_name=data.get("company_name", ""),
            business_overview=business_overview,
            strategy_analysis=strategy_analysis,
            ai_analysis=ai_analysis,
            softcom_profile=self.softcom_profile,
        )
        messages = [
            {"role": "system", "content": "你是战略合作顾问，擅长识别企业合作机会。请用中文回复。"},
            {"role": "user", "content": rendered},
        ]
        result = self.llm.chat_json(messages, model=self.llm.model_advanced)
        if isinstance(result, dict) and "cooperation_points" in result:
            return result["cooperation_points"]
        if isinstance(result, list):
            return result
        return []

    def _check_info_gaps(self, data: dict) -> list:
        """信息缺口检查 — 可选补充搜索"""
        prompt_template = self.prompts.get("info_gaps", "")
        if not prompt_template:
            return []
        data_summary = {
            "company_name": data.get("company_name", ""),
            "basic_info": data.get("basic_info", {}),
            "strategy_moves_count": len(data.get("strategy_moves", [])),
            "ai_status": data.get("ai_status", {}),
        }
        rendered = Template(prompt_template).render(
            all_data=self._format_json(data_summary),
        )
        messages = [
            {"role": "system", "content": "你是信息完整性审核专家。请用中文回复。"},
            {"role": "user", "content": rendered},
        ]
        try:
            result = self.llm.chat_json(messages)
        except Exception as e:
            console.print(f"[yellow]信息缺口检查失败: {e}[/yellow]")
            return []
        gaps = result.get("info_gaps", []) if isinstance(result, dict) else []
        suggestions = result.get("search_suggestions", []) if isinstance(result, dict) else []
        if gaps and suggestions and self._has_significant_gaps(data):
            self._supplementary_search(data, suggestions)
        return gaps

    def _has_significant_gaps(self, data: dict) -> bool:
        """判断是否存在关键信息缺失"""
        basic = data.get("basic_info", {})
        critical = ["revenue", "key_products", "industry"]
        missing = [f for f in critical if not basic.get(f)]
        return len(missing) >= 2

    def _supplementary_search(self, data: dict, suggestions: list) -> None:
        """根据缺口建议进行补充搜索，并将提取的信息合并回 research data"""
        company = data.get("company_name", "")
        console.print("[dim]  补充搜索: 发现关键信息缺口，尝试补充...[/dim]")
        for suggestion in suggestions[:2]:
            query = f"{company} {suggestion}"
            results = self.searcher.search(query, max_results=3)
            if not results:
                continue
            console.print(f"[dim]  补充搜索获取 {len(results)} 条结果[/dim]")

            # 格式化搜索结果，提取关键信息
            formatted = []
            for i, item in enumerate(results, 1):
                content = item.get("raw_content") or item.get("content") or ""
                formatted.append(f"### 结果 {i}: {item['title']}\n来源: {item['url']}\n{content[:1500]}\n")

            prompt = (
                f"以下是通过补充搜索获取的关于 {company} 的信息：\n\n"
                + "\n".join(formatted)
                + "\n请从中提取关键的结构化信息，以 JSON 格式返回：\n"
                '{"basic_info": {}, "strategy_moves": [], "ai_status": {}}\n'
                "只包含能从搜索结果中明确获取的字段，无法确认的不要编造。"
            )
            try:
                extracted = self.llm.chat_json(
                    [{"role": "user", "content": prompt}],
                    model=self.llm.model,
                )
                self._merge_supplementary(data, extracted)
            except Exception as e:
                console.print(f"[dim]  补充信息提取失败: {e}[/dim]")

    def _merge_supplementary(self, data: dict, extracted: dict) -> None:
        """将补充搜索提取的信息合并回 research data"""
        if not isinstance(extracted, dict):
            return
        # 合并 basic_info
        supp_basic = extracted.get("basic_info", {})
        if supp_basic:
            current = data.setdefault("basic_info", {})
            for k, v in supp_basic.items():
                if v and not current.get(k):
                    current[k] = v
        # 合并 strategy_moves
        supp_moves = extracted.get("strategy_moves", [])
        if supp_moves:
            current = data.setdefault("strategy_moves", [])
            current.extend(supp_moves)
        # 合并 ai_status
        supp_ai = extracted.get("ai_status", {})
        if supp_ai:
            current = data.setdefault("ai_status", {})
            for k, v in supp_ai.items():
                if v and not current.get(k):
                    current[k] = v

    @staticmethod
    def _format_json(obj) -> str:
        """将对象格式化为可读 JSON 字符串"""
        if isinstance(obj, (dict, list)):
            return json.dumps(obj, ensure_ascii=False, indent=2)
        return str(obj)
