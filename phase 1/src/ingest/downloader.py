"""Video download and metadata extraction using yt-dlp."""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import yt_dlp


logger = logging.getLogger(__name__)


class VideoDownloader:
    """Download videos and extract metadata using yt-dlp."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def download(self, url: str, skip_if_exists: bool = True) -> Dict[str, Any]:
        """
        Download video and extract metadata.
        
        Args:
            url: YouTube video URL
            skip_if_exists: Skip download if video file already exists
            
        Returns:
            Dictionary containing paths and metadata
        """
        video_path = self.output_dir / "video.mp4"
        metadata_path = self.output_dir / "metadata.json"
        
        # Check if already downloaded
        if skip_if_exists and video_path.exists():
            logger.info(f"Video already exists at {video_path}, skipping download")
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                return {
                    "video_path": str(video_path),
                    "metadata_path": str(metadata_path),
                    "metadata": metadata,
                    "captions": self._get_existing_captions()
                }
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(self.output_dir / 'video.%(ext)s'),
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US', 'en-GB'],
            'subtitlesformat': 'vtt',
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
        }
        
        logger.info(f"Downloading video from {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and download
            info = ydl.extract_info(url, download=True)
            
            # Save metadata
            metadata = self._extract_metadata(info)
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"Video downloaded to {video_path}")
            logger.info(f"Metadata saved to {metadata_path}")
        
        # Collect caption files
        captions = self._get_existing_captions()
        
        return {
            "video_path": str(video_path),
            "metadata_path": str(metadata_path),
            "metadata": metadata,
            "captions": captions
        }
    
    def _extract_metadata(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant metadata from yt-dlp info dict."""
        metadata = {
            "id": info.get("id"),
            "title": info.get("title"),
            "description": info.get("description"),
            "duration": info.get("duration"),  # seconds
            "upload_date": info.get("upload_date"),
            "uploader": info.get("uploader"),
            "uploader_id": info.get("uploader_id"),
            "channel": info.get("channel"),
            "channel_id": info.get("channel_id"),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "tags": info.get("tags", []),
            "categories": info.get("categories", []),
            "license": info.get("license"),
            "width": info.get("width"),
            "height": info.get("height"),
            "fps": info.get("fps"),
            "resolution": info.get("resolution"),
        }
        
        # Extract chapters if available
        if "chapters" in info and info["chapters"]:
            metadata["chapters"] = [
                {
                    "title": ch.get("title"),
                    "start_time": ch.get("start_time"),
                    "end_time": ch.get("end_time")
                }
                for ch in info["chapters"]
            ]
        
        # Extract available subtitles info
        if "subtitles" in info:
            metadata["subtitles_available"] = list(info["subtitles"].keys())
        if "automatic_captions" in info:
            metadata["automatic_captions_available"] = list(info["automatic_captions"].keys())
        
        return metadata
    
    def _get_existing_captions(self) -> List[Dict[str, str]]:
        """Find all caption files in the output directory."""
        caption_files = []
        for caption_file in self.output_dir.glob("*.vtt"):
            caption_files.append({
                "path": str(caption_file),
                "filename": caption_file.name,
                "language": self._extract_language_from_filename(caption_file.name)
            })
        return caption_files
    
    @staticmethod
    def _extract_language_from_filename(filename: str) -> str:
        """Extract language code from caption filename."""
        # Expected format: video.en.vtt or video.en-US.vtt
        parts = filename.split('.')
        if len(parts) >= 3:
            return parts[-2]
        return "unknown"


def download_video(url: str, output_dir: Path, skip_if_exists: bool = True) -> Dict[str, Any]:
    """
    Convenience function to download a video.
    
    Args:
        url: YouTube video URL
        output_dir: Directory to save the video and metadata
        skip_if_exists: Skip download if video file already exists
        
    Returns:
        Dictionary containing paths and metadata
    """
    downloader = VideoDownloader(output_dir)
    return downloader.download(url, skip_if_exists)
