# PraxisForge API Frontend Guide (AZ, comprehensive)

Bu senedin meqsedi: layiheye yeni qosulan bir frontend developer backend koduna baxmadan API meqzini, mehdudiyyetleri ve implementasiya qaydasini anlaya bilsin.

Bu fayli oxuyandan sonra developer:
1. Sistem ne edir sualina cavab vere bilir.
2. Hansi endpoint hansi ekran ucundur bilir.
3. Request/response formatini duzgun qurur.
4. Error hallari ucun UI davranisini yaza bilir.
5. Minimum MVP-den tam AI experience-e qeder addim-addim front qura bilir.

---

## 1) Sistem meqzi ve domen modeli

PraxisForge AI destekli project management platformasidir.

Platformanin merkezi vahidi `project`-dir. Demek olar butun endpoint-ler `project_id` etrafinda firlanir:
1. Operational layer: projects, tasks, comments, members
2. Knowledge layer: files, document analysis, insights, knowledge graph
3. AI interaction layer: chat, brain, summary, search

### Frontend ucun net mental model
1. Istifadeci project yaradir.
2. Task ve team idaresi edir.
3. Fayl yukleyir.
4. AI chat/summary/search ile qerar deyisiklikleri alir.
5. Cixarilan bilikler insights ve knowledge graph-da toplanir.

Bu axin UI planlamasini sadelesdirir: her sehife bir project contextinde isleyir.

---

## 2) Base URL, auth, headers

### Base URL
API prefix:
- `/api/v1`

Health endpoint-leri prefixsizdir:
- `/health`
- `/health/ready`
- `/health/live`

### Auth
Health xaric endpoint-lerin coxu Bearer JWT teleb edir.

Header:
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

JWT-den backend `sub` claim-ni user id kimi goturur.

### Frontend interceptor standardi
1. Her request-den evvel token elave et.
2. 401 gelende sessiyani invalidate et.
3. Eger refresh mexanizmi varsa 1 defe retry et.

---

## 3) Qlobal enum ve tipler

### ProjectMode
- `startup`
- `hackathon`
- `enterprise`
- `idea`

### TaskStatus
- `todo`
- `in_progress`
- `done`

### TaskPriority
- `low`
- `medium`
- `high`
- `urgent`

### MemberRole
- `admin`
- `member`
- `viewer`

### FactCategory
- `technical_decision`
- `key_player`
- `milestone`
- `deadline`
- `architecture`
- `general`

### EntityType
- `technology`
- `architecture_component`
- `project_goal`
- `module`
- `task`
- `person`
- `service`
- `database`
- `concept`

### RelationshipType
- `uses`
- `contains`
- `depends_on`
- `implements`
- `connects_to`
- `part_of`
- `related_to`

### FileStatus
- `processing`
- `ready`
- `failed`

### DocumentProcessingStatus
- `pending`
- `extracting_text`
- `analyzing`
- `embedding`
- `ready`
- `failed`

---

## 4) API qruplari: endpoint-by-endpoint izah

Asagidaki formatdan istifade olunur:
1. Meqsed
2. Input
3. Success response
4. Tipik xeta cavablari
5. Frontend istifadesi

---

## 4.1 Projects

Base prefix: `/api/v1/projects`

### POST `/api/v1/projects/`
Meqsed:
- Yeni project yaratmaq.

Body:
```json
{
  "name": "Smart Inventory",
  "description": "AI ile anbar proqnozu",
  "mode": "startup"
}
```

Success 201:
```json
{
  "id": "d08a2d6e-13f0-4df6-a3e2-4fef261f04da",
  "owner_id": "user-123",
  "name": "Smart Inventory",
  "description": "AI ile anbar proqnozu",
  "mode": "startup",
  "created_at": "2026-03-16T10:12:45.123456"
}
```

Tipik xeta:
- 401: token yoxdur/yanlis
- 422: body validasiya xetasi

Frontend istifadesi:
- Create project modal submit.

