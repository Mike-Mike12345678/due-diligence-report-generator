"""客户尽调报告生成器 CLI 入口"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from pipeline import DueDiligencePipeline

console = Console()

VERSION = "1.0.0"
BANNER = (
    f"[bold blue]客户尽调报告生成器[/]  v{VERSION}\n"
    f"[dim]输入公司名，输出尽调初稿 PDF[/]"
)


@click.command()
@click.option("--company", "-c", required=True, help="目标公司名称")
@click.option("--config", default="config.yaml", help="配置文件路径")
@click.option("--output", "-o", default="./output", help="输出目录")
@click.option("--verbose", "-v", is_flag=True, help="显示详细日志")
def main(company: str, config: str, output: str, verbose: bool):
    """客户尽调报告生成器 - 输入公司名，输出尽调初稿 PDF"""
    console.print(Panel.fit(BANNER, border_style="blue"))

    config_path = Path(config)
    if not config_path.exists():
        console.print(
            "\n[bold red]配置文件不存在:[/] " + str(config_path) + "\n"
            "[yellow]请复制 config.yaml.example 为 config.yaml 并填入 API Key：[/]\n"
            "[dim]  cp config.yaml.example config.yaml\n"
            "  # 然后编辑 config.yaml，填入你的 API Key[/]\n"
        )
        sys.exit(1)

    try:
        pipeline = DueDiligencePipeline(config_path=str(config_path))
    except FileNotFoundError as e:
        console.print(f"\n[bold red]{e}[/]")
        sys.exit(1)

    if verbose:
        pipeline.config.setdefault("pipeline", {})["verbose"] = True

    try:
        pdf_path = pipeline.run(company_name=company, output_dir=output)
        console.print(f"\n[bold green]完成！报告路径: {pdf_path}[/]")
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"\n[bold red]流水线执行失败: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
