"""Research Agent — 多轮搜索，收集公司公开情报"""

import json
import re
from pathlib import Path

from jinja2 import Template
from rich.console import Console
from rich.progress import Progress

from utils.llm_client import LLMClient
from utils.search_client import SearchClient

console = Console()

# prompt 模板路径
PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "research.md"

# 各轮搜索的关键词配置
SEARCH_QUERIES = {
    1: {  # 公司基本面
        "zh": [
            "{company_name} 公司简介",
            "{company_name} 营收 年报",
            "{company_name} 业务板块",
        ],
        "en": [
            "{company_name} company overview",
            "{company_name} revenue annual report",
            "{company_name} business segments",
        ],
    },
    2: {  # 战略动向
        "zh": [
            "{company_name} 战略 2024 2025 2026",
            "{company_name} 投资 并购",
            "{company_name} 数字化转型",
        ],
        "en": [
            "{company_name} strategy 2024 2025",
            "{company_name} investment acquisition M&A",
            "{company_name} digital transformation",
        ],
    },
    3: {  # AI应用
        "zh": [
            "{company_name} 人工智能 AI",
            "{company_name} AI 大模型",
            "{company_name} 智能化 数字化",
        ],
        "en": [
            "{company_name} artificial intelligence AI",
            "{company_name} AI large language model",
            "{company_name} intelligent automation",
        ],
    },
}