### GET `/api/v1/projects/`
Meqsed:
- Cari user-in butun project-lerini almaq.

Success 200:
```json
[
  {
    "id": "d08a2d6e-13f0-4df6-a3e2-4fef261f04da",
    "owner_id": "user-123",
    "name": "Smart Inventory",
    "description": "AI ile anbar proqnozu",
    "mode": "startup",
    "created_at": "2026-03-16T10:12:45.123456"
  }
]
```

Frontend istifadesi:
- Dashboard project cards.

### GET `/api/v1/projects/{project_id}`
Meqsed:
- Tek project detail.

Path param:
- `project_id` (UUID)

Success 200: Project object

Tipik xeta:
- 404: project tapilmadi

### PATCH `/api/v1/projects/{project_id}`
Meqsed:
- Project update.

Body (partial):
```json
{
  "name": "Smart Inventory v2",
  "mode": "enterprise"
}
```

Success 200: updated Project object

### DELETE `/api/v1/projects/{project_id}`
Meqsed:
- Project silmek.

Success 204: body yoxdur

---

## 4.2 Tasks

Base prefix: `/api/v1/projects/{project_id}/tasks`

### POST `/`
Meqsed:
- Yeni task yaratmaq.

Body:
```json
{
  "title": "MVP login flow",
  "description": "JWT ile login tamamlanmalidir",
  "assignee_id": null,
  "priority": "high",
  "tags": ["auth", "mvp"],
  "dependencies": [],
  "deadline": "2026-03-20T18:00:00"
}
```

Success 201:
```json
{
  "id": "7e0f3f9a-3a0b-42a8-90d3-63f63b894c6a",
  "project_id": "d08a2d6e-13f0-4df6-a3e2-4fef261f04da",
  "title": "MVP login flow",
  "description": "JWT ile login tamamlanmalidir",
  "assignee_id": null,
  "priority": "high",
  "tags": ["auth", "mvp"],
  "dependencies": [],
  "deadline": "2026-03-20T18:00:00",
  "status": "todo",
  "created_by": "user",
  "created_at": "2026-03-16T10:30:11.000000"
}
```

Tipik xeta:
- 422: assignee member deyil
- 422: dependency task bu projectde yoxdur
- 404: project yoxdur

### GET `/`
Meqsed:
- Projectin butun tasklarini listlemek.

Success 200: Task[]

Frontend istifadesi:
- Kanban ve table view eyni datani bu endpoint-den alir.

### GET `/{task_id}`
Meqsed:
- Task detail.

Success 200: Task

### PATCH `/{task_id}`
Meqsed:
- Task update.

Body (partial update):
```json
{
  "status": "in_progress",
  "assignee_id": "33d988c6-8db9-4f6c-904c-8cf8fdd88d93"
}
```

Success 200: updated Task

Qeyd:
- Backend status aliaslarini da qebul edir (meselen doing, complete), amma frontendde standard enum gondermek daha duzgundur.

### DELETE `/{task_id}`
Meqsed:
- Task silmek.

Success 204

---

## 4.3 Comments

Base prefix: `/api/v1/projects/{project_id}/tasks/{task_id}/comments`

### POST `/`
Meqsed:
- Task altina comment yazmaq.

Body:
```json
{
  "content": "Bu task ucun API contract hazirdir"
}
```

Success 201: Comment object

### GET `/`
Meqsed:
- Task comment list.

Success 200: Comment[]

### GET `/{comment_id}`
Meqsed:
- Tek comment.

Success 200: Comment

### PATCH `/{comment_id}`
Meqsed:
- Comment update.

Body:
```json
{
  "content": "Yeni redakte olunmus comment"
}
```

Tipik xeta:
- 403: author deyilsense redakte ede bilmersen

### DELETE `/{comment_id}`
Meqsed:
- Comment silmek.

Tipik xeta:
- 403: author deyilsense sile bilmersen

Success 204

---

## 4.4 Members

Base prefix: `/api/v1/projects/{project_id}/members`

