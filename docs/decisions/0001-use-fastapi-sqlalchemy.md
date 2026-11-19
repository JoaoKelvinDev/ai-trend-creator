# ADR 0001: FastAPI + SQLAlchemy 2.x + PostgreSQL

## Status
Accepted

## Contexto
Precisamos de um framework web assíncrono, ORM moderno e banco relacional robusto para o backend do AI Trend Creator.

## Decisão
- **Framework**: FastAPI (async nativo, validação Pydantic, OpenAPI automático)
- **ORM**: SQLAlchemy 2.x (async, tipo-safe, migrações Alembic)
- **Banco**: PostgreSQL 16 (JSONB, UUID, índices parciais, confiabilidade)
- **Cache/Filas**: Redis 7 + Celery

## Alternativas Consideradas
| Opção | Prós | Contras |
|-------|------|---------|
| Django + DRF | Admin, auth built-in | Sync-only, mais pesado, ORM menos flexível |
| Flask + SQLAlchemy | Simples | Sem async nativo, mais boilerplate |
| FastAPI + Tortoise ORM | Async nativo | Menos maduro, menos features PostgreSQL |
| Node.js + Prisma | Type-safe end-to-end | Ecossistema JS, não Python (equipe) |

## Consequências
- **Positivas**: Performance async, type hints completos, ecossistema Python/ML, migrações versionadas
- **Negativas**: Curva de aprendizado SQLAlchemy 2.x, Celery adiciona complexidade operacional
- **Riscos**: Async DB connections pool tuning necessário em carga

## Implementação
- `backend/app/main.py` - FastAPI app com lifespan
- `backend/app/db/session.py` - Async engine + session factory
- `backend/app/db/models.py` - 17 tabelas com enums PostgreSQL
- `migrations/` - Alembic config + migration inicial
- `docker-compose.yml` - PostgreSQL + Redis containers