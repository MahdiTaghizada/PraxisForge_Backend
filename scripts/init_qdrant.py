#!/usr/bin/env python3
"""
Qdrant Collection Initialization Script

Creates the 'praxisforge' collection with proper vector configuration
and payload indexes for efficient querying.

Usage:
    python scripts/init_qdrant.py

Requirements:
    - Qdrant running on localhost:6333 (or QDRANT_URL env var)
    - qdrant-client package installed
"""
from __future__ import annotations

import asyncio
import os
import sys

from qdrant_client import QdrantClient, models

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "praxisforge")
VECTOR_SIZE = 768  # Gemini text-embedding-004 dimension


def init_qdrant() -> None:
    """Initialize Qdrant collection with indexes."""
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL)

    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]

    if COLLECTION_NAME in collection_names:
        print(f"Collection '{COLLECTION_NAME}' already exists.")
        info = client.get_collection(COLLECTION_NAME)
        print(f"  - Points count: {info.points_count}")
        print(f"  - Vector size: {info.config.params.vectors.size}")
        return

    print(f"Creating collection '{COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    )

    # Create payload indexes for efficient filtering
    print("Creating payload indexes...")

    # Index on project_id (most common filter)
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="project_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    print("  - Created index: project_id (keyword)")

    # Index on file_id for file-specific queries
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="file_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    print("  - Created index: file_id (keyword)")

    # Index on chunk_type for filtering by content type
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="chunk_type",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    print("  - Created index: chunk_type (keyword)")

    print(f"\n✓ Collection '{COLLECTION_NAME}' initialized successfully!")
    print(f"  - Vector dimension: {VECTOR_SIZE}")
    print(f"  - Distance metric: Cosine")
    print(f"  - Payload indexes: project_id, file_id, chunk_type")


def check_health() -> bool:
    """Check Qdrant connectivity."""
    try:
        client = QdrantClient(url=QDRANT_URL)
        collections = client.get_collections()
        return True
    except Exception as e:
        print(f"Cannot connect to Qdrant: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if not check_health():
        print("\nMake sure Qdrant is running. Start it with:")
        print("  docker compose up qdrant -d")
        sys.exit(1)

    init_qdrant()
