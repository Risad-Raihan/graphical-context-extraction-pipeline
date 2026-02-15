"""Scene detection and segmentation using PySceneDetect."""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from scenedetect import open_video, SceneManager, ContentDetector


logger = logging.getLogger(__name__)


class SceneDetector:
    """Detect scene changes in video."""
    
    def __init__(
        self,
        threshold: float = 27.0,
        min_scene_len: float = 0.3
    ):
        """
        Initialize scene detector.
        
        Args:
            threshold: ContentDetector threshold (lower = more sensitive)
            min_scene_len: Minimum scene length in seconds
        """
        self.threshold = threshold
        self.min_scene_len = min_scene_len
    
    def detect(
        self,
        video_path: Path,
        output_dir: Path,
        skip_if_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Detect scenes in video.
        
        Args:
            video_path: Path to video file
            output_dir: Directory to save scene data
            skip_if_exists: Skip if output already exists
            
        Returns:
            Dictionary containing scene information
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        scenes_json_path = output_dir / "scenes.json"
        
        # Check if already processed
        if skip_if_exists and scenes_json_path.exists():
            logger.info(f"Scenes already detected at {scenes_json_path}, skipping")
            with open(scenes_json_path, 'r') as f:
                return json.load(f)
        
        logger.info(f"Detecting scenes in {video_path}")
        
        # Open video
        video = open_video(str(video_path))
        
        # Create scene manager
        scene_manager = SceneManager()
        scene_manager.add_detector(
            ContentDetector(
                threshold=self.threshold,
                min_scene_len=int(self.min_scene_len * video.frame_rate)
            )
        )
        
        # Detect scenes
        scene_manager.detect_scenes(video)
        scene_list = scene_manager.get_scene_list()
        
        logger.info(f"Detected {len(scene_list)} scenes")
        
        # Convert to our format (milliseconds)
        scenes = []
        for i, (start_time, end_time) in enumerate(scene_list):
            scene_data = {
                "scene_id": i,
                "start_ms": int(start_time.get_seconds() * 1000),
                "end_ms": int(end_time.get_seconds() * 1000),
                "start_frame": start_time.get_frames(),
                "end_frame": end_time.get_frames(),
                "duration_ms": int((end_time.get_seconds() - start_time.get_seconds()) * 1000),
            }
            scenes.append(scene_data)
        
        result = {
            "video_path": str(video_path),
            "total_scenes": len(scenes),
            "detection_threshold": self.threshold,
            "min_scene_len": self.min_scene_len,
            "scenes": scenes
        }
        
        # Save to JSON
        with open(scenes_json_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Scene data saved to {scenes_json_path}")
        
        return result


def detect_scenes(
    video_path: Path,
    output_dir: Path,
    threshold: float = 27.0,
    min_scene_len: float = 0.3,
    skip_if_exists: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to detect scenes.
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save output
        threshold: Detection threshold
        min_scene_len: Minimum scene length in seconds
        skip_if_exists: Skip if output exists
        
    Returns:
        Dictionary containing scene information
    """
    detector = SceneDetector(threshold, min_scene_len)
    return detector.detect(video_path, output_dir, skip_if_exists)
