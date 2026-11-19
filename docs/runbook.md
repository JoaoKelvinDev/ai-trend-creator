# Runbook Operacional - AI Trend Creator

## Início Rápido

```bash
# 1. Subir infraestrutura
docker-compose up -d

# 2. Instalar dependências
pip install -e ".[dev]"

# 3. Rodar migrações
alembic upgrade head

# 4. Iniciar API
uvicorn backend.app.main:app --reload

# 5. Verificar saúde
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

---

## Serviços

| Serviço | Comando | Porta | Health Check |
|---------|---------|-------|--------------|
| PostgreSQL | `docker-compose up -d postgres` | 5432 | `pg_isready` |
| Redis | `docker-compose up -d redis` | 6379 | `redis-cli ping` |
| API (FastAPI) | `uvicorn backend.app.main:app --reload` | 8000 | `/health/ready` |
| Celery Worker | `celery -A backend.app.workers.celery_app worker -l INFO` | - | Flower (opcional) |
| Celery Beat | `celery -A backend.app.workers.celery_app beat -l INFO` | - | - |
| Telegram Bot | `python -m backend.app.providers.approvals.telegram_bot` | - | `/health/ready` |

---

## Operações Diárias

### Verificar Status Geral
```bash
# Health checks
curl -s http://127.0.0.1:8000/health/live | jq
curl -s http://127.0.0.1:8000/health/ready | jq

# Métricas de quota
curl -s http://127.0.0.1:8000/api/v1/quotas | jq

# Tendências recentes
curl -s "http://127.0.0.1:8000/api/v1/trends?page_size=5" | jq
```

### Executar Descoberta Manual
```bash
curl -X POST http://127.0.0.1:8000/api/v1/discovery/run \
  -H "Content-Type: application/json" \
  -d '{"sources": ["rss", "manual"], "force_refresh": true}'
```

### Listar Candidatos do Dia
```bash
curl -s "http://127.0.0.1:8000/api/v1/candidates?page_size=10" | jq
```

### Ver Detalhes de Vídeo
```bash
curl -s "http://127.0.0.1:8000/api/v1/videos/<VIDEO_ID>" | jq
```

### Solicitar Revisão (após renderização)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/videos/<VIDEO_ID>/request-review"
```

### Ver Aprovações Pendentes
```bash
curl -s "http://127.0.0.1:8000/api/v1/approvals" | jq
```

### Ver Publicações
```bash
curl -s "http://127.0.0.1:8000/api/v1/publications" | jq
```

---

## Manutenção de Banco de Dados

### Backup
```bash
# Backup completo
docker exec ai-trend-postgres pg_dump -U app ai_trend_creator > backup_$(date +%F).sql

# Backup apenas dados (sem schema)
docker exec ai-trend-postgres pg_dump -U app --data-only ai_trend_creator > backup_data_$(date +%F).sql
```

### Restore
```bash
# Parar API primeiro
# docker-compose stop api

# Restore
docker exec -i ai-trend-postgres psql -U app ai_trend_creator < backup_2026-11-17.sql

# Subir API
# docker-compose up -d api
```

### Limpeza de Dados Antigos (Retenção)
```sql
-- Executar via psql ou adminer
-- Rejeitados > 7 dias
DELETE FROM video_projects
WHERE state = 'REJECTED' AND updated_at < NOW() - INTERVAL '7 days';

-- Aprovados > 30 dias (manter auditoria)
DELETE FROM media_assets
WHERE owner_project_id IN (
  SELECT id FROM video_projects
  WHERE state IN ('MANUALLY_PUBLISHED', 'PUBLISHED')
  AND updated_at < NOW() - INTERVAL '30 days'
);

-- Workflow events > 90 dias
DELETE FROM workflow_events
WHERE occurred_at < NOW() - INTERVAL '90 days';
```

### Migrações
```bash
# Nova migração (após mudar models.py)
alembic revision --autogenerate -m "descrição da mudança"

# Aplicar
alembic upgrade head

# Rollback (cuidado!)
alembic downgrade -1
```

---

## Logs e Debugging

### Ver Logs da API
```bash
# Se rodando via uvicorn direto
# Logs vão para stdout (JSON)

# Se rodando via systemd/docker
journalctl -u ai-trend-api -f
docker-compose logs -f api
```

### Filtrar por Trace ID
```bash
# Todos logs de um request específico
grep "trace_id.*abc123" /var/log/ai-trend/*.log | jq
```

### Ver Logs do Celery
```bash
celery -A backend.app.workers.celery_app events
# ou
tail -f /var/log/celery/worker.log
```

