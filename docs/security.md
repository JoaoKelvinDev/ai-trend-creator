# Segurança e Conformidade

## Princípios Gerais

1. **Zero Trust**: Todo input é não confiável até validado
2. **Defense in Depth**: Múltiplas camadas de validação
3. **Least Privilege**: Permissões mínimas necessárias
4. **Audit Trail**: Todos os eventos sensíveis logados
5. **R$ 0 Compliance**: Nenhuma dependência que possa gerar cobrança

---

## Validação de Entrada

### Pydantic v2 (Camada 1)
- `extra="forbid"` em todos os schemas
- Validação de tipos, ranges, formatos (URL, UUID, email)
- `str_strip_whitespace=True`, `validate_assignment=True`

### Validadores Customizados (Camada 2)
```python
# backend/app/core/security.py

# SSRF Protection
SafeUrl.validate_url()  # Bloqueia localhost, IPs privados, metadata clouds

# Shell Injection Prevention
validate_no_shell_injection()  # Bloqueia ; & | ` $() ${} > < \n \r

# XSS Prevention
sanitize_html()  # Escapa < > " ' &

# Path Traversal Prevention
sanitize_filename()  # Remove .. / \ caracteres de controle
```

### Rate Limiting (Camada 3)
- In-memory para desenvolvimento (`RateLimiter` class)
- Redis-backed para produção
- Por IP, user_id, endpoint

---

## Gestão de Segredos

### .env (Apenas Desenvolvimento)
```
# NUNCA commitar
TELEGRAM_BOT_TOKEN=123:abc
YOUTUBE_API_KEY=AIza...
TIKTOK_CLIENT_SECRET=secret
```

### Produção
- Variáveis de ambiente injetadas pelo orchestration
- Secrets manager (AWS Secrets Manager, HashiCorp Vault, etc)
- Rotação periódica de tokens

### Logs
- `SensitiveDataFilter` remove automaticamente:
  - `password`, `secret`, `token`, `key`, `api_key`
  - `authorization`, `auth`, `credential`, `private`
- Nível `DEBUG` não loga bodies de request com segredos

---

## Segurança de APIs Externas

### YouTube Data API
- Quota monitorada (alerta em 80%)
- Cache de respostas (TTL 1h)
- Não logar API key em erros

### Telegram Bot
- Webhook secret validation (se webhook)
- Long polling com whitelist de `user_id` + `chat_id`
- Callback data assinado (HMAC) ou versionado
- Idempotência via `callback_data` único

### TikTok API
- OAuth 2.0 com PKCE
- Tokens criptografados em banco
- Refresh token rotation
- Scope mínimo necessário

---

## Processamento de Mídia (FFmpeg)

### Boas Práticas
```python
# SEMPRE usar subprocess com lista de args (shell=False)
cmd = [
    "ffmpeg", "-y",
    "-i", input_path,
    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
    "-c:a", "aac", "-b:a", "128k",
    output_path
]
subprocess.run(cmd, check=True, capture_output=True)
```

### Validação de Arquivos
- `ffprobe` obrigatório antes de processar
- Verificar: codec, resolução, duração, bitrate
- Tamanho máximo: 100 MB (configurável)
- Extensão ≠ conteúdo: validar MIME type real

### Sanitização de Paths
- `LOCAL_STORAGE_ROOT` como base
- `Path.resolve()` + verificação `is_relative_to()`
- Nomes de arquivo: UUID + extensão conhecida

---

## Banco de Dados

### SQLAlchemy 2.x
- Prepared statements (prevenção SQL injection)
- `text()` apenas com parâmetros bindados
- Sessões com `expire_on_commit=False`, `autoflush=False`

### Migrações (Alembic)
- `alembic upgrade head` apenas em deployment controlado
- Backup antes de migrações destrutivas
- Testar migrações em staging

### Dados Sensíveis
- Tokens OAuth criptografados (AES-256-GCM via `cryptography`)
- Hash de vídeos (SHA256) para integridade
- Soft delete (`deleted_at`) para auditoria

---

## Conformidade de Conteúdo

### Direitos Autorais
- **Nunca** reupload de vídeos de terceiros
- Imagens IA: licença do checkpoint + prompt original
- Música: apenas royalty-free com licença verificada
- Atribuição quando requerida pela licença

### Factualidade
- Claims extraídos do roteiro → verificados contra fontes
- Alegações médicas/financeiras/jurídicas → revisão humana obrigatória
- `claim_sources` no `ScriptV1` com `verified` boolean

### IA Transparency
- `ai_disclosure` obrigatório em aprovação
- Metadados do vídeo incluem: modelo, provider, prompt hash
- TikTok: marcação "AI-generated" se aplicável

### LGPD / Privacidade
- Dados pessoais mínimos (apenas `telegram_user_id` para whitelist)
- Retenção: rejeitados 7 dias, aprovados 30 dias (configurável)
- Direito à exclusão: endpoint para deletar dados do usuário

---

## Checklist de Segurança (por release)

### Código
- [ ] `ruff` sem erros de segurança (`S` codes)
- [ ] `bandit` scan sem findings high/medium
- [ ] Dependências atualizadas (`pip-audit` clean)
- [ ] Segredos não hardcoded (`trufflehog`/`git-secrets` clean)

### Runtime
- [ ] Health checks `/health/ready` validam DB + Redis
- [ ] Rate limiting ativo em endpoints públicos
- [ ] Logs JSON sem segredos (verificar amostra)
- [ ] FFmpeg executa com `shell=False` (grep no código)
- [ ] CORS restrito a origins conhecidos

### Dados
- [ ] Migrações testadas em staging
- [ ] Backup automático configurado
- [ ] Retenção de dados implementada
- [ ] Criptografia de tokens OAuth ativa

### Conformidade
- [ ] Licenças de modelos/checkpoints/vozes arquivadas
- [ ] Termos YouTube/TikTok/Telegram revisados
- [ ] Política de moderação de conteúdo documentada
- [ ] Processo de incident response definido

---

## Incident Response

1. **Detecção**: Alertas de health check, logs de erro, métricas anômalas
2. **Contenção**: Desabilitar provider afetado, rate limit agressivo
3. **Análise**: Logs estruturados + trace IDs para rastrear
4. **Remediação**: Fix + deploy + validação
5. **Pós-incidente**: RCA documentado, melhorias no checklist