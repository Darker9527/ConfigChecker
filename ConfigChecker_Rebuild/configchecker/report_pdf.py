# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from html import escape
from .models import CheckTask, CheckResult


def write_pdf_report(task: CheckTask, results: list[CheckResult], out_dir: str | Path) -> Path:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.graphics.shapes import Drawing, Rect, String
    except ImportError as e:
        raise RuntimeError('缺少 reportlab，请执行：python -m pip install reportlab') from e

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{task.name}_{task.id or "new"}.pdf'

    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    font = 'STSong-Light'
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('cnTitle', parent=styles['Title'], fontName=font, fontSize=18, alignment=TA_CENTER)
    head_style = ParagraphStyle('cnHead', parent=styles['Heading2'], fontName=font, fontSize=13)
    cell_style = ParagraphStyle('cnCell', parent=styles['Normal'], fontName=font, fontSize=8, leading=11)

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    story = [Paragraph('配置核查报告', title_style), Spacer(1, 8)]

    def p(v):
        return Paragraph(escape(str(v or '')), cell_style)

    meta = [
        [p('任务名称'), p(task.name), p('设备类型'), p(task.devtype)],
        [p('设备品牌'), p(task.brand), p('检查项数量'), p(len(results))],
        [p('配置文件'), p(task.config_path), p('生成时间'), p(task.created_at)],
    ]
    t = Table(meta, colWidths=[25*mm, 55*mm, 25*mm, 65*mm])
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.3, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.extend([t, Spacer(1, 8), Paragraph('结果汇总', head_style)])

    counts = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    summary = [[p('状态'), p('数量')]] + [[p(k), p(v)] for k, v in counts.items()]
    t = Table(summary, colWidths=[50*mm, 30*mm])
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.3, colors.grey), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E8EEF7'))]))
    story.extend([t, Spacer(1, 8), Paragraph('风险统计图', head_style)])

    risk_counts = {'高风险': 0, '中风险': 0, '低风险': 0}
    for r in results:
        if r.risk in risk_counts:
            risk_counts[r.risk] += 1
    max_count = max(risk_counts.values()) or 1
    drawing = Drawing(170*mm, 45*mm)
    palette = {'高风险': colors.HexColor('#B91C1C'), '中风险': colors.HexColor('#D97706'), '低风险': colors.HexColor('#059669')}
    x0, y0 = 18*mm, 8*mm
    bar_w, gap = 28*mm, 20*mm
    for idx, risk in enumerate(['高风险', '中风险', '低风险']):
        val = risk_counts[risk]
        h = (val / max_count) * 28*mm
        x = x0 + idx * (bar_w + gap)
        drawing.add(Rect(x, y0, bar_w, h, fillColor=palette[risk], strokeColor=None))
        drawing.add(String(x + bar_w/2, y0 - 5*mm, risk, fontName=font, fontSize=8, textAnchor='middle'))
        drawing.add(String(x + bar_w/2, y0 + h + 2*mm, str(val), fontName=font, fontSize=8, textAnchor='middle'))
    story.extend([drawing, Spacer(1, 8), Paragraph('检查项明细', head_style)])

    data = [[p('检查项'), p('风险'), p('状态'), p('证据'), p('整改建议')]]
    for r in results:
        data.append([p(r.baseline_name), p(r.risk), p(r.status), p(r.evidence), p(r.suggestion)])
    t = Table(data, colWidths=[36*mm, 18*mm, 18*mm, 58*mm, 50*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)
    doc.build(story)
    return path