### POST `/`
Meqsed:
- Layiheye uzv elave etmek.

Body:
```json
{
  "email": "dev@example.com",
  "role": "member"
}
```

Success 201:
```json
{
  "user_id": "4a0664e2-8bb1-58ce-bc89-3ef8dd4d5dd8",
  "email": "dev@example.com",
  "role": "member"
}
```

Tipik xeta:
- 409: member artiq movcuddur
- 404: project tapilmadi

### GET `/`
Meqsed:
- Team list.

Success 200: ProjectMember[]

---

## 4.5 Files

Base prefix: `/api/v1/projects/{project_id}/files`

### POST `/`
Meqsed:
- Fayl upload,
- text chunk/embedding,
- image/pdf olarsa arxa planda multimodal emal.

Request:
- `multipart/form-data`
- field: `file`

Mehdudiyyetler:
- max 50 MB
- yalniz icazeli extensionler

Success 201: File object

Tipik xeta:
- 413: file olcusu cox boyuk
- 422: extension icazeli deyil

Frontend davranisi:
1. Uploaddan sonra listi refetch et.
2. `status=processing` ucun spinner badge goster.
3. `status=failed` ucun retry UX ver.

### GET `/`
Meqsed:
- Project fayllarini listlemek.

Success 200: File[]

### GET `/{file_id}/download`
Meqsed:
- Fayli yuklemek.

Success 200: binary stream

### DELETE `/{file_id}`
Meqsed:
- Fayli sistemden silmek.

Success 204

---

## 4.6 Document Analysis

Base prefix: `/api/v1/projects/{project_id}/documents`

### GET `/`
Meqsed:
- AI emal olunmus dokument analiz listi.

Success 200:
```json
[
  {
    "id": "4ac6b6de-1c72-4c14-9d37-e4f2874b2ca7",
    "file_id": "19f95d20-e3f8-4b16-ab92-84b27dd7dc6e",
    "project_id": "d08a2d6e-13f0-4df6-a3e2-4fef261f04da",
    "extracted_text": "...",
    "ai_analysis": "Senedde esas risk budur...",
    "content_type": "application/pdf",
    "processing_status": "ready",
    "metadata": {"pages": 12},
    "created_at": "2026-03-16T11:05:00"
  }
]
```

### GET `/{file_id}/analysis`
Meqsed:
- Konkret fayl ucun tam analiz.

Tipik xeta:
- 404: hemin fayl ucun analiz hele yoxdur

---

## 4.7 Chat

Base prefix: `/api/v1/projects/{project_id}/chat`

### POST `/`
Meqsed:
- AI chat cavabi almaq.
- Cavabdan sonra background extraction (fact/task/graph) trigger olunur.

Body:
```json
{
  "message": "Bu sprint ucun en optimal plan nedir?"
}
```

Success 200:
```json
{
  "answer": "Sprinti 3 hissede bolmek daha duzgundur...",
  "history": [
    {
      "role": "user",
      "content": "Bu sprint ucun en optimal plan nedir?",
      "created_at": "2026-03-16T11:10:00"
    },
    {
      "role": "assistant",
      "content": "Sprinti 3 hissede bolmek daha duzgundur...",
      "created_at": "2026-03-16T11:10:02"
    }
  ]
}
```

Frontend davranisi:
1. Optimistic user bubble goster.
2. Request bitende assistant bubble doldur.
3. Error halinda failed bubble + retry.

### GET `/history`
Meqsed:
- Son chat mesajlarini almaq.

Success 200: ChatMessage[]

### DELETE `/history`
Meqsed:
- Chat history temizlemek.

Success 204

---

## 4.8 Brain

Base prefix: `/api/v1/projects/{project_id}/brain`

Bu qrup chat endpointinden daha "global context" verir.

### POST `/chat`
Meqsed:
- Facts + tasks + documents + knowledge graph + vector context ile cavab.

Body:
```json
{
  "message": "Architecture bottleneck hardadir?"
}
```

Success 200: ChatResponse

