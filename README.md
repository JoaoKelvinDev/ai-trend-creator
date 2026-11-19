# AI Trend Creator

Sistema automatizado para descoberta de tendências, geração de roteiros e produção de vídeos curtos (vertical 9:16) com revisão humana via Telegram e publicação assistida no TikTok.

## 🎯 Objetivo

- Descobrir tendências em múltiplos nichos via fontes autorizadas (YouTube Data API, RSS, importação manual)
- Selecionar até **2 candidatos por dia** com ranking transparente
- Gerar vídeo híbrido: roteiro (LLM local) + imagens (ComfyUI/local) + narração (Piper TTS) + renderização (FFmpeg)
- **Revisão 100% humana** via Telegram antes de qualquer publicação
- **Custo zero** de APIs pagas — tudo roda localmente

## 🏗️ Arquitetura

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Discovery  │───▶│  Analyst    │───▶│  Strategy   │───▶│ Storyboard  │
│  (RSS/YT)   │    │  (LLM)      │    │  (LLM)      │    │  (cenas)    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                        │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  Approval   │◀───│  Render     │◀───│  Assets     │◀─────────────────┘
│  (Telegram) │    │  (FFmpeg)   │    │  (ComfyUI)  │
└─────────────┘    └─────────────┘    └─────────────┘
        │
        ▼
┌─────────────┐
│  Export     │
│  Assistida  │
└─────────────┘
```

## 📋 Requisitos

- **Python 3.11+**
- **FFmpeg** (renderização de vídeo)
- **Ollama** (LLM local)
- **ComfyUI** (geração de imagens, opcional - requer GPU)
- **Piper TTS** (narração, build manual)
- **PostgreSQL 16+** + **Redis 7+** (via Docker Compose)
- **GPU NVIDIA** com 6+ GB VRAM (recomendado para ComfyUI)

## 🚀 Início Rápido

```bash
# 1. Clonar e entrar no diretório
cd ai-trend-creator

# 2. Copiar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações

# 3. Subir banco e Redis
docker-compose up -d

# 4. Instalar dependências Python
pip install -e ".[dev]"

# 5. Rodar migrações
alembic upgrade head

# 6. Iniciar API
uvicorn backend.app.main:app --reload

# 7. Verificar saúde
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

## 📁 Estrutura do Projeto

```
ai-trend-creator/
├── AGENTS.md                 # Especificação técnica completa
├── README.md                 # Este arquivo
├── .env.example              # Variáveis de ambiente (sem segredos)
├── .gitignore
├── pyproject.toml            # Dependências e configuração
├── docker-compose.yml        # PostgreSQL + Redis
├── alembic.ini               # Configuração de migrações
├── backend/
│   └── app/
│       ├── main.py           # Entry point FastAPI
│       ├── core/             # Config, logging, security, exceptions
│       ├── api/v1/           # Rotas HTTP
│       ├── domain/           # Entidades, enums, políticas
│       ├── schemas/          # Contratos Pydantic v2
│       ├── application/      # Casos de uso
│       ├── agents/           # Prompts/estratégias LLM
│       ├── providers/        # Adapters (descoberta, LLM, imagem, speech, etc.)
│       ├── workflows/        # Orquestrador de estados
│       ├── workers/          # Celery workers
│       ├── render/           # FFmpeg presets
│       └── db/               # ORM, sessão, base
├── migrations/               # Migrações Alembic
├── tests/                    # Testes (unit, integration, contract, e2e)
├── scripts/                  # Scripts de diagnóstico/operação
├── docs/                     # Documentação
└── data/                     # Armazenamento local (gitignored)
```

## 🔧 Configuração Principal (.env)

```dotenv
APP_ENV=development
APP_TIMEZONE=America/Sao_Paulo
APP_HOST=127.0.0.1
APP_PORT=8000
APP_AUTO_PUBLISH=false
APP_CANDIDATE_LIMIT_PER_DAY=2
APP_MAX_REGENERATIONS_PER_CANDIDATE=2
APP_ALLOW_PAID_PROVIDERS=false
APP_EXTERNAL_BILLING_ENABLED=false
APP_TIKTOK_DIRECT_POST_ENABLED=false
APP_LOCAL_VIDEO_DIFFUSION_ENABLED=false

DATABASE_URL=postgresql+psycopg://app:app@127.0.0.1:5432/ai_trend_creator
REDIS_URL=redis://127.0.0.1:6379/0
LOCAL_STORAGE_ROOT=./data

LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M
IMAGE_PROVIDER=comfyui_or_template
COMFYUI_URL=http://127.0.0.1:8188
SPEECH_PROVIDER=piper_local
PIPER_VOICE=pt_BR-faber-medium

YOUTUBE_ENABLED=false
YOUTUBE_API_KEY=
RSS_ENABLED=true
RSS_ALLOWED_FEEDS=
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_IDS=
TELEGRAM_ALLOWED_CHAT_IDS=
TELEGRAM_POLLING_ENABLED=true
TIKTOK_PUBLISH_MODE=assisted
```

## 🧪 Testes

```bash
# Todos os testes
pytest

# Apenas unitários
pytest tests/unit -v

# Com cobertura
pytest --cov=backend.app --cov-report=term-missing
```

## 📚 Documentação

- [Arquitetura](docs/architecture.md)
- [Contratos de Dados](docs/contracts.md)
- [Fontes e Licenças](docs/sources-and-licenses.md)
- [Segurança](docs/security.md)
- [Runbook Operacional](docs/runbook.md)
- [Decisões de Arquitetura (ADRs)](docs/decisions/)

## ⚖️ Licença

Uso interno — não redistribuir.