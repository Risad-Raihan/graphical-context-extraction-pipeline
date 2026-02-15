#!/usr/bin/env python3
"""
Convert HTML validation report to PDF

Usage:
    python convert_to_pdf.py XNQTWZ87K4I
"""
import sys
import argparse
from pathlib import Path


def convert_html_to_pdf(video_id: str, output_dir: Path):
    """Convert HTML report to PDF using Chrome headless"""
    html_path = output_dir / video_id / "report.html"
    pdf_path = output_dir / video_id / "report.pdf"
    
    if not html_path.exists():
        print(f"❌ HTML report not found: {html_path}")
        return False
    
    # Method 1: Try Chrome/Chromium headless (best quality, exact rendering)
    import subprocess
    import shutil
    
    chrome_commands = [
        'google-chrome-stable',
        'google-chrome',
        'chromium',
        'chromium-browser',
        'chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/google-chrome',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser'
    ]
    
    chrome_path = None
    for cmd in chrome_commands:
        if shutil.which(cmd):
            chrome_path = cmd
            break
    
    if chrome_path:
        print(f"Converting {html_path} to PDF using Chrome...")
        try:
            # Use absolute path for HTML
            abs_html_path = html_path.absolute()
            result = subprocess.run(
                [
                    chrome_path,
                    '--headless',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--print-to-pdf=' + str(pdf_path),
                    f'file://{abs_html_path}'
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                print(f"✅ PDF saved to: {pdf_path}")
                print(f"   File size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
                return True
            else:
                print(f"❌ PDF generation failed")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Chrome conversion failed: {e}")
            return False
    else:
        print("❌ Chrome/Chromium not found.")
        print("\nInstall Chrome with:")
        print("  # Arch Linux:")
        print("  sudo pacman -S chromium")
        print("\n  # Ubuntu/Debian:")
        print("  sudo apt install chromium-browser")
        return False


def main():
    parser = argparse.ArgumentParser(description="Convert HTML validation report to PDF")
    parser.add_argument("video_id", help="Video ID (e.g., XNQTWZ87K4I)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "output",
        help="Output directory (default: ./output)"
    )
    
    args = parser.parse_args()
    
    success = convert_html_to_pdf(args.video_id, args.output_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