### GET `/summary`
Meqsed:
- Brain metadata summary almaq.

Success 200:
```json
{
  "project_name": "Smart Inventory",
  "project_mode": "startup",
  "tech_stack": ["fastapi", "postgres", "qdrant"],
  "architecture_components": ["api", "vector_store", "llm"],
  "facts_count": 18,
  "facts_by_category": {
    "technical_decision": 6,
    "milestone": 4
  },
  "task_stats": {
    "todo": 12,
    "in_progress": 5,
    "done": 8
  },
  "has_knowledge_graph": true,
  "documents_analyzed": 7
}
```

UI istifadesi:
- Project intelligence dashboard header.

---

## 4.9 Insights

Base prefix: `/api/v1/projects/{project_id}/insights`

### GET `/`
Meqsed:
- Faktlari kateqoriya bazasinda getirmek.

Success 200:
```json
{
  "technical_decisions": [],
  "key_players": [],
  "milestones": [],
  "deadlines": []
}
```

### GET `/all`
Meqsed:
- Butun faktlar tek list.

Success 200: Fact[]

### POST `/pin`
Meqsed:
- Kritik fakti manual pin etmek.

Body:
```json
{
  "content": "Postgres + Qdrant hibrid saxlanacaq",
  "category": "technical_decision"
}
```

Success 201: Fact

### PATCH `/{fact_id}`
Meqsed:
- Fakt redaktesi.

### DELETE `/{fact_id}`
Meqsed:
- Fakt silmek.

---

## 4.10 Search

Base prefix: `/api/v1/projects/{project_id}/search`

### POST `/`
Meqsed:
- Market uniqueness + SWOT.

Body:
```json
{
  "query": "AI inventory optimization SaaS competitors"
}
```

Success 200:
```json
{
  "summary": "Mehsul B2B segmentde ferqlenir...",
  "competitors": ["Competitor A", "Competitor B"],
  "swot": {
    "strengths": ["..."],
    "weaknesses": ["..."],
    "opportunities": ["..."],
    "threats": ["..."]
  },
  "evaluation": {
    "uniqueness_score": 74,
    "market_gap_score": 68,
    "feasibility_score": 71,
    "innovation_score": 66,
    "early_stage_fit_score": 79,
    "verdict": "Ilkin merhelede bazar testi ucun mentiqli potensial var.",
    "recommendations": ["Niche segment secin", "Pilot musteri ile test edin"]
  },
  "sources": ["https://...", "https://..."]
}
```

Qeyd:
- Summary dili chat kontekstine gore secilir (chat AZ-dirsa summary AZ, eks halda default EN).
- Search cavabi default olaraq EN-dir, amma AZ query verilirse cavab AZ ola biler.

UI istifadesi:
- SWOT dord card, competitor table, sources link list.

---

## 4.11 Summary

Base prefix: `/api/v1/projects/{project_id}/summary`

### GET `/`
Meqsed:
- Project uzre executive summary.

Success 200:
```json
{
  "project_name": "Smart Inventory",
  "project_mode": "startup",
  "summary": "Layihenin umumi meqzi...",
  "architecture_overview": "Servisler arasi axin...",
  "key_facts": [],
  "recommended_db_structure": "users, projects, tasks ...",
  "key_insights": ["..."],
  "task_overview": {
    "todo": 12,
    "in_progress": 5,
    "done": 8
  }
}
```

UI istifadesi:
- PM/Founder icmallari ucun print-friendly page.

---

## 4.12 Knowledge Graph

Base prefix: `/api/v1/projects/{project_id}/knowledge-graph`

### GET `/`
Meqsed:
- Full graph almaq.

Success 200:
```json
{
  "entities": [
    {
      "id": "e1a...",
      "project_id": "d08...",
      "name": "Qdrant",
      "entity_type": "database",
      "description": "vector store",
      "properties": {},
      "created_at": "2026-03-16T11:20:00"
    }
  ],
  "relationships": [
    {
      "id": "r1...",
      "project_id": "d08...",
      "source_entity_id": "e1...",
      "target_entity_id": "e2...",
      "relationship_type": "depends_on",
      "description": "...",
      "confidence": 0.86,
      "created_at": "2026-03-16T11:21:00"
    }
  ]
}
```

