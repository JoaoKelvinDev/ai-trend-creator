# Arquitetura do AI Trend Creator

## Visão Geral

O AI Trend Creator é um sistema modular para descoberta de tendências, geração de roteiros e produção de vídeos curtos (formato vertical 9:16) com revisão humana via Telegram e publicação assistida no TikTok.

## Princípios Arquiteturais

1. **Custo Zero (R$ 0)**: Todas as inferências e processamentos rodam localmente
2. **Modularidade**: Providers intercambiáveis via interfaces bem definidas
3. **Observabilidade**: Logs estruturados, trace IDs, métricas
4. **Segurança**: Validação de entrada, sanitização, rate limiting
5. **Idempotência**: Operações repetíveis sem efeitos colaterais
6. **Aprovação Humana Obrigatória**: Nenhum vídeo publicado sem revisão

## Camadas da Aplicação

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                    │
│  /health  /config  /trends  /candidates  /videos  /approvals│
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  Use Cases / Orchestrators / Workflows                      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                           │
│  Entities / Enums / Policies (Quotas, States, Quality)      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                      │
│  Providers (Discovery, LLM, Images, Speech, Storage,       │
│              Approvals, Publishing)                         │
│  Database (PostgreSQL + SQLAlchemy 2.x)                    │
│  Queue (Redis + Celery)                                     │
│  Render (FFmpeg)                                            │
└─────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados (Pipeline)

```
Scheduler (APScheduler)
    │
    ▼
Discovery Providers (YouTube API, RSS, Manual Import)
    │
    ▼
Normalizer + Deduplicator (canonical_key, fingerprints)
    │
    ▼
Trend Snapshots → Clusters
    │
    ▼
Trend Analyst (LLM + Regras) → Score 0-100 + Confidence
    │
    ▼
Content Strategist (LLM) → ContentPlanV1 (ângulo, gancho, claims)
    │
    ▼
Scriptwriter (LLM) → ScriptV1 (narração, textos, legendas)
    │
    ▼
Storyboarder → StoryboardV1 (cenas, prompts, timeline)
    │
    ▼
MediaGenerator (ComfyUI, Piper, Templates) → Assets
    │
    ▼
Renderer (FFmpeg) → MP4 9:16 + SRT + Thumbnail
    │
    ▼
Quality Check (ffprobe + validações)
    │
    ▼
Telegram Bot → Aprovação Humana (Approve/Reject/Revision)
    │
    ▼
Assisted Export → Pacote para publicação manual no TikTok
```

## Machine de Estados (VideoProject)

```
DISCOVERED → SCORED → SELECTED → SCRIPTED → STORYBOARDED
    → GENERATING_ASSETS → RENDERING → QUALITY_CHECK
    → PENDING_APPROVAL
        → REJECTED (terminal)
        → REVISION_REQUESTED → GENERATING_ASSETS/RENDERING → ...
        → APPROVED → READY_FOR_MANUAL_POST → MANUALLY_PUBLISHED
        → APPROVED → PUBLISHING (se official) → PUBLISHED

Qualquer estado executável → FAILED_RETRYABLE → RETRYING → estado anterior
Qualquer estado executável → FAILED_TERMINAL
```

## Contratos de Dados (Pydantic v2)

Todos os contratos entre módulos usam Pydantic v2 com:
- `extra="forbid"` - rejeita campos extras
- `schema_version` - versionamento de schema
- `trace_id` - rastreamento distribuído
- Validação estrita de tipos

Principais schemas:
- `TrendCandidateV1` - Tendência descoberta
- `TrendAssessmentV1` - Avaliação do Analyst
- `ContentPlanV1` - Plano editorial
- `ScriptV1` - Roteiro completo
- `StoryboardV1` - Storyboard com cenas
- `AssetRequestV1` / `AssetResultV1` - Geração de assets
- `RenderResultV1` - Resultado da renderização
- `QualityReportV1` - Relatório de qualidade
- `ApprovalDecisionV1` - Decisão de aprovação
- `PublicationRequestV1` / `PublicationResultV1` - Publicação

## Banco de Dados (PostgreSQL)

17 tabelas principais (ver `backend/app/db/models.py`):
- `niches`, `source_configs` - Configuração
- `trend_items`, `trend_snapshots`, `trend_clusters`, `trend_cluster_items` - Descoberta
- `content_candidates` - Candidatos selecionados
- `video_projects`, `scripts`, `storyboard_scenes`, `media_assets` - Produção
- `jobs` - Filas assíncronas
- `approval_requests`, `approval_decisions` - Aprovação
- `publication_jobs` - Publicação
- `workflow_events` - Auditoria (event sourcing leve)
- `daily_quotas` - Controle de quotas diárias
- `model_registry` - Registro de modelos e licenças

## Providers (Interfaces)

```python
# Descoberta
class DiscoveryProvider:
    async def fetch_trends() -> list[TrendCandidateV1]

# LLM
class LLMProvider:
    async def generate_structured(schema, prompt, context) -> BaseModel

# Imagens
class ImageProvider:
    async def generate_image(spec: AssetRequestV1) -> AssetResultV1

# Speech
class SpeechProvider:
    async def synthesize(text, voice, locale) -> AssetResultV1

# Storage
class AssetStore:
    async def put/get/delete/metadata

# Approvals
class ApprovalProvider:
    async def send_for_approval(request: ApprovalRequestV1)
    async def handle_callback(callback: ApprovalCallbackData)

# Publishing
class PublishingProvider:
    async def publish(request: PublicationRequestV1) -> PublicationResultV1
```

## Segurança

- **Input Validation**: Pydantic + validadores customizados (SSRF protection, shell injection prevention)
- **Secrets**: Apenas em `.env`, nunca em logs ou código
- **Rate Limiting**: In-memory para desenvolvimento, Redis para produção
- **Sanitization**: HTML escape, filename sanitization
- **FFmpeg**: Sempre `shell=False`, argumentos estruturados

## Observabilidade

- **Logging**: JSON estruturado com `python-json-logger`
- **Trace ID**: Propagado via headers (`X-Trace-ID`) e contextvars
- **Metrics**: Contadores por etapa, latências, taxa de erro
- **Health Checks**: `/health/live` (processo) + `/health/ready` (dependências)

## Deployment Local

```
docker-compose.yml → PostgreSQL 16 + Redis 7
├── postgres:5432 (data volume)
└── redis:6379 (appendonly)

Aplicação:
├── uvicorn backend.app.main:app --reload (API)
├── celery -A backend.app.workers.celery_app worker (workers)
├── celery -A backend.app.workers.celery_app beat (scheduler)
└── python -m backend.app.providers.approvals.telegram_bot (bot polling)
```

## Escalabilidade Futura

- Workers Celery podem rodar em máquinas separadas
- ComfyUI/Ollama podem ser serviços remotos (com autenticação)
- Frontend React opcional (fase posterior)
- Multi-tenancy via namespaces no banco