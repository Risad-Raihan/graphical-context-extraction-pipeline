"""Export chunks to JSONL, Parquet, and JSON formats."""
import json
import logging
from pathlib import Path
from typing import List
import pandas as pd

from src.chunker import Chunk


logger = logging.getLogger(__name__)


class ChunkExporter:
    """Export chunks to various formats."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(self, chunks: List[Chunk]) -> dict:
        """Export chunks to all formats."""
        logger.info(f"Exporting {len(chunks)} chunks")
        
        output_files = {}
        
        # Export to JSON (human-readable, complete)
        json_path = self.output_dir / "chunks.json"
        self._export_json(chunks, json_path)
        output_files['json'] = str(json_path)
        
        # Export to JSONL (training-ready, one per line)
        jsonl_path = self.output_dir / "chunks.jsonl"
        self._export_jsonl(chunks, jsonl_path)
        output_files['jsonl'] = str(jsonl_path)
        
        # Export to Parquet (columnar, efficient)
        parquet_path = self.output_dir / "chunks.parquet"
        self._export_parquet(chunks, parquet_path)
        output_files['parquet'] = str(parquet_path)
        
        logger.info("Export complete")
        return output_files
    
    def _export_json(self, chunks: List[Chunk], output_path: Path):
        """Export to JSON."""
        logger.info(f"Exporting to JSON: {output_path}")
        
        chunks_data = []
        for chunk in chunks:
            chunk_dict = chunk.to_dict()
            # Include embeddings as lists for portability
            if hasattr(chunk, 'text_embedding'):
                chunk_dict['text_embedding'] = chunk.text_embedding.tolist()
            if hasattr(chunk, 'image_embedding'):
                chunk_dict['image_embedding'] = chunk.image_embedding.tolist()
            chunks_data.append(chunk_dict)
        
        with open(output_path, 'w') as f:
            json.dump(chunks_data, f, indent=2)
        
        logger.info(f"JSON export complete: {output_path.stat().st_size / 1024:.1f} KB")
    
    def _export_jsonl(self, chunks: List[Chunk], output_path: Path):
        """Export to JSONL (one chunk per line)."""
        logger.info(f"Exporting to JSONL: {output_path}")
        
        with open(output_path, 'w') as f:
            for chunk in chunks:
                chunk_dict = chunk.to_dict()
                # Include embeddings
                if hasattr(chunk, 'text_embedding'):
                    chunk_dict['text_embedding'] = chunk.text_embedding.tolist()
                if hasattr(chunk, 'image_embedding'):
                    chunk_dict['image_embedding'] = chunk.image_embedding.tolist()
                f.write(json.dumps(chunk_dict) + '\n')
        
        logger.info(f"JSONL export complete: {output_path.stat().st_size / 1024:.1f} KB")
    
    def _export_parquet(self, chunks: List[Chunk], output_path: Path):
        """Export to Parquet."""
        logger.info(f"Exporting to Parquet: {output_path}")
        
        # Prepare data for DataFrame
        records = []
        for chunk in chunks:
            record = chunk.to_dict()
            # Convert embeddings to lists
            if hasattr(chunk, 'text_embedding'):
                record['text_embedding'] = chunk.text_embedding.tolist()
            if hasattr(chunk, 'image_embedding'):
                record['image_embedding'] = chunk.image_embedding.tolist()
            records.append(record)
        
        # Create DataFrame and export
        df = pd.DataFrame(records)
        df.to_parquet(output_path, index=False, engine='pyarrow')
        
        logger.info(f"Parquet export complete: {output_path.stat().st_size / 1024:.1f} KB")


def export_chunks(chunks: List[Chunk], output_dir: Path) -> dict:
    """Convenience function to export chunks."""
    exporter = ChunkExporter(output_dir)
    return exporter.export(chunks)