### GET `/entities?entity_type=technology`
Meqsed:
- Filterlenmis entity list.

### POST `/entities`
Meqsed:
- Entity yaratmaq.

Body:
```json
{
  "name": "Redis",
  "entity_type": "service",
  "description": "cache layer",
  "properties": {
    "role": "cache"
  }
}
```

Tipik xeta:
- 409: eyni adla entity artiq var

### DELETE `/entities/{entity_id}`
Meqsed:
- Entity silmek.

### POST `/relationships`
Meqsed:
- Relationship yaratmaq.

Body:
```json
{
  "source_entity_id": "11111111-1111-1111-1111-111111111111",
  "target_entity_id": "22222222-2222-2222-2222-222222222222",
  "relationship_type": "uses",
  "description": "API uses cache"
}
```

Tipik xeta:
- 404: source ve ya target entity yoxdur

### DELETE `/relationships/{rel_id}`
Meqsed:
- Relationship silmek.

---

## 4.13 Users

### GET `/api/v1/users/me`
Meqsed:
- Cari user profilini almaq.

Success 200:
```json
{
  "id": "user-123",
  "email": "owner@example.com"
}
```

UI istifadesi:
- Header avatar menu.

---

## 4.14 Health

### GET `/health`
Meqsed:
- Sistem servislerinin saglamliq yoxlamasi.

Success 200/503:
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "services": {
    "postgres": {"status": "healthy", "message": "Connected", "latency_ms": 4.5},
    "qdrant": {"status": "healthy", "message": "Collection has points", "latency_ms": 8.1}
  }
}
```

### GET `/health/ready`
Meqsed:
- Readiness probe.

### GET `/health/live`
Meqsed:
- Liveness probe.

---

## 5) Frontend ekran-api map-i

### Dashboard
1. GET `/api/v1/users/me`
2. GET `/api/v1/projects/`

### Project Home
1. GET `/api/v1/projects/{project_id}`
2. GET `/api/v1/projects/{project_id}/brain/summary`
3. GET `/api/v1/projects/{project_id}/summary/`

### Tasks Board
1. GET `/api/v1/projects/{project_id}/tasks/`
2. PATCH `/api/v1/projects/{project_id}/tasks/{task_id}`
3. POST `/api/v1/projects/{project_id}/tasks/`

### Task Detail Drawer
1. GET `/api/v1/projects/{project_id}/tasks/{task_id}`
2. GET `/api/v1/projects/{project_id}/tasks/{task_id}/comments/`
3. POST `/api/v1/projects/{project_id}/tasks/{task_id}/comments/`

### Team Management
1. GET `/api/v1/projects/{project_id}/members/`
2. POST `/api/v1/projects/{project_id}/members/`

### AI Chat
1. GET `/api/v1/projects/{project_id}/chat/history`
2. POST `/api/v1/projects/{project_id}/chat/`
3. DELETE `/api/v1/projects/{project_id}/chat/history`

### Files & Docs
1. POST `/api/v1/projects/{project_id}/files/`
2. GET `/api/v1/projects/{project_id}/files/`
3. GET `/api/v1/projects/{project_id}/documents/`
4. GET `/api/v1/projects/{project_id}/documents/{file_id}/analysis`

### Knowledge Graph
1. GET `/api/v1/projects/{project_id}/knowledge-graph/`
2. POST `/api/v1/projects/{project_id}/knowledge-graph/entities`
3. POST `/api/v1/projects/{project_id}/knowledge-graph/relationships`

---

## 6) Error handling ve UX strategiyasi

Tipik status kodlari:
1. 200: ugurlu fetch/update
2. 201: ugurlu create
3. 204: ugurlu delete, body yoxdur
4. 401: auth problemi
5. 403: icaze problemi
6. 404: resurs tapilmadi
7. 409: conflict/duplicate
8. 413: fayl cox boyuk
9. 422: input validasiya xetasi
10. 503: LLM ve ya servis movcud deyil

UI qaydasi:
1. 401: auth page-a yonlendir.
2. 403: "Bu emeliyyat ucun icazeniz yoxdur" toast.
3. 404: empty state + geri qayit.
4. 422: field-level error map.
5. 503: AI modulunda fallback panel goster.

### Validation error payload (tipik FastAPI)
```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

