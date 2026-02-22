#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown转PDF转换器 - 使用reportlab
支持中文、表格等格式
"""

import os
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


def register_chinese_fonts():
    """注册中文字体"""
    font_paths = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Chinese', font_path, subfontIndex=0))
                return 'Chinese'
            except Exception:
                continue
    
    return 'Helvetica'


def parse_markdown_table(lines):
    """解析Markdown表格"""
    rows = []
    for line in lines:
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            cells = [cell.strip() for cell in line[1:-1].split('|')]
            if all(c.replace('-', '').replace(':', '') == '' for c in cells):
                continue
            rows.append(cells)
    return rows


def create_styles(font_name):
    """创建样式"""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='ChineseTitle',
        fontName=font_name,
        fontSize=20,
        leading=28,
        textColor=colors.HexColor('#1a5276'),
        spaceAfter=20,
        alignment=TA_CENTER,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseH1',
        fontName=font_name,
        fontSize=18,
        leading=26,
        textColor=colors.HexColor('#1a5276'),
        spaceBefore=20,
        spaceAfter=12,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseH2',
        fontName=font_name,
        fontSize=14,
        leading=20,
        textColor=colors.HexColor('#2874a6'),
        spaceBefore=15,
        spaceAfter=10,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseH3',
        fontName=font_name,
        fontSize=12,
        leading=18,
        textColor=colors.HexColor('#1a5276'),
        spaceBefore=12,
        spaceAfter=8,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseH4',
        fontName=font_name,
        fontSize=11,
        leading=16,
        textColor=colors.HexColor('#2e86ab'),
        spaceBefore=10,
        spaceAfter=6,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseBody',
        fontName=font_name,
        fontSize=10,
        leading=16,
        textColor=colors.HexColor('#333333'),
        spaceBefore=4,
        spaceAfter=4,
        alignment=TA_JUSTIFY,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseQuote',
        fontName=font_name,
        fontSize=10,
        leading=16,
        textColor=colors.HexColor('#555555'),
        leftIndent=20,
        spaceBefore=8,
        spaceAfter=8,
        borderPadding=5,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseBullet',
        fontName=font_name,
        fontSize=10,
        leading=16,
        textColor=colors.HexColor('#333333'),
        leftIndent=15,
        spaceBefore=2,
        spaceAfter=2,
    ))
    
    return styles


def clean_text(text):
    """清理文本中的特殊字符"""
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
    
    emoji_map = {
        '🎯': '[目标]', '📊': '[图表]', '📖': '[说明]', '📌': '[重点]',
        '💡': '[提示]', '⚠️': '[警告]', '📝': '[笔记]', '📎': '[附件]',
        '❓': '[问题]', '📈': '[上涨]', '📉': '[下跌]',
    }
    for emoji, replacement in emoji_map.items():
        text = text.replace(emoji, replacement)
    
    text = text.replace('**', '')
    text = text.replace('*', '')
    
    return text


def convert_markdown_to_pdf(md_file_path: str, output_pdf_path: str = None):
    """将Markdown文件转换为PDF"""
    if output_pdf_path is None:
        output_pdf_path = md_file_path.replace('.md', '.pdf')
    
    font_name = register_chinese_fonts()
    styles = create_styles(font_name)
    
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    
    story = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        if line.startswith('# ') and not line.startswith('## '):
            text = clean_text(line[2:])
            story.append(Paragraph(text, styles['ChineseTitle']))
            story.append(Spacer(1, 10))
        
        elif line.startswith('## '):
            text = clean_text(line[3:])
            story.append(Spacer(1, 10))
            story.append(Paragraph(text, styles['ChineseH1']))
        
        elif line.startswith('### '):
            text = clean_text(line[4:])
            story.append(Paragraph(text, styles['ChineseH2']))
        
        elif line.startswith('#### '):
            text = clean_text(line[5:])
            story.append(Paragraph(text, styles['ChineseH3']))
        
        elif line.startswith('| ') and '|' in line:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            i -= 1
            
            rows = parse_markdown_table(table_lines)
            if rows:
                col_count = len(rows[0])
                col_width = (doc.width - 10) / col_count
                
                table_data = []
                for row in rows:
                    cleaned_row = [Paragraph(clean_text(cell), styles['ChineseBody']) for cell in row]
                    table_data.append(cleaned_row)
                
                table = Table(table_data, colWidths=[col_width] * col_count)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('TOPPADDING', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    ('TOPPADDING', (0, 1), (-1, -1), 6),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                story.append(Spacer(1, 8))
                story.append(KeepTogether(table))
                story.append(Spacer(1, 8))
        
        elif line.startswith('> '):
            text = clean_text(line[2:])
            story.append(Paragraph(text, styles['ChineseQuote']))
        
        elif line.startswith('- ') or line.startswith('* '):
            text = clean_text(line[2:])
            story.append(Paragraph(f"• {text}", styles['ChineseBullet']))
        
        elif line.startswith('---'):
            story.append(Spacer(1, 10))
        
        elif re.match(r'^\d+\.', line):
            text = re.sub(r'^\d+\.\s*', '', line)
            text = clean_text(text)
            num = re.match(r'^(\d+)\.', line).group(1)
            story.append(Paragraph(f"{num}. {text}", styles['ChineseBullet']))
        
        else:
            text = clean_text(line)
            if text:
                story.append(Paragraph(text, styles['ChineseBody']))
        
        i += 1
    
    print(f"正在生成PDF: {output_pdf_path}")
    doc.build(story)
    print(f"PDF生成完成: {output_pdf_path}")
    
    return output_pdf_path


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_file = os.path.join(script_dir, '策略说明文档.md')
    pdf_file = os.path.join(script_dir, '策略说明文档.pdf')
    
    convert_markdown_to_pdf(md_file, pdf_file)
