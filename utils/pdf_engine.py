"""PDF 生成引擎 - 使用 reportlab 生成专业尽调报告 PDF"""

import os
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus.flowables import Flowable
from rich.console import Console

console = Console()
ROOT_DIR = Path(__file__).resolve().parent.parent

# 注册中文字体（CID 内置，无需系统字体）
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

PRIMARY = HexColor("#1a3a6b")
PRIMARY_LIGHT = HexColor("#2c5aa0")
TEXT_COLOR = HexColor("#333333")
LIGHT_BG = HexColor("#f5f7fa")


class _ColorBar(Flowable):
    """左侧竖色带装饰"""
    def __init__(self, width=3*mm, height=18*mm, color=PRIMARY):
        super().__init__()
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


# ---------- 样式 ----------

def _make_styles() -> dict:
    base = {"fontName": "STSong-Light", "leading": 16}
    return {
        "toc_title": ParagraphStyle("toc_title", fontSize=16, alignment=TA_CENTER,
                                     textColor=PRIMARY, spaceAfter=8, **base),
        "toc_item": ParagraphStyle("toc_item", fontSize=11, textColor=TEXT_COLOR,
                                    spaceAfter=4, **base),
        "chapter_num": ParagraphStyle("chapter_num", fontSize=10,
                                       textColor=PRIMARY_LIGHT, **base),
        "chapter_title": ParagraphStyle("chapter_title", fontSize=16,
                                         textColor=PRIMARY, spaceAfter=10, **base),
        "section_title": ParagraphStyle("section_title", fontSize=12,
                                         textColor=PRIMARY, spaceAfter=4,
                                         spaceBefore=6, **base),
        "h4": ParagraphStyle("h4", fontSize=11, textColor=PRIMARY,
                              spaceBefore=6, spaceAfter=2, **base),
        "body": ParagraphStyle("body", fontSize=10, textColor=TEXT_COLOR,
                                alignment=TA_JUSTIFY, spaceAfter=4,
                                firstLineIndent=20, **base),
        "body_no_indent": ParagraphStyle("body_no_indent", fontSize=10,
                                          textColor=TEXT_COLOR, alignment=TA_JUSTIFY,
                                          spaceAfter=4, **base),
        "li": ParagraphStyle("li", fontSize=10, textColor=TEXT_COLOR,
                              alignment=TA_JUSTIFY, spaceAfter=3,
                              leftIndent=18, bulletIndent=6, **base),
        "li2": ParagraphStyle("li2", fontSize=10, textColor=TEXT_COLOR,
                               alignment=TA_JUSTIFY, spaceAfter=3,
                               leftIndent=36, bulletIndent=24, **base),
        "li3": ParagraphStyle("li3", fontSize=10, textColor=TEXT_COLOR,
                               alignment=TA_JUSTIFY, spaceAfter=3,
                               leftIndent=54, bulletIndent=42, **base),
        "table_header": ParagraphStyle("th", fontSize=9, textColor=HexColor("#ffffff"),
                                        alignment=TA_CENTER, **base),
        "table_cell": ParagraphStyle("tc", fontSize=9, textColor=TEXT_COLOR,
                                      alignment=TA_CENTER, **base),
        "disclaimer_title": ParagraphStyle("disclaimer_title", fontSize=12,
                                            textColor=PRIMARY, spaceAfter=6, **base),
        "disclaimer_body": ParagraphStyle("disclaimer_body", fontSize=9,
                                           textColor=HexColor("#666666"),
                                           fontName="STSong-Light", leading=14),
    }