class ResearchAgent:
    """信息搜集 Agent — 通过多轮搜索收集公司情报"""

    def __init__(self, config: dict):
        self.config = config
        self.llm = LLMClient(config)
        self.search = SearchClient(config)
        self.max_rounds = config.get("pipeline", {}).get("max_research_rounds", 3)
        self.verbose = config.get("pipeline", {}).get("verbose", False)

        # 加载 prompt 模板
        self._load_prompt_template()

    def _load_prompt_template(self):
        """加载 prompts/research.md 模板文件"""
        if not PROMPT_FILE.exists():
            raise FileNotFoundError(f"Prompt 模板文件不存在: {PROMPT_FILE}")
        self.prompt_text = PROMPT_FILE.read_text(encoding="utf-8")

    def _is_overseas(self, company_name: str) -> bool:
        """判断是否为海外公司（根据名称是否包含中文字符）"""
        return not bool(re.search(r'[一-鿿]', company_name))

    def _build_queries(self, round_num: int, company_name: str) -> list[str]:
        """根据轮次和公司类型生成搜索关键词"""
        lang = "en" if self._is_overseas(company_name) else "zh"
        templates = SEARCH_QUERIES.get(round_num, {}).get(lang, [])
        return [q.format(company_name=company_name) for q in templates]

    MAX_CONTENT_CHARS = 2000  # 每条搜索结果最大字符数

    def _format_search_results(self, results: list[dict]) -> str:
        """将搜索结果格式化为文本，供 LLM 阅读（截断过长内容）"""
        parts = []
        for i, item in enumerate(results, 1):
            parts.append(f"### 结果 {i}: {item['title']}")
            parts.append(f"来源: {item['url']}")
            content = item.get("raw_content") or item.get("content") or ""
            if len(content) > self.MAX_CONTENT_CHARS:
                content = content[:self.MAX_CONTENT_CHARS] + "..."
            parts.append(content)
            parts.append("")
        return "\n".join(parts)

    def _get_extraction_prompt(self, company_name: str, search_results: str) -> str:
        """从模板中提取「信息提取 Prompt」区段，并用 Jinja2 渲染"""
        # 按分隔线切分，找到信息提取 prompt 区段
        sections = self.prompt_text.split("---")
        for section in sections:
            if "信息提取 Prompt" in section:
                # 去掉区段标题行
                lines = section.strip().split("\n")
                # 找到标题行之后的内容
                body_start = 0
                for i, line in enumerate(lines):
                    if "信息提取 Prompt" in line:
                        body_start = i + 1
                        break
                body = "\n".join(lines[body_start:]).strip()
                template = Template(body)
                return template.render(
                    company_name=company_name,
                    search_results=search_results,
                )
        # 回退：使用整个模板
        template = Template(self.prompt_text)
        return template.render(
            company_name=company_name,
            search_results=search_results,
        )

    def _get_consolidation_prompt(self, company_name: str, raw_info: str) -> str:
        """从模板中提取「整理 Prompt」区段，并用 Jinja2 渲染"""
        sections = self.prompt_text.split("---")
        for section in sections:
            if "整理 Prompt" in section:
                lines = section.strip().split("\n")
                body_start = 0
                for i, line in enumerate(lines):
                    if "整理 Prompt" in line:
                        body_start = i + 1
                        break
                body = "\n".join(lines[body_start:]).strip()
                template = Template(body)
                return template.render(
                    company_name=company_name,
                    raw_info=raw_info,
                )
        # 回退
        template = Template(self.prompt_text)
        return template.render(
            company_name=company_name,
            raw_info=raw_info,
        )

    def _search_round(self, round_num: int, company_name: str) -> tuple[dict, list[dict]]:
        """执行一轮搜索：搜索 -> LLM 提取"""
        queries = self._build_queries(round_num, company_name)
        all_results = []
        search_log_entries = []

        for query in queries:
            console.print(f"  [cyan]搜索: {query}[/cyan]")
            results = self.search.search(query)
            all_results.extend(results)
            search_log_entries.append({
                "query": query,
                "results_count": len(results),
            })

        # 去重（按 URL）
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique_results.append(r)

        if not unique_results:
            console.print(f"  [yellow]第 {round_num} 轮搜索无结果[/yellow]")
            return {}, search_log_entries

        # 格式化搜索结果，交给 LLM 提取
        formatted = self._format_search_results(unique_results)
        prompt = self._get_extraction_prompt(company_name, formatted)

        messages = [{"role": "user", "content": prompt}]
        extracted = self.llm.chat_json(messages)

        if self.verbose:
            console.print(f"  [dim]第 {round_num} 轮提取完成，提取到 {len(json.dumps(extracted, ensure_ascii=False))} 字符[/dim]")

        return extracted, search_log_entries

    def run(self, company_name: str) -> dict:
        """
        主方法：执行多轮搜索并整理输出

        Args:
            company_name: 目标公司名称

        Returns:
            符合 RESEARCH_OUTPUT 格式的字典
        """
        console.print(f"\n[bold blue]===== Research Agent 启动 =====[/bold blue]")
        console.print(f"[bold]目标公司: {company_name}[/bold]")
        if self._is_overseas(company_name):
            console.print("[dim]检测到海外公司，将使用英文关键词搜索[/dim]")
        console.print(f"[dim]最大搜索轮数: {self.max_rounds}[/dim]\n")

        all_extracted = []  # 各轮提取的原始结果
        search_log = []     # 搜索日志

        # 按轮次搜索
        with Progress() as progress:
            task = progress.add_task("[green]信息搜集中...", total=self.max_rounds + 1)

            for round_num in range(1, self.max_rounds + 1):
                round_labels = {1: "公司基本面", 2: "战略动向", 3: "AI应用"}
                label = round_labels.get(round_num, f"第{round_num}轮")
                console.print(f"[bold]第 {round_num} 轮 — {label}[/bold]")

                extracted, log_entries = self._search_round(round_num, company_name)
                all_extracted.append(extracted)
                search_log.extend(log_entries)

                progress.update(task, advance=1)

            # 合并整理
            console.print("\n[bold]合并整理所有信息...[/bold]")
            raw_info = json.dumps(all_extracted, ensure_ascii=False, indent=2)

            consolidation_prompt = self._get_consolidation_prompt(company_name, raw_info)
            messages = [{"role": "user", "content": consolidation_prompt}]
            final = self.llm.chat_json(messages, model=self.llm.model_advanced)

            progress.update(task, advance=1)

        # 补充 search_log（LLM 输出中可能不含此字段）
        final["search_log"] = search_log
        # 确保公司名一致
        final["company_name"] = company_name

        console.print(f"[bold green]===== Research Agent 完成 =====[/bold green]")
        console.print(f"[dim]共执行 {len(search_log)} 次搜索，"
                      f"涵盖 {self.max_rounds} 个维度[/dim]\n")

        return final
