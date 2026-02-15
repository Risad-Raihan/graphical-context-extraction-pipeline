"""Qdrant storage for chunks."""
import logging
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
    CreateCollection,
)

from src.chunker import Chunk
from src.config import QdrantConfig


logger = logging.getLogger(__name__)


class QdrantStore:
    """Store chunks in Qdrant."""
    
    def __init__(self, config: QdrantConfig):
        self.config = config
        
        # Connect to Qdrant Cloud or local
        if config.url and config.api_key:
            logger.info(f"Connecting to Qdrant Cloud at {config.url}")
            self.client = QdrantClient(url=config.url, api_key=config.api_key)
        else:
            logger.info(f"Connecting to Qdrant at {config.host}:{config.port}")
            self.client = QdrantClient(host=config.host, port=config.port)
    
    def store(self, chunks: List[Chunk]) -> int:
        """Store chunks in Qdrant."""
        logger.info("Storing chunks in Qdrant")
        
        # Create collection if it doesn't exist
        self._create_collection(chunks)
        
        # Prepare points
        points = []
        for i, chunk in enumerate(chunks):
            point = self._chunk_to_point(chunk, i)
            points.append(point)
        
        # Upsert points
        self.client.upsert(
            collection_name=self.config.collection_name,
            points=points
        )
        
        logger.info(f"Stored {len(points)} points in Qdrant")
        
        # Verify with a sample query
        self._verify_storage()
        
        return len(points)
    
    def _create_collection(self, chunks: List[Chunk]):
        """Create Qdrant collection with multi-vector support."""
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.config.collection_name in collection_names:
            logger.info(f"Collection {self.config.collection_name} already exists")
            return
        
        # Get dimensions from first chunk
        if not chunks or not hasattr(chunks[0], 'text_embedding'):
            raise ValueError("Chunks must have embeddings before storing")
        
        text_dim = len(chunks[0].text_embedding)
        image_dim = len(chunks[0].image_embedding)
        
        logger.info(f"Creating collection {self.config.collection_name}")
        logger.info(f"  Text vector: {text_dim} dimensions")
        logger.info(f"  Image vector: {image_dim} dimensions")
        
        # Create collection with named vectors
        self.client.create_collection(
            collection_name=self.config.collection_name,
            vectors_config={
                self.config.text_vector_name: VectorParams(
                    size=text_dim,
                    distance=Distance.COSINE
                ),
                self.config.image_vector_name: VectorParams(
                    size=image_dim,
                    distance=Distance.COSINE
                )
            }
        )
        
        # Create payload indexes for efficient filtering
        logger.info("Creating payload indexes")
        
        self.client.create_payload_index(
            collection_name=self.config.collection_name,
            field_name="video_id",
            field_schema=PayloadSchemaType.KEYWORD
        )
        
        self.client.create_payload_index(
            collection_name=self.config.collection_name,
            field_name="chapter_title",
            field_schema=PayloadSchemaType.TEXT
        )
        
        self.client.create_payload_index(
            collection_name=self.config.collection_name,
            field_name="scene_id",
            field_schema=PayloadSchemaType.INTEGER
        )
        
        self.client.create_payload_index(
            collection_name=self.config.collection_name,
            field_name="t_start_ms",
            field_schema=PayloadSchemaType.INTEGER
        )
        
        self.client.create_payload_index(
            collection_name=self.config.collection_name,
            field_name="t_end_ms",
            field_schema=PayloadSchemaType.INTEGER
        )
    
    def _chunk_to_point(self, chunk: Chunk, point_id: int) -> PointStruct:
        """Convert chunk to Qdrant point."""
        # Prepare payload (all metadata except embeddings)
        payload = chunk.to_dict()
        
        # Remove embeddings from payload (they go in vectors)
        payload.pop('text_embedding', None)
        payload.pop('image_embedding', None)
        
        # Create point with named vectors
        point = PointStruct(
            id=point_id,
            vector={
                self.config.text_vector_name: chunk.text_embedding.tolist(),
                self.config.image_vector_name: chunk.image_embedding.tolist()
            },
            payload=payload
        )
        
        return point
    
    def _verify_storage(self):
        """Verify storage with a sample query."""
        try:
            # Get collection info
            collection_info = self.client.get_collection(self.config.collection_name)
            logger.info(f"Collection info: {collection_info.points_count} points")
            
            # Try a simple scroll to get first point
            points = self.client.scroll(
                collection_name=self.config.collection_name,
                limit=1
            )
            
            if points[0]:
                logger.info(f"Sample point ID: {points[0][0].id}")
                logger.info(f"Sample payload keys: {list(points[0][0].payload.keys())}")
        
        except Exception as e:
            logger.warning(f"Verification failed: {e}")


def store_in_qdrant(chunks: List[Chunk], config: QdrantConfig) -> int:
    """Convenience function to store chunks in Qdrant."""
    store = QdrantStore(config)
    return store.store(chunks)