---

## Troubleshooting Comum

### API não inicia - "Database connection failed"
```bash
# Verificar PostgreSQL
docker-compose ps postgres
docker-compose logs postgres

# Testar conexão
docker exec ai-trend-postgres pg_isready -U app -d ai_trend_creator

# Verificar DATABASE_URL no .env
cat .env | grep DATABASE_URL
```

### Redis connection failed
```bash
docker-compose ps redis
docker-compose logs redis
redis-cli -h 127.0.0.1 -p 6379 ping
```

### FFmpeg não encontrado
```bash
# Windows
winget install Gyan.FFmpeg
# Ou baixar de https://ffmpeg.org/download.html

# Verificar
ffmpeg -version
```

### Ollama não responde
```bash
# Verificar serviço
ollama list
curl http://127.0.0.1:11434/api/tags

# Reiniciar
ollama serve
```

### ComfyUI não acessível
```bash
# Verificar se rodando
curl http://127.0.0.1:8188/system_stats

# Verificar VRAM
nvidia-smi
```

### Telegram Bot não recebe updates
```bash
# Verificar token
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Verificar webhook (se configurado)
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Testar polling
python -m backend.app.providers.approvals.telegram_bot --test
```

### Quota diária não reseta
```bash
# Verificar fuso horário
curl http://127.0.0.1:8000/api/v1/config | jq .app_timezone

# Ver daily_quotas table
docker exec -it ai-trend-postgres psql -U app -d ai_trend_creator -c "SELECT * FROM daily_quotas;"

# Reset manual (cuidado!)
docker exec -it ai-trend-postgres psql -U app -d ai_trend_creator -c "DELETE FROM daily_quotas WHERE local_date < CURRENT_DATE;"
```

### Celery tasks falhando
```bash
# Ver tasks ativas
celery -A backend.app.workers.celery_app inspect active

# Ver tasks registradas
celery -A backend.app.workers.celery_app inspect registered

# Purge queue (cuidado!)
celery -A backend.app.workers.celery_app purge
```

---

## Monitoramento

### Métricas Chave
| Métrica | Alerta | Ação |
|---------|--------|------|
| `api.health.ready` = false | Imediato | Verificar DB/Redis |
| `quota.candidates_remaining` = 0 | Diário | Normal (limite atingido) |
| `celery.queue.length` > 100 | 15 min | Escalar workers |
| `ffmpeg.render_time_ms` > 60s | Por job | Verificar GPU/CPU |
| `trend.discovery.errors` > 0 | Por execução | Verificar API keys/feeds |

### Dashboards Sugeridos (Grafana/Prometheus)
- API: Request rate, latency (p50/p95/p99), error rate
- Celery: Queue depth, task duration, success rate
- Database: Connections, query duration, replication lag
- Redis: Memory, hit rate, connected clients
- GPU: VRAM usage, GPU utilization, temperature

---

## Atualizações e Deploy

### Atualizar Dependências
```bash
# Verificar outdated
pip list --outdated

# Atualizar (testar em staging primeiro!)
pip install -U "package==new_version"
pip freeze > requirements.txt  # Se não usar pyproject.toml lock
```

### Deploy de Nova Versão
```bash
# 1. Backup DB
# 2. Parar serviços
docker-compose stop api worker beat bot

# 3. Pull novo código
git pull origin main

# 4. Migrações
alembic upgrade head

# 5. Rebuild se Dockerfile mudou
docker-compose build api

# 6. Subir serviços
docker-compose up -d

# 7. Verificar health
curl http://127.0.0.1:8000/health/ready
```

---

## Contatos e Escalação

| Componente | Responsável | Escalação |
|------------|-------------|-----------|
| Infra (Docker/DB/Redis) | DevOps | - |
| API/Backend | Backend Lead | Arquitetura |
| IA/Providers | ML Engineer | Backend Lead |
| Telegram Bot | Backend Lead | - |
| TikTok Integration | Product | Legal/Compliance |

---

## Checklist de Parada de Emergência

Se comportamento anômalo detectado (gasto inesperado, loop infinito, conteúdo inapropriado):

1. [ ] `docker-compose stop api worker beat bot` - Parar processamento
2. [ ] `docker-compose stop redis` - Parar filas
3. [ ] Verificar logs: `docker-compose logs api worker`
4. [ ] Identificar root cause
5. [ ] Fix + teste em staging
6. [ ] `docker-compose up -d` - Restaurar gradualmente
7. [ ] Documentar incidente