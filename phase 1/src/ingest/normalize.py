"""Media normalization using ffmpeg."""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import ffmpeg


logger = logging.getLogger(__name__)


class MediaNormalizer:
    """Normalize video and audio files using ffmpeg."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def normalize(
        self,
        video_path: Path,
        audio_sample_rate: int = 16000,
        audio_channels: int = 1,
        video_fps: Optional[int] = None,
        video_codec: str = "libx264",
        video_preset: str = "medium",
        skip_if_exists: bool = True
    ) -> Dict[str, str]:
        """
        Normalize video and extract audio.
        
        Args:
            video_path: Path to input video
            audio_sample_rate: Target audio sample rate (Hz)
            audio_channels: Number of audio channels (1=mono, 2=stereo)
            video_fps: Target video FPS (None=keep original)
            video_codec: Video codec for output
            video_preset: Encoding preset for video codec
            skip_if_exists: Skip if output files already exist
            
        Returns:
            Dictionary with paths to normalized files
        """
        audio_path = self.output_dir / "audio.wav"
        video_out_path = self.output_dir / "video.mp4"
        
        # Check if already normalized
        if skip_if_exists and audio_path.exists() and video_out_path.exists():
            logger.info(f"Normalized files already exist, skipping normalization")
            return {
                "audio_path": str(audio_path),
                "video_path": str(video_out_path)
            }
        
        # Extract and normalize audio
        if not (skip_if_exists and audio_path.exists()):
            logger.info(f"Extracting audio to {audio_path}")
            self._extract_audio(video_path, audio_path, audio_sample_rate, audio_channels)
        
        # Normalize video
        if not (skip_if_exists and video_out_path.exists()):
            logger.info(f"Normalizing video to {video_out_path}")
            self._normalize_video(video_path, video_out_path, video_fps, video_codec, video_preset)
        
        return {
            "audio_path": str(audio_path),
            "video_path": str(video_out_path)
        }
    
    def _extract_audio(
        self,
        video_path: Path,
        audio_path: Path,
        sample_rate: int,
        channels: int
    ):
        """Extract audio from video and convert to WAV."""
        try:
            (
                ffmpeg
                .input(str(video_path))
                .output(
                    str(audio_path),
                    acodec='pcm_s16le',
                    ac=channels,
                    ar=sample_rate,
                    loglevel='error'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            logger.info(f"Audio extracted successfully: {audio_path}")
        except ffmpeg.Error as e:
            logger.error(f"ffmpeg error: {e.stderr.decode()}")
            raise
    
    def _normalize_video(
        self,
        input_path: Path,
        output_path: Path,
        fps: Optional[int],
        codec: str,
        preset: str
    ):
        """Normalize video to constant framerate MP4."""
        try:
            input_stream = ffmpeg.input(str(input_path))
            
            # Build output options
            output_opts = {
                'vcodec': codec,
                'preset': preset,
                'loglevel': 'error'
            }
            
            # Add FPS filter if specified
            if fps is not None:
                output_opts['r'] = fps
            
            # Copy audio stream
            output_opts['acodec'] = 'aac'
            output_opts['audio_bitrate'] = '128k'
            
            (
                input_stream
                .output(str(output_path), **output_opts)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            logger.info(f"Video normalized successfully: {output_path}")
        except ffmpeg.Error as e:
            logger.error(f"ffmpeg error: {e.stderr.decode()}")
            raise
    
    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get video information using ffprobe."""
        try:
            probe = ffmpeg.probe(str(video_path))
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            audio_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'audio'),
                None
            )
            
            info = {
                'format': probe['format'],
                'duration': float(probe['format'].get('duration', 0)),
            }
            
            if video_stream:
                info['video'] = {
                    'codec': video_stream.get('codec_name'),
                    'width': video_stream.get('width'),
                    'height': video_stream.get('height'),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                    'bitrate': video_stream.get('bit_rate')
                }
            
            if audio_stream:
                info['audio'] = {
                    'codec': audio_stream.get('codec_name'),
                    'sample_rate': audio_stream.get('sample_rate'),
                    'channels': audio_stream.get('channels'),
                    'bitrate': audio_stream.get('bit_rate')
                }
            
            return info
        except ffmpeg.Error as e:
            logger.error(f"ffprobe error: {e.stderr.decode()}")
            raise


def normalize_media(
    video_path: Path,
    output_dir: Path,
    audio_sample_rate: int = 16000,
    audio_channels: int = 1,
    video_fps: Optional[int] = None,
    video_codec: str = "libx264",
    video_preset: str = "medium",
    skip_if_exists: bool = True
) -> Dict[str, str]:
    """
    Convenience function to normalize media files.
    
    Args:
        video_path: Path to input video
        output_dir: Directory to save normalized files
        audio_sample_rate: Target audio sample rate (Hz)
        audio_channels: Number of audio channels
        video_fps: Target video FPS (None=keep original)
        video_codec: Video codec for output
        video_preset: Encoding preset
        skip_if_exists: Skip if output files already exist
        
    Returns:
        Dictionary with paths to normalized files
    """
    normalizer = MediaNormalizer(output_dir)
    return normalizer.normalize(
        video_path,
        audio_sample_rate,
        audio_channels,
        video_fps,
        video_codec,
        video_preset,
        skip_if_exists
    )
