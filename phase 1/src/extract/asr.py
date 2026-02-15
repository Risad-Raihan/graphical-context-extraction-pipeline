"""Automatic Speech Recognition with word-level timestamps."""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import torch
from faster_whisper import WhisperModel
import whisperx


logger = logging.getLogger(__name__)


class ASRProcessor:
    """Process audio to generate transcripts with word-level timestamps."""
    
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        batch_size: int = 16
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.batch_size = batch_size
        self.model = None
        
    def process(
        self,
        audio_path: Path,
        output_dir: Path,
        align: bool = True,
        diarize: bool = False,
        skip_if_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Process audio file to generate transcript with timestamps.
        
        Args:
            audio_path: Path to audio file (WAV format)
            output_dir: Directory to save output files
            align: Whether to perform word-level alignment with WhisperX
            diarize: Whether to perform speaker diarization
            skip_if_exists: Skip if output already exists
            
        Returns:
            Dictionary containing transcript data and paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        asr_json_path = output_dir / "asr.json"
        transcript_path = output_dir / "transcript.txt"
        
        # Check if already processed
        if skip_if_exists and asr_json_path.exists():
            logger.info(f"ASR output already exists at {asr_json_path}, skipping")
            with open(asr_json_path, 'r') as f:
                result = json.load(f)
            return result
        
        logger.info(f"Starting ASR processing for {audio_path}")
        
        # Step 1: Transcribe with faster-whisper
        logger.info("Step 1: Transcribing with Whisper...")
        whisper_result = self._transcribe_whisper(audio_path)
        
        # Step 2: Align with WhisperX if requested
        if align:
            logger.info("Step 2: Aligning with WhisperX...")
            whisper_result = self._align_whisperx(audio_path, whisper_result)
        
        # Step 3: Diarize if requested
        if diarize:
            logger.info("Step 3: Performing speaker diarization...")
            whisper_result = self._diarize_whisperx(audio_path, whisper_result)
        
        # Prepare output
        result = {
            "audio_path": str(audio_path),
            "model": self.model_size,
            "segments": whisper_result["segments"],
            "language": whisper_result.get("language", "en"),
            "aligned": align,
            "diarized": diarize
        }
        
        # Save JSON output
        with open(asr_json_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Save human-readable transcript
        transcript_text = self._format_transcript(result["segments"])
        with open(transcript_path, 'w') as f:
            f.write(transcript_text)
        
        logger.info(f"ASR complete. Output saved to {asr_json_path}")
        
        return result
    
    def _transcribe_whisper(self, audio_path: Path) -> Dict[str, Any]:
        """Transcribe audio using faster-whisper."""
        if self.model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
        
        segments, info = self.model.transcribe(
            str(audio_path),
            beam_size=5,
            word_timestamps=True,
            vad_filter=True
        )
        
        # Convert segments to list with millisecond timestamps
        segment_list = []
        for segment in segments:
            segment_dict = {
                "start": int(segment.start * 1000),  # Convert to milliseconds
                "end": int(segment.end * 1000),
                "text": segment.text.strip(),
            }
            
            # Add word-level timestamps if available
            if hasattr(segment, 'words') and segment.words:
                segment_dict["words"] = [
                    {
                        "word": word.word,
                        "start": int(word.start * 1000),
                        "end": int(word.end * 1000),
                        "probability": word.probability
                    }
                    for word in segment.words
                ]
            
            segment_list.append(segment_dict)
        
        return {
            "segments": segment_list,
            "language": info.language,
            "duration": info.duration
        }
    
    def _align_whisperx(self, audio_path: Path, whisper_result: Dict[str, Any]) -> Dict[str, Any]:
        """Improve timestamp alignment using WhisperX."""
        try:
            # Load audio
            audio = whisperx.load_audio(str(audio_path))
            
            # Load alignment model
            model_a, metadata = whisperx.load_align_model(
                language_code=whisper_result.get("language", "en"),
                device=self.device
            )
            
            # Prepare segments for alignment (convert back to seconds)
            segments_for_align = [
                {
                    "start": seg["start"] / 1000.0,
                    "end": seg["end"] / 1000.0,
                    "text": seg["text"]
                }
                for seg in whisper_result["segments"]
            ]
            
            # Perform alignment
            result_aligned = whisperx.align(
                segments_for_align,
                model_a,
                metadata,
                audio,
                self.device,
                return_char_alignments=False
            )
            
            # Convert aligned segments back to milliseconds
            aligned_segments = []
            for seg in result_aligned["segments"]:
                segment_dict = {
                    "start": int(seg["start"] * 1000),
                    "end": int(seg["end"] * 1000),
                    "text": seg["text"].strip(),
                }
                
                # Add aligned word timestamps
                if "words" in seg:
                    segment_dict["words"] = [
                        {
                            "word": word["word"],
                            "start": int(word["start"] * 1000),
                            "end": int(word["end"] * 1000),
                            "score": word.get("score", 1.0)
                        }
                        for word in seg["words"]
                    ]
                
                aligned_segments.append(segment_dict)
            
            whisper_result["segments"] = aligned_segments
            
        except Exception as e:
            logger.warning(f"WhisperX alignment failed: {e}. Using original timestamps.")
        
        return whisper_result
    
    def _diarize_whisperx(self, audio_path: Path, whisper_result: Dict[str, Any]) -> Dict[str, Any]:
        """Perform speaker diarization using WhisperX."""
        try:
            # Load diarization model
            diarize_model = whisperx.DiarizationPipeline(
                use_auth_token=None,  # Can use HuggingFace token if needed
                device=self.device
            )
            
            # Load audio
            audio = whisperx.load_audio(str(audio_path))
            
            # Perform diarization
            diarize_segments = diarize_model(audio)
            
            # Assign speakers to segments
            result_with_speakers = whisperx.assign_word_speakers(
                diarize_segments,
                whisper_result["segments"]
            )
            
            # Update segments with speaker information
            for seg in result_with_speakers["segments"]:
                if "speaker" in seg:
                    # Find corresponding segment in our result
                    seg_start_ms = int(seg["start"] * 1000)
                    for our_seg in whisper_result["segments"]:
                        if our_seg["start"] == seg_start_ms:
                            our_seg["speaker"] = seg["speaker"]
                            break
            
        except Exception as e:
            logger.warning(f"Diarization failed: {e}. Proceeding without speaker labels.")
        
        return whisper_result
    
    def _format_transcript(self, segments: List[Dict[str, Any]]) -> str:
        """Format segments into readable transcript."""
        lines = []
        for seg in segments:
            start_time = self._format_timestamp(seg["start"])
            end_time = self._format_timestamp(seg["end"])
            speaker = seg.get("speaker", "")
            speaker_prefix = f"[{speaker}] " if speaker else ""
            
            lines.append(f"[{start_time} -> {end_time}] {speaker_prefix}{seg['text']}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_timestamp(ms: int) -> str:
        """Format milliseconds as HH:MM:SS.mmm"""
        seconds = ms / 1000
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def process_asr(
    audio_path: Path,
    output_dir: Path,
    model_size: str = "large-v3",
    device: str = "cuda",
    compute_type: str = "float16",
    batch_size: int = 16,
    align: bool = True,
    diarize: bool = False,
    skip_if_exists: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to process ASR.
    
    Args:
        audio_path: Path to audio file
        output_dir: Directory to save outputs
        model_size: Whisper model size
        device: Device to use (cuda/cpu)
        compute_type: Compute type for inference
        batch_size: Batch size for processing
        align: Whether to perform alignment
        diarize: Whether to perform diarization
        skip_if_exists: Skip if output exists
        
    Returns:
        Dictionary containing transcript data
    """
    processor = ASRProcessor(model_size, device, compute_type, batch_size)
    return processor.process(audio_path, output_dir, align, diarize, skip_if_exists)
