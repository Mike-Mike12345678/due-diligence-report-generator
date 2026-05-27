"""客户尽调报告生成流水线 - 串联 Research / Analysis / Report 三个 Agent"""

import json
import os
import time
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel

from agents.research import ResearchAgent
from agents.analysis import AnalysisAgent
from agents.report import ReportAgent

console = Console()


class DueDiligencePipeline:
    """尽调报告生成流水线"""

    def __init__(self, config_path: str = "config.yaml"):
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {config_path}\n"
                f"请复制 config.yaml.example 为 config.yaml 并填入 API Key。"
            )
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.research_agent = ResearchAgent(self.config)
        self.analysis_agent = AnalysisAgent(self.config)
        self.report_agent = ReportAgent(self.config)

    def run(self, company_name: str, output_dir: str = None) -> str:
        """执行完整流水线，返回生成的 PDF 路径。"""
        start_time = time.time()

        if output_dir is None:
            output_dir = self.config.get("report", {}).get("output_dir", "./output")
        os.makedirs(output_dir, exist_ok=True)

        console.print(Panel.fit(
            f"[bold]客户尽调报告生成[/bold]\n"
            f"公司: {company_name}\n"
            f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            title="[blue]Pipeline 启动[/]",
            border_style="blue",
        ))

        # Step 1: Research Agent
        console.print("\n[bold cyan]>>> Step 1/3: Research Agent - 信息搜集[/]")
        try:
            research_data = self.research_agent.run(company_name)
        except Exception as e:
            console.print(f"[bold red]Research Agent 失败: {e}[/]")
            raise SystemExit(1)

        self._save_intermediate(
            output_dir, f"{company_name}_research.json", research_data
        )

        # Step 2: Analysis Agent
        console.print("\n[bold cyan]>>> Step 2/3: Analysis Agent - 深度分析[/]")
        try:
            analysis_data = self.analysis_agent.run(research_data)
        except Exception as e:
            console.print(f"[bold red]Analysis Agent 失败: {e}[/]")
            raise SystemExit(1)

        self._save_intermediate(
            output_dir, f"{company_name}_analysis.json", analysis_data
        )

        # Step 3: Report Agent
        console.print("\n[bold cyan]>>> Step 3/3: Report Agent - 报告生成[/]")
        try:
            pdf_path = self.report_agent.run(analysis_data, company_name)
        except Exception as e:
            console.print(f"[bold red]Report Agent 失败: {e}[/]")
            raise SystemExit(1)

        elapsed = time.time() - start_time

        console.print(Panel.fit(
            f"[bold green]报告生成完成[/]\n"
            f"PDF 路径: {pdf_path}\n"
            f"总耗时: {elapsed:.1f} 秒",
            border_style="green",
        ))

        return pdf_path

    @staticmethod
    def _save_intermediate(output_dir: str, filename: str, data: dict) -> None:
        """将中间结果保存为 JSON 文件。"""
        filepath = os.path.join(output_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            console.print(f"[dim]中间结果已保存: {filepath}[/dim]")
        except Exception as e:
            console.print(f"[yellow]保存中间结果失败 ({filename}): {e}[/yellow]")
