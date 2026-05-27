"""Report Agent —— 接收 Analysis Agent 输出，生成最终 PDF 尽调报告"""

import os
import re
from datetime import date
from pathlib import Path

from rich.console import Console

from utils.llm_client import LLMClient
from utils.pdf_engine import PDFEngine

console = Console()

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent


class ReportAgent:
    """尽调报告生成 Agent：将分析数据转换为格式化 PDF 报告"""

    def __init__(self, config: dict):
        self.llm = LLMClient(config)
        self.pdf = PDFEngine()
        self.config = config
        self.verbose = config.get("pipeline", {}).get("verbose", False)

        # 加载 prompt 模板
        prompt_path = ROOT_DIR / "prompts" / "report.md"
        self.prompt_template = prompt_path.read_text(encoding="utf-8")

        # 按 --- 分割，提取润色和扩展两个区段
        self.polish_template = ""
        self.expand_template = ""
        sections = re.split(r"\n---\n", self.prompt_template)
        for section in sections:
            if "内容润色 Prompt" in section:
                # 提取标题之后的内容作为模板
                lines = section.strip().split("\n")
                # 跳过 "## 内容润色 Prompt" 标题行及后续空行
                content_lines = []
                skip_header = True
                for line in lines:
                    if skip_header and (line.startswith("## ") or line.strip() == ""):
                        continue
                    skip_header = False
                    content_lines.append(line)
                self.polish_template = "\n".join(content_lines).strip()
            elif "内容扩展 Prompt" in section:
                lines = section.strip().split("\n")
                content_lines = []
                skip_header = True
                for line in lines:
                    if skip_header and (line.startswith("## ") or line.strip() == ""):
                        continue
                    skip_header = False
                    content_lines.append(line)
                self.expand_template = "\n".join(content_lines).strip()

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def run(self, analysis_data: dict, company_name: str = None) -> str:
        """生成尽调 PDF 报告

        Args:
            analysis_data: Analysis Agent 的输出
            company_name: 可选覆盖公司名，默认取 analysis_data 中的值

        Returns:
            生成的 PDF 文件绝对路径
        """
        company = company_name or analysis_data.get("company_name", "未知公司")
        today = date.today().strftime("%Y-%m-%d")

        console.print(f"\n[bold cyan]===== Report Agent 启动 =====[/]")
        console.print(f"[bold]公司:[/] {company}  [bold]日期:[/] {today}")

        # 1. 构建报告数据
        console.print("\n[bold blue]Step 1:[/] 构建报告章节结构")
        report_data = self._build_report_data(analysis_data, company, today)

        # 2. 内容增强
        console.print("[bold blue]Step 2:[/] 内容增强与润色")
        report_data = self._enhance_content(report_data)

        # 3. 生成 PDF
        console.print("[bold blue]Step 3:[/] 生成 PDF")
        output_filename = f"{company}_尽调报告_{today}.pdf"
        output_path = os.path.join("output", output_filename)

        pdf_path = self.pdf.generate(
            report_data=report_data,
            output_path=output_path,
        )

        console.print(f"\n[bold green]报告已生成:[/] {pdf_path}")
        return pdf_path

    # ------------------------------------------------------------------
    # 构建报告数据
    # ------------------------------------------------------------------
    def _build_report_data(
        self, analysis_data: dict, company_name: str, report_date: str
    ) -> dict:
        """将 Analysis Agent 输出转换为 PDF 引擎所需的 report_data 格式"""

        # 第四章：合作切入点 — 合并为一个 section
        coop_parts = []
        for i, cp in enumerate(analysis_data.get("cooperation_points", []), 1):
            priority_label = {"high": "高", "medium": "中", "low": "低"}.get(
                cp.get("priority", "medium"), "中"
            )
            coop_parts.append(
                f"<h4>切入点{i}：{cp.get('title', '')}（优先级：{priority_label}）</h4>"
                f"<p>{cp.get('description', '')}</p>"
                f"<p>推荐理由：{cp.get('reason', '')}</p>"
                f"<p>建议合作方式：{cp.get('approach', '')}</p>"
            )
        coop_sections = [
            {"subtitle": "合作建议", "content": "".join(coop_parts)}
        ]

        chapters = [
            {
                "title": "公司业务概览",
                "number": "01",
                "sections": [
                    {
                        "subtitle": "公司简介与业务结构",
                        "content": analysis_data.get("business_overview", "<p>暂无数据</p>"),
                    }
                ],
            },
            {
                "title": "近三年关键战略动向",
                "number": "02",
                "sections": [
                    {
                        "subtitle": "战略动向总览",
                        "content": analysis_data.get("strategy_analysis", "<p>暂无数据</p>"),
                    }
                ],
            },
            {
                "title": "AI 应用现状分析",
                "number": "03",
                "sections": [
                    {
                        "subtitle": "AI 布局与应用",
                        "content": analysis_data.get("ai_analysis", "<p>暂无数据</p>"),
                    }
                ],
            },
            {
                "title": "与软通动力的合作切入点",
                "number": "04",
                "sections": coop_sections,
            },
        ]

        report_data = {
            "company_name": company_name,
            "report_date": report_date,
            "chapters": chapters,
            "disclaimer": (
                "本报告基于公开信息整理，仅供参考，不构成投资或商业决策建议。"
                "报告中的信息可能存在时效性差异，建议结合最新公开资料进行验证。"
            ),
        }

        # 不再添加信息缺口章节，保持报告精简

        return report_data

    # ------------------------------------------------------------------
    # 内容增强
    # ------------------------------------------------------------------
    def _enhance_content(self, report_data: dict) -> dict:
        """使用 LLM 对各章节内容进行润色和增强"""

        for chapter in report_data["chapters"]:
            chapter_title = chapter["title"]
            for section in chapter["sections"]:
                content = section["content"]
                # 去除 HTML 标签后计算纯文本字数
                plain_text = re.sub(r"<[^>]+>", "", content).strip()
                char_count = len(plain_text)

                # 短内容需要扩展，正常内容仅润色
                if char_count < 150:
                    console.print(
                        f"  [yellow]扩展[/] {chapter_title} / {section['subtitle']} "
                        f"({char_count} 字)"
                    )
                    enhanced = self._llm_expand(
                        chapter_title, section["subtitle"], content
                    )
                else:
                    console.print(
                        f"  [green]润色[/] {chapter_title} / {section['subtitle']} "
                        f"({char_count} 字)"
                    )
                    enhanced = self._llm_polish(
                        chapter_title, section["subtitle"], content
                    )

                if enhanced:
                    section["content"] = enhanced

        return report_data

    # ------------------------------------------------------------------
    # LLM 调用
    # ------------------------------------------------------------------
    def _llm_polish(
        self, chapter_title: str, section_subtitle: str, content: str
    ) -> str:
        """润色内容"""
        if self.polish_template:
            from jinja2 import Template
            rendered = Template(self.polish_template).render(
                chapter_title=chapter_title,
                section_subtitle=section_subtitle,
                content=content,
            )
            prompt = rendered
        else:
            prompt = (
                "你是一个专业的商业报告撰写专家。请对以下报告章节内容进行润色和增强：\n\n"
                f"章节：{chapter_title}\n"
                f"子节：{section_subtitle}\n"
                f"当前内容：\n{content}\n\n"
                "要求：\n"
                "1. 保持原有信息和数据不变\n"
                "2. 优化段落结构，确保逻辑清晰\n"
                "3. 适当添加过渡句和总结性表述\n"
                "4. 使用 HTML 标签格式化（h4/p/ul/li/table）\n"
                "5. 字数控制在 500-1500 字\n"
                "6. 专业、客观的语言风格\n\n"
                "请直接返回增强后的 HTML 内容，不要包含任何解释说明。"
            )

        try:
            return self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.llm.model_advanced,
            )
        except Exception as e:
            console.print(f"  [red]润色失败，保留原文: {e}[/red]")
            return content

    def _llm_expand(
        self, chapter_title: str, section_subtitle: str, content: str
    ) -> str:
        """扩展内容（针对字数不足的章节）"""
        if self.expand_template:
            from jinja2 import Template
            rendered = Template(self.expand_template).render(
                chapter_title=chapter_title,
                section_subtitle=section_subtitle,
                content=content,
            )
            prompt = rendered
        else:
            prompt = (
                "以下报告章节内容偏短，请根据已有信息进行合理扩展，"
                "补充必要的分析和说明：\n\n"
                f"章节：{chapter_title}\n"
                f"子节：{section_subtitle}\n"
                f"当前内容：\n{content}\n\n"
                "要求：\n"
                "1. 保持原有信息和核心观点不变\n"
                "2. 在不编造事实的前提下，补充合理的分析和推论\n"
                "3. 增加段落层次，每段聚焦一个要点\n"
                "4. 添加过渡句，使段落间衔接自然\n"
                "5. 在末尾添加简短的章节小结\n"
                "6. 使用 HTML 标签格式化（h4/p/ul/li/table）\n"
                "7. 扩展后字数不少于 500 字\n"
                "8. 专业、客观的语言风格\n\n"
                "请直接返回扩展后的 HTML 内容，不要包含任何解释说明。"
            )

        try:
            return self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.llm.model_advanced,
            )
        except Exception as e:
            console.print(f"  [red]扩展失败，保留原文: {e}[/red]")
            return content