def _esc(text: str) -> str:
    """转义 reportlab Paragraph 中的特殊 XML 字符"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- HTML → reportlab Flowables ----------

def _html_to_flowables(html: str, styles: dict) -> list:
    """将 HTML 内容转为 reportlab flowable 列表"""
    if not html:
        return []

    elements = []
    # 按顶级结构拆分
    parts = re.split(r"(<table>.*?</table>)", html, flags=re.DOTALL)

    for part in parts:
        if part.startswith("<table>"):
            elements.extend(_parse_table(part, styles))
            continue
        elements.extend(_parse_blocks(part, styles))

    return elements


def _parse_blocks(html: str, styles: dict) -> list:
    elements = []
    # 用正则逐个提取块级元素
    pos = 0
    while pos < len(html):
        # 跳过空白
        m = re.match(r"\s+", html[pos:])
        if m:
            pos += m.end()
            continue

        # <h4>
        m = re.match(r"<h4>(.*?)</h4>", html[pos:], re.DOTALL)
        if m:
            text = _clean(m.group(1))
            if text:
                elements.append(Paragraph(_esc(text), styles["h4"]))
            pos += m.end()
            continue

        # <ul>
        m = re.match(r"<ul>", html[pos:])
        if m:
            pos += m.end()
            # 找到匹配的 </ul>，考虑嵌套
            depth = 1
            end = pos
            while depth > 0 and end < len(html):
                open_m = re.match(r"<ul>", html[end:])
                close_m = re.match(r"</ul>", html[end:])
                if open_m:
                    depth += 1
                    end += open_m.end()
                elif close_m:
                    depth -= 1
                    if depth == 0:
                        ul_content = html[pos:end]
                        pos = end + close_m.end()
                        break
                    end += close_m.end()
                else:
                    # 找 <li>
                    li_m = re.match(r"<li>", html[end:])
                    if li_m:
                        end += li_m.end()
                    else:
                        end += 1
            else:
                ul_content = html[pos:]
                pos = len(html)

            elements.extend(_parse_list(ul_content, 0, styles))
            continue

        # </ul> 跳过
        m = re.match(r"</ul>", html[pos:])
        if m:
            pos += m.end()
            continue

        # <li>（不在 ul 内的孤立 li）
        m = re.match(r"<li>(.*?)</li>", html[pos:], re.DOTALL)
        if m:
            text = _clean(m.group(1))
            if text:
                elements.append(Paragraph(f"- {_esc(text)}", styles["li"]))
            pos += m.end()
            continue

        # <p>
        m = re.match(r"<p>(.*?)</p>", html[pos:], re.DOTALL)
        if m:
            text = _clean(m.group(1))
            if text:
                elements.append(Paragraph(_esc(text), styles["body"]))
            pos += m.end()
            continue

        # 其他标签跳过
        m = re.match(r"<[^>]+>", html[pos:])
        if m:
            pos += m.end()
            continue

        # 纯文本
        next_tag = html.find("<", pos)
        if next_tag == -1:
            next_tag = len(html)
        text = html[pos:next_tag].strip()
        if text:
            elements.append(Paragraph(_esc(text), styles["body_no_indent"]))
        pos = next_tag

    return elements


def _parse_list(html: str, level: int, styles: dict) -> list:
    """解析 <ul> 内的 <li> 项"""
    elements = []
    style_key = ["li", "li2", "li3"][min(level, 2)]

    for m in re.finditer(r"<li>(.*?)</li>", html, re.DOTALL):
        li_content = m.group(1).strip()
        # 检查是否有嵌套 <ul>
        inner_ul = re.search(r"<ul>(.*)</ul>", li_content, re.DOTALL)
        if inner_ul:
            # li 的文本部分
            text_before = _clean(li_content[:inner_ul.start()])
            if text_before:
                elements.append(Paragraph(f"- {_esc(text_before)}", styles[style_key]))
            # 嵌套列表
            elements.extend(_parse_list(inner_ul.group(1), level + 1, styles))
        else:
            text = _clean(li_content)
            if text:
                elements.append(Paragraph(f"- {_esc(text)}", styles[style_key]))

    return elements


def _parse_table(html: str, styles: dict) -> list:
    """解析 <table> 为 reportlab Table"""
    rows = []
    for tr in re.finditer(r"<tr>(.*?)</tr>", html, re.DOTALL):
        cells = []
        for td in re.finditer(r"<td>(.*?)</td>", tr.group(1), re.DOTALL):
            cells.append(_clean(td.group(1)))
        for th in re.finditer(r"<th>(.*?)</th>", tr.group(1), re.DOTALL):
            cells.append(_clean(th.group(1)))
        if cells:
            rows.append(cells)

    if not rows:
        return []

    elements = []
    # 用 Paragraph 包装每个单元格（支持自动换行）
    num_cols = max(len(r) for r in rows)
    col_width = (A4[0] - 40 * mm) / num_cols

    data = []
    for i, row in enumerate(rows):
        styled_cells = []
        style = styles["table_header"] if i == 0 else styles["table_cell"]
        for cell in row:
            styled_cells.append(Paragraph(_esc(cell), style))
        # 补齐列数
        while len(styled_cells) < num_cols:
            styled_cells.append(Paragraph("", style))
        data.append(styled_cells)

    col_widths = [col_width] * num_cols
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#d0d0d0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    table.setStyle(TableStyle(style_cmds))

    elements.append(Spacer(1, 8))
    elements.append(table)
    elements.append(Spacer(1, 8))
    return elements


def _clean(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


# ---------- 引擎主类 ----------

class PDFEngine:
    def __init__(self):
        pass

    def generate(self, report_data: dict, output_path: str = "output/report.pdf") -> str:
        abs_output = ROOT_DIR / output_path
        abs_output.parent.mkdir(parents=True, exist_ok=True)
        console.print(f"[bold blue]生成 PDF:[/] {abs_output}")

        styles = _make_styles()
        story = []

        # 封面用回调绘制，不加入 story
        company_name = report_data.get("company_name", "")
        report_date = report_data.get("report_date", "")

        def on_first_page(canvas, doc):
            w, h = A4
            canvas.saveState()
            canvas.setFillColor(PRIMARY)
            canvas.rect(0, 0, w, h, fill=1, stroke=0)
            canvas.setFillColor(HexColor("#ffffff"))
            canvas.setFont("STSong-Light", 14)
            canvas.drawCentredString(w / 2, h - 70 * mm, "软 通 动 力")
            canvas.setStrokeColor(HexColor("#ffffff"))
            canvas.setLineWidth(0.5)
            canvas.line(w / 2 - 25 * mm, h - 78 * mm, w / 2 + 25 * mm, h - 78 * mm)
            canvas.setFont("STSong-Light", 28)
            canvas.drawCentredString(w / 2, h - 95 * mm, "客户尽调报告")
            canvas.setFont("STSong-Light", 22)
            canvas.drawCentredString(w / 2, h - 120 * mm, company_name)
            canvas.setFillColor(HexColor("#c8d2e6"))
            canvas.setFont("STSong-Light", 11)
            canvas.drawCentredString(w / 2, h - 195 * mm, f"报告日期：{report_date}")
            canvas.drawCentredString(w / 2, h - 205 * mm, "软通动力信息技术（集团）股份有限公司")
            canvas.restoreState()

        def on_later_pages(canvas, doc):
            canvas.saveState()
            canvas.setFont("STSong-Light", 9)
            canvas.setFillColor(HexColor("#999999"))
            canvas.drawCentredString(A4[0] / 2, 15 * mm, f"— {doc.page} —")
            canvas.restoreState()

        # 封面占第一页，内容从第二页开始
        story.append(Spacer(1, 1))  # 占位
        story.append(PageBreak())

        # 目录（紧接内容，不单独换页）
        story.append(Paragraph("目  录", styles["toc_title"]))
        story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=8))
        for ch in report_data.get("chapters", []):
            num = ch.get("number", "")
            title = ch.get("title", "")
            story.append(Paragraph(f"<b>{num}</b>&nbsp;&nbsp;&nbsp;{title}", styles["toc_item"]))
        story.append(Spacer(1, 12))

        # 章节
        for ch in report_data.get("chapters", []):
            story.append(Paragraph(ch.get("number", ""), styles["chapter_num"]))
            story.append(Paragraph(ch.get("title", ""), styles["chapter_title"]))
            story.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#d0d0d0"),
                                     spaceAfter=4))

            for sec in ch.get("sections", []):
                story.append(Paragraph(sec.get("subtitle", ""), styles["section_title"]))
                story.append(HRFlowable(width="100%", thickness=0.2,
                                         color=HexColor("#e0e0e0"), spaceAfter=3))
                story.extend(_html_to_flowables(sec.get("content", ""), styles))
                story.append(Spacer(1, 3))

            story.append(Spacer(1, 6))

        # 免责声明（不换页，紧跟内容）
        disclaimer = report_data.get("disclaimer", "")
        if disclaimer:
            story.append(Spacer(1, 6))
            story.append(Paragraph("免责声明", styles["disclaimer_title"]))
            story.append(Paragraph(_esc(disclaimer), styles["disclaimer_body"]))

        doc = SimpleDocTemplate(
            str(abs_output),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=22 * mm,
            bottomMargin=22 * mm,
        )
        doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        console.print(f"[bold green]完成:[/] {abs_output}")
        return str(abs_output)
