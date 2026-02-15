"""Keyframe extraction with blur detection and smart sampling."""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import cv2
import numpy as np


logger = logging.getLogger(__name__)


class KeyframeExtractor:
    """Extract keyframes from video based on scene changes and content."""
    
    def __init__(
        self,
        blur_threshold: float = 100.0,
        long_scene_threshold: float = 30.0,
        long_scene_sample_interval: float = 5.0,
        pixel_delta_threshold: float = 0.15
    ):
        """
        Initialize keyframe extractor.
        
        Args:
            blur_threshold: Laplacian variance threshold (higher = sharper)
            long_scene_threshold: Scenes longer than this get extra sampling (seconds)
            long_scene_sample_interval: Interval for sampling long scenes (seconds)
            pixel_delta_threshold: Fraction of pixels that must change for delta sampling
        """
        self.blur_threshold = blur_threshold
        self.long_scene_threshold = long_scene_threshold
        self.long_scene_sample_interval = long_scene_sample_interval
        self.pixel_delta_threshold = pixel_delta_threshold
    
    def extract(
        self,
        video_path: Path,
        scenes_data: Dict[str, Any],
        output_dir: Path,
        skip_if_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Extract keyframes from video based on scene data.
        
        Args:
            video_path: Path to video file
            scenes_data: Scene detection results
            output_dir: Directory to save keyframes
            skip_if_exists: Skip if output already exists
            
        Returns:
            Dictionary containing keyframe information
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        keyframes_json_path = output_dir.parent / "keyframes.json"
        
        # Check if already processed
        if skip_if_exists and keyframes_json_path.exists():
            logger.info(f"Keyframes already extracted at {keyframes_json_path}, skipping")
            with open(keyframes_json_path, 'r') as f:
                return json.load(f)
        
        logger.info(f"Extracting keyframes from {video_path}")
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Video: {fps:.2f} fps, {total_frames} frames")
        
        keyframes = []
        frame_id = 0
        
        # Process each scene
        for scene in scenes_data["scenes"]:
            scene_id = scene["scene_id"]
            start_ms = scene["start_ms"]
            end_ms = scene["end_ms"]
            duration_ms = scene["duration_ms"]
            duration_s = duration_ms / 1000.0
            
            logger.info(f"Processing scene {scene_id}: {start_ms}ms - {end_ms}ms")
            
            # Extract first sharp frame after scene start
            first_frame = self._extract_first_sharp_frame(
                cap, start_ms, fps, output_dir, frame_id, scene_id
            )
            
            if first_frame:
                keyframes.append(first_frame)
                frame_id += 1
            
            # For long scenes, extract additional keyframes
            if duration_s > self.long_scene_threshold:
                additional_frames = self._extract_long_scene_frames(
                    cap, start_ms, end_ms, fps, output_dir, frame_id, scene_id
                )
                keyframes.extend(additional_frames)
                frame_id += len(additional_frames)
        
        cap.release()
        
        result = {
            "video_path": str(video_path),
            "total_keyframes": len(keyframes),
            "blur_threshold": self.blur_threshold,
            "keyframes": keyframes
        }
        
        # Save to JSON
        with open(keyframes_json_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Extracted {len(keyframes)} keyframes, saved to {keyframes_json_path}")
        
        return result
    
    def _extract_first_sharp_frame(
        self,
        cap: cv2.VideoCapture,
        start_ms: int,
        fps: float,
        output_dir: Path,
        frame_id: int,
        scene_id: int
    ) -> Optional[Dict[str, Any]]:
        """Extract first sharp frame after scene start."""
        start_frame = int((start_ms / 1000.0) * fps)
        
        # Try up to 10 frames after scene start
        for offset in range(10):
            frame_num = start_frame + offset
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # Check blur
            blur_score = self._calculate_blur_score(frame)
            
            if blur_score >= self.blur_threshold:
                # Save keyframe
                timestamp_ms = int((frame_num / fps) * 1000)
                filename = f"frame_{frame_id:05d}.jpg"
                filepath = output_dir / filename
                cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                return {
                    "frame_id": frame_id,
                    "scene_id": scene_id,
                    "timestamp_ms": timestamp_ms,
                    "frame_number": frame_num,
                    "filename": filename,
                    "path": str(filepath),
                    "blur_score": float(blur_score),
                    "width": frame.shape[1],
                    "height": frame.shape[0]
                }
        
        logger.warning(f"No sharp frame found for scene {scene_id}")
        return None
    
    def _extract_long_scene_frames(
        self,
        cap: cv2.VideoCapture,
        start_ms: int,
        end_ms: int,
        fps: float,
        output_dir: Path,
        start_frame_id: int,
        scene_id: int
    ) -> List[Dict[str, Any]]:
        """Extract additional frames from long scenes."""
        keyframes = []
        frame_id = start_frame_id
        
        # Sample at regular intervals
        current_ms = start_ms + int(self.long_scene_sample_interval * 1000)
        last_frame = None
        
        while current_ms < end_ms:
            frame_num = int((current_ms / 1000.0) * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if not ret:
                current_ms += int(self.long_scene_sample_interval * 1000)
                continue
            
            # Check blur
            blur_score = self._calculate_blur_score(frame)
            
            # Check if content changed significantly from last frame
            content_changed = True
            if last_frame is not None:
                content_changed = self._has_significant_change(last_frame, frame)
            
            if blur_score >= self.blur_threshold and content_changed:
                # Save keyframe
                filename = f"frame_{frame_id:05d}.jpg"
                filepath = output_dir / filename
                cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                keyframes.append({
                    "frame_id": frame_id,
                    "scene_id": scene_id,
                    "timestamp_ms": current_ms,
                    "frame_number": frame_num,
                    "filename": filename,
                    "path": str(filepath),
                    "blur_score": float(blur_score),
                    "width": frame.shape[1],
                    "height": frame.shape[0]
                })
                
                frame_id += 1
                last_frame = frame.copy()
            
            current_ms += int(self.long_scene_sample_interval * 1000)
        
        return keyframes
    
    def _calculate_blur_score(self, frame: np.ndarray) -> float:
        """Calculate blur score using Laplacian variance."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return variance
    
    def _has_significant_change(self, frame1: np.ndarray, frame2: np.ndarray) -> bool:
        """Check if two frames have significant visual difference."""
        # Resize for faster comparison
        small1 = cv2.resize(frame1, (320, 180))
        small2 = cv2.resize(frame2, (320, 180))
        
        # Calculate absolute difference
        diff = cv2.absdiff(small1, small2)
        
        # Count changed pixels
        threshold = 30  # Pixel difference threshold
        changed_pixels = np.sum(diff > threshold)
        total_pixels = small1.shape[0] * small1.shape[1] * small1.shape[2]
        
        change_ratio = changed_pixels / total_pixels
        
        return change_ratio >= self.pixel_delta_threshold


def extract_keyframes(
    video_path: Path,
    scenes_data: Dict[str, Any],
    output_dir: Path,
    blur_threshold: float = 100.0,
    long_scene_threshold: float = 30.0,
    long_scene_sample_interval: float = 5.0,
    pixel_delta_threshold: float = 0.15,
    skip_if_exists: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to extract keyframes.
    
    Args:
        video_path: Path to video file
        scenes_data: Scene detection results
        output_dir: Directory to save keyframes
        blur_threshold: Blur detection threshold
        long_scene_threshold: Long scene threshold in seconds
        long_scene_sample_interval: Sampling interval for long scenes
        pixel_delta_threshold: Pixel change threshold
        skip_if_exists: Skip if output exists
        
    Returns:
        Dictionary containing keyframe information
    """
    extractor = KeyframeExtractor(
        blur_threshold,
        long_scene_threshold,
        long_scene_sample_interval,
        pixel_delta_threshold
    )
    return extractor.extract(video_path, scenes_data, output_dir, skip_if_exists)
