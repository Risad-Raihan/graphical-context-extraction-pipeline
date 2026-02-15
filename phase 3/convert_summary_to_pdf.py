#!/usr/bin/env python3
"""Convert Executive Summary markdown to PDF"""
import subprocess
import shutil
from pathlib import Path


def markdown_to_html(md_path: Path) -> str:
    """Convert markdown to HTML with styling"""
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Simple markdown to HTML conversion
    html_lines = []
    in_table = False
    
    for line in md_content.split('\n'):
        # Headers
        if line.startswith('# '):
            html_lines.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('### '):
            html_lines.append(f'<h3>{line[4:]}</h3>')
        # Horizontal rules
        elif line.strip() == '---':
            html_lines.append('<hr>')
        # Bold text
        elif '**' in line:
            # Simple bold replacement
            converted = line
            while '**' in converted:
                converted = converted.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
            html_lines.append(f'<p>{converted}</p>')
        # Lists
        elif line.strip().startswith('- '):
            html_lines.append(f'<li>{line.strip()[2:]}</li>')
        elif line.strip().startswith(('1. ', '2. ', '3. ', '4. ', '5. ')):
            html_lines.append(f'<li>{line.strip()[3:]}</li>')
        # Table detection
        elif '|' in line and not in_table:
            in_table = True
            html_lines.append('<table>')
            # Parse header
            cells = [c.strip() for c in line.split('|') if c.strip()]
            html_lines.append('<thead><tr>')
            for cell in cells:
                html_lines.append(f'<th>{cell}</th>')
            html_lines.append('</tr></thead><tbody>')
        elif '|' in line and in_table:
            if line.strip().startswith('|---'):
                continue  # Skip separator
            cells = [c.strip() for c in line.split('|') if c.strip()]
            html_lines.append('<tr>')
            for cell in cells:
                html_lines.append(f'<td>{cell}</td>')
            html_lines.append('</tr>')
        elif in_table and not '|' in line:
            in_table = False
            html_lines.append('</tbody></table>')
            html_lines.append(f'<p>{line}</p>')
        # Empty lines
        elif not line.strip():
            html_lines.append('<br>')
        # Regular text
        else:
            html_lines.append(f'<p>{line}</p>')
    
    if in_table:
        html_lines.append('</tbody></table>')
    
    html_content = '\n'.join(html_lines)
    
    # Wrap in full HTML document
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Executive Summary</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
               line-height: 1.6; max-width: 900px; margin: 40px auto; padding: 20px; color: #333; }}
        h1 {{ font-size: 2rem; margin: 2rem 0 1rem; border-bottom: 3px solid #333; padding-bottom: 0.5rem; }}
        h2 {{ font-size: 1.5rem; margin: 1.5rem 0 0.75rem; color: #444; }}
        h3 {{ font-size: 1.2rem; margin: 1rem 0 0.5rem; color: #555; }}
        p {{ margin: 0.5rem 0; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 2rem 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ padding: 0.75rem; text-align: left; border: 1px solid #ddd; }}
        th {{ background: #f5f5f5; font-weight: bold; }}
        li {{ margin: 0.25rem 0; }}
        strong {{ font-weight: 600; }}
        br {{ margin: 0.5rem 0; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
    
    return full_html


def convert_to_pdf(md_path: Path, pdf_path: Path):
    """Convert markdown to PDF via HTML and Chrome"""
    
    if not md_path.exists():
        print(f"❌ Markdown file not found: {md_path}")
        return False
    
    # Convert markdown to HTML
    print(f"Converting {md_path.name} to HTML...")
    html_content = markdown_to_html(md_path)
    
    # Save temporary HTML
    temp_html = md_path.parent / "temp_summary.html"
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Find Chrome
    chrome_commands = [
        'google-chrome-stable',
        'google-chrome',
        'chromium',
        'chromium-browser'
    ]
    
    chrome_path = None
    for cmd in chrome_commands:
        if shutil.which(cmd):
            chrome_path = cmd
            break
    
    if not chrome_path:
        print("❌ Chrome not found")
        temp_html.unlink()
        return False
    
    # Convert to PDF
    print(f"Converting to PDF using Chrome...")
    try:
        result = subprocess.run(
            [
                chrome_path,
                '--headless',
                '--disable-gpu',
                '--no-sandbox',
                '--print-to-pdf=' + str(pdf_path),
                f'file://{temp_html.absolute()}'
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Clean up temp HTML
        temp_html.unlink()
        
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            print(f"✅ PDF saved to: {pdf_path}")
            print(f"   File size: {pdf_path.stat().st_size / 1024:.1f} KB")
            return True
        else:
            print(f"❌ PDF generation failed")
            return False
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        if temp_html.exists():
            temp_html.unlink()
        return False


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    md_path = project_root / "EXECUTIVE_SUMMARY.md"
    pdf_path = project_root / "EXECUTIVE_SUMMARY.pdf"
    
    success = convert_to_pdf(md_path, pdf_path)
    exit(0 if success else 1)
