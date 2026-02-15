"""Q&A pair generation using Google Gemini"""
import json
from pathlib import Path
from typing import List, Dict, Any
import logging
from dataclasses import dataclass

from .loader import Chunk

logger = logging.getLogger(__name__)


@dataclass
class QAPair:
    """Question-Answer pair"""
    question: str
    answer: str
    evidence_type: str  # "spoken", "visual", "both"
    chunk_id: str
    t_start_ms: int
    t_end_ms: int
    chapter_title: str
    video_id: str


class QAGenerator:
    """Generate Q&A pairs from chunks using Gemini"""
    
    def __init__(
        self, 
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        max_pairs_per_chunk: int = 5,
        temperature: float = 0.7
    ):
        self.api_key = api_key
        self.model = model
        self.max_pairs_per_chunk = max_pairs_per_chunk
        self.temperature = temperature
        
        # Import google-genai
        try:
            from google import genai
            self.genai = genai
            # Configure client with API key
            self.client = genai.Client(api_key=api_key)
        except ImportError:
            logger.error("google-genai package not installed. Run: pip install google-genai")
            raise
    
    def generate(self, chunks: List[Chunk], video_id: str) -> List[QAPair]:
        """Generate Q&A pairs for all chunks"""
        logger.info(f"Generating Q&A pairs for {len(chunks)} chunks")
        
        all_pairs = []
        
        for i, chunk in enumerate(chunks, 1):
            try:
                logger.info(f"Processing chunk {i}/{len(chunks)}: {chunk.chunk_id}")
                pairs = self._generate_for_chunk(chunk, video_id)
                all_pairs.extend(pairs)
                logger.info(f"Generated {len(pairs)} Q&A pairs for {chunk.chunk_id}")
            except Exception as e:
                logger.error(f"Failed to generate Q&A for {chunk.chunk_id}: {e}")
        
        logger.info(f"Total Q&A pairs generated: {len(all_pairs)}")
        return all_pairs
    
    def _generate_for_chunk(self, chunk: Chunk, video_id: str) -> List[QAPair]:
        """Generate Q&A pairs for a single chunk"""
        
        # Build prompt
        prompt = self._build_prompt(chunk)
        
        # Call Gemini
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "temperature": self.temperature,
                    "max_output_tokens": 2048,
                }
            )
            
            # Parse response
            pairs = self._parse_response(response.text, chunk, video_id)
            return pairs
        
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return []
    
    def _build_prompt(self, chunk: Chunk) -> str:
        """Build prompt for Gemini"""
        
        t_start_sec = chunk.t_start_ms / 1000
        t_end_sec = chunk.t_end_ms / 1000
        
        prompt = f"""You are generating training data from a video tutorial.

Given the following content from a video segment:

Chapter: {chunk.chapter_title}
Time: {t_start_sec:.1f}s - {t_end_sec:.1f}s
Duration: {chunk.duration_sec:.1f}s

Spoken (ASR):
{chunk.asr_text if chunk.asr_text else "[No speech]"}

On Screen (OCR):
{chunk.ocr_text_cleaned if chunk.ocr_text_cleaned else "[No on-screen text]"}

Generate {self.max_pairs_per_chunk} question-answer pairs that:
1. Test understanding of the content shown/spoken in this segment
2. Include at least one question about visual/graphical content (what was shown on screen)
3. Each answer should cite whether the information was spoken, shown on screen, or both
4. Keep answers concise but accurate
5. Questions should be specific and answerable from the provided content

Output as a JSON array with this exact format:
[
  {{"question": "...", "answer": "...", "evidence_type": "spoken|visual|both"}},
  {{"question": "...", "answer": "...", "evidence_type": "spoken|visual|both"}}
]

Output ONLY the JSON array, no other text."""
        
        return prompt
    
    def _parse_response(self, response_text: str, chunk: Chunk, video_id: str) -> List[QAPair]:
        """Parse Gemini response into QAPair objects"""
        
        # Clean response text
        response_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines (markdown markers)
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        try:
            pairs_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return []
        
        # Convert to QAPair objects
        qa_pairs = []
        for pair_data in pairs_data:
            try:
                qa_pair = QAPair(
                    question=pair_data["question"],
                    answer=pair_data["answer"],
                    evidence_type=pair_data.get("evidence_type", "both"),
                    chunk_id=chunk.chunk_id,
                    t_start_ms=chunk.t_start_ms,
                    t_end_ms=chunk.t_end_ms,
                    chapter_title=chunk.chapter_title,
                    video_id=video_id
                )
                qa_pairs.append(qa_pair)
            except KeyError as e:
                logger.error(f"Missing field in Q&A pair: {e}")
        
        return qa_pairs
    
    def save_jsonl(self, qa_pairs: List[QAPair], output_path: Path):
        """Save Q&A pairs to JSONL format"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for pair in qa_pairs:
                json_str = json.dumps({
                    "question": pair.question,
                    "answer": pair.answer,
                    "evidence_type": pair.evidence_type,
                    "chunk_id": pair.chunk_id,
                    "t_start_ms": pair.t_start_ms,
                    "t_end_ms": pair.t_end_ms,
                    "chapter_title": pair.chapter_title,
                    "video_id": pair.video_id
                }, ensure_ascii=False)
                f.write(json_str + "\n")
        
        logger.info(f"Saved {len(qa_pairs)} Q&A pairs to {output_path}")
