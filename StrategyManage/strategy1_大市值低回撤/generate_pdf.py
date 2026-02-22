#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略说明文档PDF生成器 - 优化版
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import re

def register_chinese_fonts():
    font_paths = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Chinese', font_path))
                return 'Chinese'
            except:
                continue
    
    return 'Helvetica'

def create_styles(font_name):
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='ChineseTitle',
        fontName=font_name,
        fontSize=22,
        leading=28,
        alignment=1,
        spaceAfter=15,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseSubtitle',
        fontName=font_name,
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.grey,
        spaceAfter=25,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseHeading1',
        fontName=font_name,
        fontSize=15,
        leading=20,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#2c3e50'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseHeading2',
        fontName=font_name,
        fontSize=13,
        leading=18,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor('#34495e'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseHeading3',
        fontName=font_name,
        fontSize=11,
        leading=16,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor('#7f8c8d'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseBody',
        fontName=font_name,
        fontSize=10,
        leading=15,
        spaceBefore=3,
        spaceAfter=3,
        firstLineIndent=18,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseBodyNoIndent',
        fontName=font_name,
        fontSize=10,
        leading=15,
        spaceBefore=3,
        spaceAfter=3,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseQuote',
        fontName=font_name,
        fontSize=10,
        leading=15,
        leftIndent=15,
        rightIndent=15,
        spaceBefore=6,
        spaceAfter=6,
        textColor=colors.HexColor('#7f8c8d'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseBullet',
        fontName=font_name,
        fontSize=10,
        leading=15,
        leftIndent=15,
        spaceBefore=2,
        spaceAfter=2,
    ))
    
    styles.add(ParagraphStyle(
        name='TableCell',
        fontName=font_name,
        fontSize=9,
        leading=12,
        alignment=0,
    ))
    
    styles.add(ParagraphStyle(
        name='TableCellCenter',
        fontName=font_name,
        fontSize=9,
        leading=12,
        alignment=1,
    ))
    
    styles.add(ParagraphStyle(
        name='TableCellRight',
        fontName=font_name,
        fontSize=9,
        leading=12,
        alignment=2,
    ))
    
    styles.add(ParagraphStyle(
        name='TableHeader',
        fontName=font_name,
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.white,
    ))
    
    return styles

def parse_markdown_table(lines, start_idx):
    table_data = []
    idx = start_idx
    
    while idx < len(lines) and lines[idx].strip().startswith('|'):
        row = lines[idx].strip()
        cells = [cell.strip() for cell in row.split('|')[1:-1]]
        table_data.append(cells)
        idx += 1
        
        if idx < len(lines) and '---' in lines[idx]:
            idx += 1
    
    return table_data, idx

def estimate_column_widths(table_data, available_width):
    if not table_data:
        return None
    
    col_count = len(table_data[0])
    max_chars = [0] * col_count
    total_chars = 0
    
    for row in table_data:
        for i, cell in enumerate(row):
            cell_len = len(cell)
            if cell_len > max_chars[i]:
                max_chars[i] = cell_len
        total_chars += sum(len(cell) for cell in row)
    
    avg_chars = total_chars / (len(table_data) * col_count) if table_data else 10
    
    widths = []
    for i, max_char in enumerate(max_chars):
        if max_char <= 6:
            widths.append(min(2.5*cm, available_width * 0.15))
        elif max_char <= 12:
            widths.append(min(3.5*cm, available_width * 0.25))
        elif max_char <= 20:
            widths.append(min(4.5*cm, available_width * 0.35))
        else:
            widths.append(min(5.5*cm, available_width * 0.45))
    
    total_width = sum(widths)
    if total_width > available_width:
        scale = available_width / total_width
        widths = [w * scale for w in widths]
    
    return widths

def create_table(table_data, styles, available_width=16*cm):
    if not table_data:
        return None
    
    col_count = len(table_data[0])
    col_widths = estimate_column_widths(table_data, available_width)
    
    def format_cell(text, is_header=False, align='center'):
        text = text.replace('**', '')
        
        if align == 'center' or is_header:
            style = styles['TableHeader'] if is_header else styles['TableCellCenter']
        elif align == 'right':
            style = styles['TableCellRight']
        else:
            style = styles['TableCell']
        
        return Paragraph(text, style)
    
    def get_alignment(cell, col_idx, row_idx):
        if row_idx == 0:
            return 'center'
        
        cell_lower = cell.lower().strip()
        
        if re.match(r'^[\d,\.\-+%￥元]+$', cell_lower.replace(' ', '')):
            return 'right'
        
        if cell.startswith('|:') or '---' in cell:
            return 'left'
        
        if col_idx == 0:
            return 'center'
        
        return 'left'
    
    formatted_data = []
    for row_idx, row in enumerate(table_data):
        formatted_row = []
        for col_idx, cell in enumerate(row):
            align = get_alignment(cell, col_idx, row_idx)
            formatted_row.append(format_cell(cell, is_header=(row_idx == 0), align=align))
        formatted_data.append(formatted_row)
    
    style = TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Chinese'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ])
    
    if len(formatted_data) > 1:
        style.add('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db'))
        style.add('TEXTCOLOR', (0, 0), (-1, 0), colors.white)
    
    for i in range(1, len(formatted_data)):
        if i % 2 == 0:
            style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8f9fa'))
    
    table = Table(formatted_data, colWidths=col_widths)
    table.setStyle(style)
    
    return table