Frontend parser:
1. `loc`-dan field adini cixar.
2. Formun hemin inputuna error bind et.

---

## 7) State management teklifi

Bu layihe ucun query/mutation bazali state idealdir.

Praktik plan:
1. Server state: React Query/TanStack Query
2. UI state: local component state ve ya yigilmis store
3. Form state: React Hook Form + schema validator

### Query key konvensiyasi
1. `projects.list`
2. `projects.detail.{projectId}`
3. `tasks.list.{projectId}`
4. `chat.history.{projectId}`
5. `files.list.{projectId}`
6. `documents.list.{projectId}`
7. `insights.{projectId}`
8. `brain.summary.{projectId}`

### Mutasiya sonra invalidation
1. Task create/update/delete -> `tasks.list.{projectId}` invalidate
2. Comment create/update/delete -> `task.comments.{projectId}.{taskId}` invalidate
3. File upload/delete -> `files.list.{projectId}` ve `documents.list.{projectId}` invalidate
4. Chat send -> `chat.history.{projectId}`, `insights.{projectId}`, `brain.summary.{projectId}` invalidate

---

## 8) API client skeleton (TypeScript)

```ts
export type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

const API_BASE = "/api/v1";

export async function apiRequest<T>(
  path: string,
  method: HttpMethod,
  body?: unknown,
  token?: string,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw { status: res.status, data };
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}
```

File upload helper:
```ts
export async function uploadProjectFile(
  projectId: string,
  file: File,
  token: string,
) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`/api/v1/projects/${projectId}/files/`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });

  if (!res.ok) throw await res.json();
  return res.json();
}
```

---

## 9) MVP implementasiya plani (real sprint view)

### Sprint 1
1. Auth hookup (`/users/me`)
2. Projects CRUD
3. Basic layout + routing

Deliverable:
- Istifadeci project yarada bilir, listi gore bilir.

### Sprint 2
1. Tasks CRUD
2. Comments
3. Members

Deliverable:
- Team task management tam islek.

### Sprint 3
1. Chat + history
2. Insights + Summary
3. Search SWOT

Deliverable:
- PM ucun AI assistant experience.

### Sprint 4
1. Files upload/download/delete
2. Document analysis view
3. Knowledge graph view

Deliverable:
- Knowledge intelligence panel tamamlanir.

---

## 10) Test checklist (frontend QA)

### Functional
1. Token olmadan protected endpoint 401 qaytarir.
2. Project create-den sonra listde yeni card gorunur.
3. Task status update kanban-da derhal deyisir.
4. File upload status processing->ready olaraq yenilenir.
5. Chat send-den sonra historyde her iki mesaj var.

### Error
1. 422 xetalar form field-level gorunur.
2. 409 duplicate hallarda duzgun toast cixir.
3. 503 AI endpointlerde fallback UI cixir.

### UX
1. Loading state butun list endpointlerde var.
2. Empty state (no projects/no tasks/no documents) dizayn olunub.
3. Delete emeliyyatlari confirm modal ile qorunur.

---

## 11) Qisa yekun

Bu backendin istifadesi ucun frontend strategiyasi sade formul ile yadinda qalsin:
1. Evvel project merkezli CRUD.
2. Sonra collaboration (comments/members).
3. Sonra AI (chat/summary/search/insights).
4. En sonda knowledge expansion (files/documents/graph).

Bu ardicilliq hem texniki riskleri azaldir, hem de her sprintde gozle gorunen biznes deyer verir.
