"""Generate HTML validation report"""
from pathlib import Path
import base64
import logging
from typing import Dict, List
from datetime import datetime

from .loader import VideoData, Chunk
from .validator import ValidationReport

logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """Generate self-contained HTML report with validation results"""
    
    def generate(
        self, 
        video_data: VideoData, 
        validation_report: ValidationReport,
        annotated_keyframes: Dict[str, Path],
        output_path: Path
    ):
        """Generate HTML report"""
        logger.info(f"Generating HTML report for {video_data.video_id}")
        
        html = self._build_html(video_data, validation_report, annotated_keyframes)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"HTML report saved to {output_path}")
    
    def _build_html(
        self, 
        video_data: VideoData, 
        report: ValidationReport,
        annotated_keyframes: Dict[str, Path]
    ) -> str:
        """Build complete HTML document"""
        
        # Build sections
        summary_html = self._build_summary_dashboard(video_data, report)
        timeline_html = self._build_timeline_strip(video_data, report)
        chunks_html = self._build_chunk_details(video_data, annotated_keyframes)
        gaps_html = self._build_gaps_section(report)
        
        # Combine into full HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extraction Validation Report - {video_data.video_id}</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        <h1>Extraction Validation Report</h1>
        <p class="subtitle">Video ID: {video_data.video_id}</p>
        <p class="subtitle">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        {summary_html}
        {timeline_html}
        {chunks_html}
        {gaps_html}
    </div>
