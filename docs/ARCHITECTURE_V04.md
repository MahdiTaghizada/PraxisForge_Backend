# PraxisForge v0.4.0 — Architecture Extension

## Three New Major Features

### Feature 1: Multimodal AI Processing
### Feature 2: Knowledge Graph Memory
### Feature 3: AI Project Brain

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                           │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌───────────────────┐  │
│  │ Chat     │ │ Files    │ │ Knowledge    │ │ Brain             │  │
│  │ Router   │ │ Router   │ │ Graph Router │ │ Router            │  │
│  │ (v2)     │ │ (v2)     │ │ (new)        │ │ (new)             │  │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘ └───────┬───────────┘  │
│       │             │              │                 │              │
│  ┌────┴─────┐       │              │           ┌─────┴──────────┐  │
│  │Documents │       │              │           │ Summary Router │  │
│  │ Router   │       │              │           │ (existing)     │  │
│  │ (new)    │       │              │           └────────────────┘  │
│  └────┬─────┘       │              │                               │
└───────┼─────────────┼──────────────┼───────────────────────────────┘
        │             │              │
┌───────┼─────────────┼──────────────┼───────────────────────────────┐
│       │      APPLICATION LAYER     │                               │
│       │             │              │                               │
│  ┌────┴──────────┐  │  ┌───────────┴───────────┐                   │
│  │ Multimodal    │  │  │ Knowledge Graph       │                   │
│  │ Processing    │  │  │ Extraction UseCase    │                   │
│  │ UseCase       │  │  └───────────────────────┘                   │
│  └───────────────┘  │                                              │
│                     │  ┌───────────────────────────────────────┐   │
│  ┌───────────────┐  │  │         PROJECT BRAIN                 │   │
│  │ RAG Chat      │  │  │  ┌─────────────────────────────────┐ │   │
│  │ UseCase       ├──┼──┤  │ Context Builder                 │ │   │
│  └───────────────┘  │  │  │  - Facts (by category)          │ │   │
│                     │  │  │  - Tech Stack                   │ │   │
│  ┌───────────────┐  │  │  │  - Architecture Components     │ │   │
│  │ Smart         │  │  │  │  - Tasks & Deadlines            │ │   │
│  │ Extraction    │  │  │  │  - Knowledge Graph              │ │   │
│  │ UseCase       │  │  │  │  - Document Analyses            │ │   │
│  └───────────────┘  │  │  │  - Chat History                 │ │   │
│                     │  │  │  - Vector Search Results         │ │   │
│                     │  │  └─────────────────────────────────┘ │   │
│                     │  └───────────────────────────────────────┘   │
└─────────────────────┼─────────────────────────────────────────────┘
                      │
┌─────────────────────┼─────────────────────────────────────────────┐
│              DOMAIN LAYER                                         │
│                                                                   │
│  Entities:                    Repository Interfaces:              │
│  ┌──────────────────────┐    ┌──────────────────────────────┐    │
│  │ KnowledgeEntity      │    │ KnowledgeEntityRepository    │    │
│  │ KnowledgeRelationship│    │ KnowledgeRelationshipRepo    │    │
│  │ DocumentAnalysis     │    │ DocumentAnalysisRepository   │    │
│  │ (+ existing models)  │    │ (+ existing repos)           │    │
│  └──────────────────────┘    └──────────────────────────────┘    │
│                                                                   │
│  New Enums: EntityType, RelationshipType,                        │
│             DocumentProcessingStatus                              │
└───────────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────┼─────────────────────────────────────────────┐
│            INFRASTRUCTURE LAYER                                   │
│                                                                   │
│  ┌────────────────────┐  ┌────────────────────────────────────┐  │
│  │ PostgreSQL          │  │ External Services                  │  │
│  │  - knowledge_       │  │  ┌──────────────┐ ┌────────────┐  │  │
│  │    entities         │  │  │Gemini Vision │ │Text Extract│  │  │
│  │  - knowledge_       │  │  │Service       │ │Service     │  │  │
│  │    relationships    │  │  │(multimodal)  │ │(OCR + PDF) │  │  │
│  │  - document_        │  │  └──────────────┘ └────────────┘  │  │
│  │    analyses         │  │  ┌──────────────┐ ┌────────────┐  │  │
│  │                     │  │  │Gemini LLM    │ │Groq LLM   │  │  │
│  └────────────────────┘  │  └──────────────┘ └────────────┘  │  │
│                           └────────────────────────────────────┘  │
│  ┌────────────────────┐  ┌────────────────────────────────────┐  │
│  │ Qdrant Vector DB   │  │ Optional Services                  │  │
│  │  - document chunks  │  │  ┌──────────┐ ┌────────────────┐  │  │
│  │  - fact chunks      │  │  │ MinIO    │ │ Redis Cache    │  │  │
│  │  - analysis chunks  │  │  │ (files)  │ │ (optional)     │  │  │
│  └────────────────────┘  │  └──────────┘ └────────────────┘  │  │
│                           └────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

