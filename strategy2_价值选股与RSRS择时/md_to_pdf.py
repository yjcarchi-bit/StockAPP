#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将策略说明文档转换为PDF (使用reportlab)
"""

import os
import re

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError as e:
    print(f"请安装reportlab: pip install reportlab")
    print(f"错误: {e}")
    exit(1)

pdfmetrics.registerFont(TTFont('Chinese', '/System/Library/Fonts/STHeiti Medium.ttc'))


def parse_markdown_table(lines):
    """解析Markdown表格"""
    rows = []
    for line in lines:
        if line.strip().startswith('|') and not re.match(r'^\|[-:\s|]+\|$', line.strip()):
            cells = [c.strip() for c in line.strip().split('|')[1:-1]]
            if cells:
                rows.append(cells)
    return rows


def create_pdf(md_file, pdf_file):
    """将Markdown转换为PDF"""
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    doc = SimpleDocTemplate(pdf_file, pagesize=A4, 
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontName='Chinese',
        fontSize=18,
        textColor=colors.HexColor('#003366'),
        spaceAfter=12,
        spaceBefore=0
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Chinese',
        fontSize=14,
        textColor=colors.HexColor('#003366'),
        spaceAfter=8,
        spaceBefore=16
    )
    
    h3_style = ParagraphStyle(
        'H3',
        parent=styles['Heading3'],
        fontName='Chinese',
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        spaceBefore=12
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Chinese',
        fontSize=10,
        leading=14,
        spaceAfter=6
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=20,
        bulletIndent=10
    )
    
    story = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip()
        
        if not line or line.strip() == '':
            i += 1
            continue
        
        stripped = line.strip()
        
        if stripped.startswith('# '):
            story.append(Paragraph(stripped[2:], title_style))
            
        elif stripped.startswith('## '):
            story.append(Paragraph(stripped[3:], h2_style))
            
        elif stripped.startswith('### '):
            story.append(Paragraph(stripped[4:], h3_style))
            
        elif stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            i -= 1
            
            rows = parse_markdown_table(table_lines)
            if rows:
                col_count = len(rows[0])
                col_width = (A4[0] - 4*cm) / col_count
                
                table = Table(rows, colWidths=[col_width]*col_count)
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Chinese'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6e6e6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(table)
                story.append(Spacer(1, 6))
                
        elif stripped.startswith('---'):
            story.append(Spacer(1, 12))
            
        elif stripped.startswith('- ') or stripped.startswith('* '):
            text = stripped[2:]
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            story.append(Paragraph('• ' + text, bullet_style))
            
        elif len(stripped) > 0 and stripped[0].isdigit() and '. ' in stripped:
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', stripped)
            story.append(Paragraph(text, body_style))
            
        elif stripped.startswith('**Q'):
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', stripped)
            story.append(Paragraph(text, ParagraphStyle('Q', parent=body_style, textColor=colors.HexColor('#003366'))))
            
        elif stripped.startswith('A：') or stripped.startswith('A:'):
            story.append(Paragraph(stripped, body_style))
            
        else:
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', stripped)
            story.append(Paragraph(text, body_style))
        
        i += 1
    
    doc.build(story)
    print(f"PDF已生成: {pdf_file}")


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_file = os.path.join(script_dir, '策略说明文档.md')
    pdf_file = os.path.join(script_dir, '策略说明文档.pdf')
    
    if os.path.exists(md_file):
        create_pdf(md_file, pdf_file)
    else:
        print(f"文件不存在: {md_file}")
