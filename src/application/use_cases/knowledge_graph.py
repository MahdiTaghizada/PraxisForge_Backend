"""Use case: automatic knowledge graph extraction from chat messages.

Extracts entities (technologies, components, goals, etc.) and their relationships
from conversation snippets and stores them in the project knowledge graph.
"""

from __future__ import annotations

import json
import logging
import uuid

from src.application.interfaces.llm import LLMService
from src.domain.entities.models import KnowledgeEntity, KnowledgeRelationship
from src.domain.repositories.knowledge_graph_repo import (
    KnowledgeEntityRepository,
    KnowledgeRelationshipRepository,
)
from src.domain.value_objects.enums import EntityType, RelationshipType

logger = logging.getLogger(__name__)

_VALID_ENTITY_TYPES = {e.value for e in EntityType}
_VALID_REL_TYPES = {r.value for r in RelationshipType}

_GRAPH_EXTRACTION_PROMPT = """\
You are a knowledge graph extraction engine. Given the conversation below, \
extract entities and relationships relevant to a software project.

CONVERSATION:
{conversation}

Entity types: technology, architecture_component, project_goal, module, task, person, service, database, concept
Relationship types: uses, contains, depends_on, implements, connects_to, part_of, related_to

Return ONLY valid JSON (no markdown fences):
{{
  "entities": [
    {{"name": "Entity Name", "type": "technology", "description": "Brief description"}}
  ],
  "relationships": [
    {{"source": "Entity A", "target": "Entity B", "type": "uses", "description": "How they relate"}}
  ]
}}

Rules:
- Entity names should be normalised (e.g. "FastAPI" not "fast api" or "fastapi framework")
- Only extract entities and relationships clearly stated or strongly implied
- Do not invent connections that are not in the conversation
- If nothing is extractable, return empty lists
"""


class KnowledgeGraphExtractionUseCase:
    """Extracts entities and relationships from conversations into a knowledge graph."""

    def __init__(
        self,
        llm: LLMService,
        entity_repo: KnowledgeEntityRepository,
        relationship_repo: KnowledgeRelationshipRepository,
    ) -> None:
        self._llm = llm
        self._entity_repo = entity_repo
        self._relationship_repo = relationship_repo

    async def extract_from_conversation(
        self,
        project_id: uuid.UUID,
        conversation_snippet: str,
        source_message_id: uuid.UUID | None = None,
    ) -> dict:
        """Extract and persist knowledge graph data from a conversation."""

        prompt = _GRAPH_EXTRACTION_PROMPT.format(conversation=conversation_snippet)
        raw = await self._llm.generate(prompt=prompt)

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            data = json.loads(cleaned.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Knowledge graph LLM returned unparseable JSON: %s", raw[:200])
            return {"entities_created": 0, "relationships_created": 0}

        # Process entities — deduplicate by name within project
        entity_name_map: dict[str, uuid.UUID] = {}
        entities_created = 0

        for ent_data in data.get("entities", []):
            name = ent_data.get("name", "").strip()
            ent_type = ent_data.get("type", "concept").strip()
            if not name:
                continue
            if ent_type not in _VALID_ENTITY_TYPES:
                ent_type = "concept"

            # Check for existing entity
            existing = await self._entity_repo.find_by_name(project_id, name)
            if existing:
                entity_name_map[name] = existing.id
                continue

            entity = KnowledgeEntity(
                project_id=project_id,
                name=name,
                entity_type=EntityType(ent_type),
                description=ent_data.get("description", ""),
                source_message_id=source_message_id,
            )
            created = await self._entity_repo.create(entity)
            entity_name_map[name] = created.id
            entities_created += 1

        # Process relationships
        relationships_created = 0
        for rel_data in data.get("relationships", []):
            source_name = rel_data.get("source", "").strip()
            target_name = rel_data.get("target", "").strip()
            rel_type = rel_data.get("type", "related_to").strip()

            if not source_name or not target_name:
                continue
            if rel_type not in _VALID_REL_TYPES:
                rel_type = "related_to"

            source_id = entity_name_map.get(source_name)
            target_id = entity_name_map.get(target_name)

            if not source_id or not target_id:
                continue

            relationship = KnowledgeRelationship(
                project_id=project_id,
                source_entity_id=source_id,
                target_entity_id=target_id,
                relationship_type=RelationshipType(rel_type),
                description=rel_data.get("description", ""),
                source_message_id=source_message_id,
            )
            await self._relationship_repo.create(relationship)
            relationships_created += 1

        logger.info(
            "Knowledge graph extraction: %d entities, %d relationships for project %s",
            entities_created,
            relationships_created,
            project_id,
        )

        return {
            "entities_created": entities_created,
            "relationships_created": relationships_created,
        }

    async def get_project_graph(self, project_id: uuid.UUID) -> dict:
        """Return the full knowledge graph for a project."""
        entities = await self._entity_repo.list_by_project(project_id)
        relationships = await self._relationship_repo.list_by_project(project_id)

        return {
            "entities": [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "type": str(e.entity_type),
                    "description": e.description,
                }
                for e in entities
            ],
            "relationships": [
                {
                    "id": str(r.id),
                    "source_entity_id": str(r.source_entity_id),
                    "target_entity_id": str(r.target_entity_id),
                    "type": str(r.relationship_type),
                    "description": r.description,
                }
                for r in relationships
            ],
        }

    async def get_entity_context(
        self, project_id: uuid.UUID, entity_name: str
    ) -> str:
        """Build a text context snippet about an entity and its relationships."""
        entity = await self._entity_repo.find_by_name(project_id, entity_name)
        if not entity:
            return ""

        rels = await self._relationship_repo.list_by_entity(entity.id, project_id)

        # Resolve entity names for relationships
        parts = [f"{entity.name} ({entity.entity_type}): {entity.description}"]
        for rel in rels:
            if rel.source_entity_id == entity.id:
                target = await self._entity_repo.get_by_id(rel.target_entity_id, project_id)
                if target:
                    parts.append(f"  → {rel.relationship_type} → {target.name}")
            else:
                source = await self._entity_repo.get_by_id(rel.source_entity_id, project_id)
                if source:
                    parts.append(f"  ← {rel.relationship_type} ← {source.name}")

        return "\n".join(parts)