</body>
</html>"""
        
        return html
    
    def _build_summary_dashboard(self, video_data: VideoData, report: ValidationReport) -> str:
        """Build compact summary dashboard"""
        
        # Pass/fail verdict
        verdict = "✅ PASS" if report.overall_coverage_pct >= 90 else "⚠️ PARTIAL" if report.overall_coverage_pct >= 70 else "❌ FAIL"
        verdict_class = "pass" if report.overall_coverage_pct >= 90 else "partial" if report.overall_coverage_pct >= 70 else "fail"
        
        html = f"""
        <section class="summary">
            <h2>Summary</h2>
            <div class="verdict {verdict_class}">{verdict}</div>
            <div class="stats-grid">
                <div class="stat">
                    <div class="stat-label">Video Title</div>
                    <div class="stat-value">{video_data.metadata.title}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Duration</div>
                    <div class="stat-value">{video_data.metadata.duration_sec:.1f}s</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Coverage</div>
                    <div class="stat-value">{report.overall_coverage_pct:.1f}%</div>
                </div>
                <div class="stat">
                    <div class="stat-label">ASR Segments</div>
                    <div class="stat-value">{report.num_total_asr_segments}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Scenes</div>
                    <div class="stat-value">{len(video_data.scenes)}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Keyframes</div>
                    <div class="stat-value">{report.num_total_keyframes}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">OCR Blocks</div>
                    <div class="stat-value">{report.num_total_ocr_blocks}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Chunks</div>
                    <div class="stat-value">{report.num_total_chunks}</div>
                </div>
            </div>
        </section>
        """
        
        return html
    
    def _build_timeline_strip(self, video_data: VideoData, report: ValidationReport) -> str:
        """Build timeline visualization strip"""
        
        duration_ms = int(video_data.metadata.duration_sec * 1000)
        
        # Build timeline bars
        chapter_bars = []
        for ch in video_data.metadata.chapters:
            start_pct = (ch.start_ms / duration_ms) * 100
            width_pct = ((ch.end_ms - ch.start_ms) / duration_ms) * 100
            chapter_bars.append(f'<div class="timeline-bar chapter" style="left: {start_pct}%; width: {width_pct}%;" title="{ch.title}"></div>')
        
        # Scene markers
        scene_markers = []
        for scene in video_data.scenes:
            pos_pct = (scene.start_ms / duration_ms) * 100
            scene_markers.append(f'<div class="timeline-marker scene" style="left: {pos_pct}%;" title="Scene {scene.idx}"></div>')
        
        # Keyframe markers
        keyframe_markers = []
        for kf in video_data.keyframes:
            pos_pct = (kf.timestamp_ms / duration_ms) * 100
            keyframe_markers.append(f'<div class="timeline-marker keyframe" style="left: {pos_pct}%;" title="Keyframe @ {kf.timestamp_ms/1000:.1f}s"></div>')
        
        # Gap highlights
        gap_bars = []
        for gap in report.keyframe_gaps:
            start_pct = (gap.start_ms / duration_ms) * 100
            width_pct = ((gap.end_ms - gap.start_ms) / duration_ms) * 100
            gap_bars.append(f'<div class="timeline-bar gap" style="left: {start_pct}%; width: {width_pct}%;" title="Gap: {gap.duration_sec:.1f}s"></div>')
        
        html = f"""
        <section class="timeline">
            <h2>Timeline</h2>
            <div class="timeline-container">
                <div class="timeline-track">
                    {''.join(chapter_bars)}
                    {''.join(gap_bars)}
                    {''.join(scene_markers)}
                    {''.join(keyframe_markers)}
                </div>
            </div>
            <div class="timeline-legend">
                <span class="legend-item"><span class="legend-color chapter"></span> Chapters</span>
                <span class="legend-item"><span class="legend-color scene"></span> Scenes</span>
                <span class="legend-item"><span class="legend-color keyframe"></span> Keyframes</span>
                <span class="legend-item"><span class="legend-color gap"></span> Gaps</span>
            </div>
        </section>
        """
        
        return html
    
    def _build_chunk_details(self, video_data: VideoData, annotated_keyframes: Dict[str, Path]) -> str:
        """Build chunk-by-chunk detail section"""
        
        chunks_html = []
        
        for chunk in video_data.chunks:
            # Get annotated keyframes for this chunk
            chunk_keyframes = []
            for kf_path in chunk.keyframe_paths:
                # Try multiple path variants
                variants = [
                    kf_path,
                    str(Path(kf_path)),
                    str(Path(kf_path).name),
                ]
                
                for variant in variants:
                    if variant in annotated_keyframes:
                        annotated_path = annotated_keyframes[variant]
                        img_b64 = self._image_to_base64(annotated_path)
                        chunk_keyframes.append(f'<img src="data:image/jpeg;base64,{img_b64}" alt="Keyframe" class="keyframe-img">')
                        break
                else:
                    # Try finding by filename
                    kf_name = Path(kf_path).name
                    for k, v in annotated_keyframes.items():
                        if Path(k).name == kf_name or Path(v).name.replace('_annotated', '') == kf_name.replace('.jpg', ''):
                            img_b64 = self._image_to_base64(v)
                            chunk_keyframes.append(f'<img src="data:image/jpeg;base64,{img_b64}" alt="Keyframe" class="keyframe-img">')
                            break
            
            keyframes_html = ''.join(chunk_keyframes) if chunk_keyframes else '<p class="no-data">No keyframes</p>'
            
            # Format text
            asr_text = chunk.asr_text if chunk.asr_text else '<em>No speech</em>'
            ocr_text = chunk.ocr_text_cleaned if chunk.ocr_text_cleaned else '<em>No OCR text</em>'
            
            chunk_html = f"""
            <div class="chunk">
                <h3>{chunk.chunk_id}</h3>
                <div class="chunk-meta">
                    <span>Chapter: {chunk.chapter_title}</span>
                    <span>Time: {chunk.t_start_ms/1000:.1f}s - {chunk.t_end_ms/1000:.1f}s ({chunk.duration_sec:.1f}s)</span>
                    <span>ASR Confidence: {chunk.asr_confidence_avg:.2f}</span>
                    <span>OCR Confidence: {chunk.ocr_confidence_avg:.2f}</span>
                </div>
                
                <div class="chunk-content">
                    <div class="chunk-section">
                        <h4>Keyframes (OCR Overlay)</h4>
                        <div class="keyframes-grid">
                            {keyframes_html}
                        </div>
                    </div>
                    
                    <div class="chunk-section">
                        <h4>Spoken (ASR)</h4>
                        <p class="text-content">{asr_text}</p>
                    </div>
                    
                    <div class="chunk-section">
                        <h4>On Screen (OCR Cleaned)</h4>
                        <p class="text-content">{ocr_text}</p>
                    </div>
                </div>
            </div>
            """
            
            chunks_html.append(chunk_html)
        
        html = f"""
        <section class="chunks">
            <h2>Chunk Details</h2>
            {''.join(chunks_html)}
        </section>
        """
        
        return html
    
    def _build_gaps_section(self, report: ValidationReport) -> str:
        """Build extraction gaps/issues section"""
        
        # Keyframe gaps
        kf_gaps_html = []
        for gap in report.keyframe_gaps:
            kf_gaps_html.append(f"""
            <div class="issue {gap.severity}">
                <strong>Keyframe Gap ({gap.severity})</strong>: 
                {gap.start_ms/1000:.1f}s - {gap.end_ms/1000:.1f}s ({gap.duration_sec:.1f}s)
            </div>
            """)
        
        # Quality flags
        flags_html = []
        for flag in report.quality_flags[:20]:  # Limit to top 20
            flags_html.append(f"""
            <div class="issue {flag.severity}">
                <strong>{flag.flag_type} ({flag.severity})</strong>: 
                {flag.description} - {Path(flag.location).name}
            </div>
            """)
        
        html = f"""
        <section class="gaps">
            <h2>Extraction Gaps & Issues</h2>
            
            <h3>Keyframe Gaps ({len(report.keyframe_gaps)})</h3>
            <div class="issues-list">
                {''.join(kf_gaps_html) if kf_gaps_html else '<p class="no-data">No significant keyframe gaps</p>'}
            </div>
            
            <h3>Quality Flags ({len(report.quality_flags)})</h3>
            <div class="issues-list">
                {''.join(flags_html) if flags_html else '<p class="no-data">No quality issues detected</p>'}
            </div>
        </section>
        """
        
        return html
    
    def _image_to_base64(self, image_path: Path) -> str:
        """Convert image to base64 string"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _get_css(self) -> str:
        """Get CSS styles for report"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        h2 { font-size: 1.5rem; margin: 2rem 0 1rem; border-bottom: 2px solid #333; padding-bottom: 0.5rem; }
        h3 { font-size: 1.2rem; margin: 1.5rem 0 0.5rem; }
        h4 { font-size: 1rem; margin: 1rem 0 0.5rem; color: #666; }
        .subtitle { color: #666; margin-bottom: 0.5rem; }
        
        /* Summary */
        .summary { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .verdict { font-size: 2rem; font-weight: bold; margin: 1rem 0; text-align: center; padding: 1rem; border-radius: 8px; }
        .verdict.pass { background: #d4edda; color: #155724; }
        .verdict.partial { background: #fff3cd; color: #856404; }
        .verdict.fail { background: #f8d7da; color: #721c24; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-top: 1rem; }
        .stat { padding: 1rem; background: #f8f9fa; border-radius: 4px; text-align: center; }
        .stat-label { font-size: 0.85rem; color: #666; margin-bottom: 0.5rem; }
        .stat-value { font-size: 1.5rem; font-weight: bold; color: #333; }
        
        /* Timeline */
        .timeline { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 2rem; }
        .timeline-container { height: 80px; background: #e9ecef; border-radius: 4px; position: relative; margin: 1rem 0; }
        .timeline-track { position: relative; height: 100%; }
        .timeline-bar { position: absolute; height: 30%; top: 35%; border-radius: 2px; }
        .timeline-bar.chapter { background: #007bff; opacity: 0.3; }
        .timeline-bar.gap { background: #dc3545; opacity: 0.5; }
        .timeline-marker { position: absolute; width: 2px; height: 60%; top: 20%; }
        .timeline-marker.scene { background: #6c757d; }
        .timeline-marker.keyframe { background: #28a745; }
        .timeline-legend { display: flex; gap: 1rem; margin-top: 1rem; }
        .legend-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; }
        .legend-color { width: 20px; height: 12px; border-radius: 2px; }
        .legend-color.chapter { background: #007bff; opacity: 0.3; }
        .legend-color.scene { background: #6c757d; width: 2px; height: 20px; }
        .legend-color.keyframe { background: #28a745; width: 2px; height: 20px; }
        .legend-color.gap { background: #dc3545; opacity: 0.5; }
        
        /* Chunks */
        .chunks { margin-top: 2rem; }
        .chunk { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }
        .chunk-meta { display: flex; gap: 1rem; flex-wrap: wrap; margin: 0.5rem 0 1rem; font-size: 0.9rem; color: #666; }
        .chunk-content { display: grid; gap: 1rem; }
        .chunk-section { padding: 1rem; background: #f8f9fa; border-radius: 4px; }
        .keyframes-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-top: 0.5rem; }
        .keyframe-img { width: 100%; height: auto; border-radius: 4px; border: 1px solid #dee2e6; }
        .text-content { margin-top: 0.5rem; white-space: pre-wrap; }
        .no-data { color: #999; font-style: italic; }
        
        /* Gaps */
        .gaps { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 2rem; }
        .issues-list { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 1rem; }
        .issue { padding: 0.75rem; border-radius: 4px; border-left: 4px solid; }
        .issue.high { background: #f8d7da; border-color: #dc3545; }
        .issue.medium { background: #fff3cd; border-color: #ffc107; }
        .issue.low { background: #d1ecf1; border-color: #17a2b8; }
        """