---

## Database Schema (New Tables)

```sql
-- Knowledge Graph: Entities
CREATE TABLE knowledge_entities (
    id              UUID PRIMARY KEY,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            VARCHAR(512) NOT NULL,
    entity_type     VARCHAR(100) NOT NULL,   -- technology, architecture_component, project_goal, module, task, person, service, database, concept
    description     TEXT DEFAULT '',
    properties      JSON DEFAULT '{}',
    source_message_id UUID,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_knowledge_entities_project_id ON knowledge_entities(project_id);
CREATE INDEX ix_knowledge_entities_entity_type ON knowledge_entities(entity_type);

-- Knowledge Graph: Relationships
CREATE TABLE knowledge_relationships (
    id                  UUID PRIMARY KEY,
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_entity_id    UUID NOT NULL REFERENCES knowledge_entities(id) ON DELETE CASCADE,
    target_entity_id    UUID NOT NULL REFERENCES knowledge_entities(id) ON DELETE CASCADE,
    relationship_type   VARCHAR(100) NOT NULL,  -- uses, contains, depends_on, implements, connects_to, part_of, related_to
    description         TEXT DEFAULT '',
    confidence          FLOAT DEFAULT 1.0,
    source_message_id   UUID,
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_knowledge_relationships_project_id ON knowledge_relationships(project_id);
CREATE INDEX ix_knowledge_relationships_source_entity_id ON knowledge_relationships(source_entity_id);
CREATE INDEX ix_knowledge_relationships_target_entity_id ON knowledge_relationships(target_entity_id);

-- Document Analysis (multimodal processing results)
CREATE TABLE document_analyses (
    id                  UUID PRIMARY KEY,
    file_id             UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    extracted_text      TEXT DEFAULT '',
    ai_analysis         TEXT DEFAULT '',
    content_type        VARCHAR(100) DEFAULT 'document',  -- image, diagram, pdf, document
    processing_status   VARCHAR(50) DEFAULT 'pending',    -- pending, extracting_text, analyzing, embedding, ready, failed
    metadata_json       JSON DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_document_analyses_file_id ON document_analyses(file_id);
CREATE INDEX ix_document_analyses_project_id ON document_analyses(project_id);
```

---

## New Services

| Service | Layer | Purpose |
|---------|-------|---------|
| `GeminiVisionService` | Infrastructure | Analyze images/diagrams using Gemini's multimodal capabilities |
| `TextExtractionService` | Infrastructure | Extract text from PDFs (PyMuPDF) and images (Tesseract OCR) |
| `MultimodalProcessingUseCase` | Application | Orchestrate the full file processing pipeline: extract → analyze → embed → store |
| `KnowledgeGraphExtractionUseCase` | Application | Extract entities and relationships from conversations using LLM |
| `ProjectBrainUseCase` | Application | Build comprehensive project context from all data sources before AI response |

---

## New Endpoints

### Knowledge Graph
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/projects/{id}/knowledge-graph/` | Full knowledge graph (entities + relationships) |
| `GET` | `/api/v1/projects/{id}/knowledge-graph/entities` | List entities (optional `?entity_type=` filter) |
| `POST` | `/api/v1/projects/{id}/knowledge-graph/entities` | Create entity manually |
| `DELETE` | `/api/v1/projects/{id}/knowledge-graph/entities/{entity_id}` | Delete entity |
| `POST` | `/api/v1/projects/{id}/knowledge-graph/relationships` | Create relationship |
| `DELETE` | `/api/v1/projects/{id}/knowledge-graph/relationships/{rel_id}` | Delete relationship |

### Project Brain
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/projects/{id}/brain/chat` | Chat with full Project Brain context |
| `GET` | `/api/v1/projects/{id}/brain/summary` | Get structured brain summary |