def parse_markdown(content, styles, font_name):
    elements = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        if line.startswith('# ') and not line.startswith('## '):
            title = line[2:].strip()
            elements.append(Paragraph(title, styles['ChineseTitle']))
            i += 1
            continue
        
        if line.startswith('## '):
            heading = line[3:].strip()
            elements.append(Spacer(1, 8))
            elements.append(Paragraph(heading, styles['ChineseHeading1']))
            i += 1
            continue
        
        if line.startswith('### '):
            heading = line[4:].strip()
            elements.append(Paragraph(heading, styles['ChineseHeading2']))
            i += 1
            continue
        
        if line.startswith('#### '):
            heading = line[5:].strip()
            elements.append(Paragraph(heading, styles['ChineseHeading3']))
            i += 1
            continue
        
        if line.startswith('> '):
            quote = line[2:].strip()
            elements.append(Paragraph(quote, styles['ChineseQuote']))
            i += 1
            continue
        
        if line.startswith('---'):
            elements.append(Spacer(1, 8))
            i += 1
            continue
        
        if line.startswith('|'):
            table_data, new_idx = parse_markdown_table(lines, i)
            if table_data:
                table = create_table(table_data, styles)
                if table:
                    elements.append(Spacer(1, 6))
                    elements.append(table)
                    elements.append(Spacer(1, 6))
            i = new_idx
            continue
        
        if line.startswith('```'):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1
            
            code_text = '\n'.join(code_lines)
            code_text = code_text.replace('┌', '+').replace('┐', '+')
            code_text = code_text.replace('└', '+').replace('┘', '+')
            code_text = code_text.replace('├', '+').replace('┤', '+')
            code_text = code_text.replace('─', '-').replace('│', '|')
            code_text = code_text.replace('↓', 'v').replace('→', '->')
            code_text = code_text.replace('✓', 'Y')
            
            for code_line in code_text.split('\n'):
                if code_line.strip():
                    elements.append(Paragraph(code_line, styles['ChineseBodyNoIndent']))
            continue
        
        if line.startswith('- ') or line.startswith('* '):
            bullet = line[2:].strip()
            bullet = bullet.replace('**', '')
            elements.append(Paragraph(f"• {bullet}", styles['ChineseBullet']))
            i += 1
            continue
        
        if line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.'):
            text = re.sub(r'^\d+\.\s*', '', line)
            text = text.replace('**', '')
            elements.append(Paragraph(text, styles['ChineseBullet']))
            i += 1
            continue
        
        text = line.replace('**', '')
        elements.append(Paragraph(text, styles['ChineseBody']))
        i += 1
    
    return elements

def generate_pdf(md_file, pdf_file):
    font_name = register_chinese_fonts()
    styles = create_styles(font_name)
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    elements = parse_markdown(content, styles, font_name)
    
    doc.build(elements)
    print(f"PDF已生成: {pdf_file}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_file = os.path.join(script_dir, '策略说明.md')
    pdf_file = os.path.join(script_dir, '策略说明.pdf')
    
    generate_pdf(md_file, pdf_file)