### Document Analysis
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/projects/{id}/documents/` | List all document analyses |
| `GET` | `/api/v1/projects/{id}/documents/{file_id}/analysis` | Get analysis for a specific file |

### Updated Endpoints
| Method | Path | Change |
|--------|------|--------|
| `POST` | `/api/v1/projects/{id}/chat/` | Now uses Project Brain + knowledge graph extraction in background |
| `POST` | `/api/v1/projects/{id}/files/` | Now triggers multimodal processing for images/PDFs |

---

## Example AI Prompts Used Internally

### 1. Knowledge Graph Extraction Prompt
```
You are a knowledge graph extraction engine. Given the conversation below,
extract entities and relationships relevant to a software project.

Entity types: technology, architecture_component, project_goal, module, task,
              person, service, database, concept
Relationship types: uses, contains, depends_on, implements, connects_to,
                    part_of, related_to

Return JSON: { "entities": [...], "relationships": [...] }
```

### 2. Gemini Vision Image Analysis Prompt
```
Analyze this image in detail. Describe:
1. What the image shows
2. If it's a diagram/architecture: identify components, connections, and patterns
3. If it's a screenshot: identify the application, UI elements, and state
4. Any text visible in the image
5. Key technical insights
```

### 3. Document Context Analysis Prompt
```
PROJECT CONTEXT: {project_context}
DOCUMENT CONTENT: {text_content}

Provide a structured analysis covering:
1. Summary of the document
2. Key technical components mentioned
3. Architecture decisions or patterns
4. Action items or tasks implied
5. Technologies and tools referenced
```

### 4. Project Brain Enhanced System Prompt
```
You are PraxisForge AI, an expert project development assistant with a Project Brain.
You have access to the user's project documents, past conversations, knowledge graph,
structured facts, task status, and document analyses via RAG memory.
Always reference concrete details from the provided context when answering.
When discussing architecture or technology, reference the knowledge graph entities.
When discussing progress, reference tasks and deadlines.
When discussing documents or images, reference the document analysis results.
```

---

## Integration with Existing Chat System

The existing chat endpoint (`POST /projects/{id}/chat/`) has been upgraded:

1. **Before** (v0.3): RAG chat → retrieves documents + facts from Qdrant → generates response
2. **After** (v0.4): Project Brain chat → gathers ALL data sources → generates context-rich response

### Data Flow on Every Chat Message:

```
User Message
    │
    ▼
┌──────────────────────────────────┐
│ PROJECT BRAIN Context Builder    │
│  1. Fetch all structured facts   │
│  2. Fetch all tasks + deadlines  │
│  3. Fetch knowledge graph        │
│  4. Fetch document analyses      │
│  5. Fetch recent chat history    │
│  6. Vector search (query-based)  │
│  7. Build unified prompt         │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ LLM Generation (Gemini)         │
│  System prompt + Full context    │
└──────────────┬───────────────────┘
               │
               ▼
       AI Response Saved
               │
               ▼
┌──────────────────────────────────┐
│ Background Tasks (Groq)         │
│  1. Smart Extraction             │
│     → facts, tasks → Qdrant     │
│  2. Knowledge Graph Extraction   │
│     → entities, relationships    │
└──────────────────────────────────┘
```

### Multimodal File Upload Flow:

```
File Upload (image/PDF/document)
    │
    ├── Inline: text chunking + Qdrant storage (existing)
    │
    └── Background: Multimodal Processing Pipeline
            │
            ├── 1. Text Extraction (PyMuPDF / Tesseract OCR)
            ├── 2. AI Analysis (Gemini Vision for images, LLM for text)
            ├── 3. Combined text generation
            ├── 4. Embedding + Qdrant storage (document + analysis chunks)
            └── 5. PostgreSQL document_analyses record
```

---

## Infrastructure Notes

### Required (core stack):
- PostgreSQL 16 — structured data + new tables
- Qdrant v1.12 — vector embeddings with new `document_analysis` chunk type
- Gemini API — LLM + embeddings + vision (multimodal)
- Groq API — fast background extraction
- Tesseract OCR — installed in Docker container

### Optional (docker-compose `--profile full`):
- MinIO — S3-compatible object storage for files
- Redis — caching layer for brain context

### New Dependencies:
- `PyMuPDF==1.25.1` — PDF text extraction
- `pytesseract==0.3.13` — OCR wrapper
- `Pillow==11.1.0` — image processing

### Migration:
```bash
alembic upgrade head  # applies 005_knowledge_graph_multimodal_brain
```
