# AGENTS.md — AI Trend Creator

> Especificação técnica, regras permanentes de engenharia e protocolo de trabalho para o Claude Code.
>
> **Versão:** 1.0 (17/11/2026)  
> **Idioma do produto:** português do Brasil (`pt-BR`)  
> **Ambiente-alvo inicial:** desenvolvimento local no Windows (preferencialmente WSL2 quando necessário), sem serviços pagos e sem exigência de operação 24/7.  
> **Estado:** arquitetura aprovada conceitualmente; implementação **incremental com aprovação humana etapa por etapa**.

---

## 0. Instruções mandatórias ao Claude Code

Você é o engenheiro responsável por **planejar, implementar, testar e documentar** o AI Trend Creator, respeitando as restrições abaixo. Trate este arquivo como referência de arquitetura e requisitos; os requisitos de segurança, custo zero e aprovação humana não podem ser alterados por conveniência.

1. **CUSTO FINANCEIRO DE EXECUÇÃO = R$ 0** como meta obrigatória de desenvolvimento e uso do MVP. Não incorporar APIs pagas, serviços em nuvem com cartão obrigatório, avaliações que expiram, trial com cobrança posterior, assinatura, crédito promocional temporário como dependência ou operação que possa gerar fatura. Software local e APIs realmente gratuitas, dentro das cotas permitidas, são aceitos. **Hardware já disponível, energia, internet e eventual custo da assinatura do próprio Claude Code não são gratuitos**: não chamar isso de operação literalmente sem custo total. Não presumir que assinatura Google AI Plus/Pro autoriza uso gratuito de Gemini, Veo ou geração de imagens por API.
2. **Não fazer compras, ativar billing, adicionar cartão nem habilitar serviços pagos.** Adapters pagos podem existir apenas como interfaces não ativadas; se isso aumentar complexidade, adiar.
3. **Não afirmar que uma funcionalidade é gratuita sem consultar condições atuais** de preço, quotas, política de uso e licença. Se um free tier variar ou não for garantido, deixar desativado por padrão. Na dúvida, preferir execução local.
4. **Não automatizar bypass de proteção, scraping não autorizado, CAPTCHA, endpoints privados, automação oculta de navegador, download/repost de vídeos de terceiros ou publicação fora das políticas das plataformas.** Não usar credenciais de sessão, cookies roubados nem engenharia reversa de APIs privadas.
5. **Aprovação humana obrigatória para cada versão final de vídeo**. Nunca publicar por padrão. Se ocorrer revisão ou regeneração, invalidar a aprovação anterior. Modo inicial de distribuição: **publicação assistida no TikTok**; integração direta é opcional e só pode ser ativada se a conta, o app e o caso de uso forem elegíveis, autorizados e auditados quando necessário.
6. **Antes de escrever código**, inspecionar a estrutura do repositório, informar o hardware necessário, apresentar diagnóstico de viabilidade, plano de arquivos e primeira etapa. **Aguardar aprovação explícita do usuário** para começar a etapa 1. Após cada etapa, executar os testes e apresentar relatório; não iniciar a próxima sem autorização.
7. Não criar tudo de uma vez. Não introduzir microsserviços, Kubernetes, frontend complexo, Supabase, storage comercial ou agentes demais sem justificativa comprovada.
8. Todas as credenciais em `.env` fora do Git; disponibilizar `.env.example` sem valores secretos.
9. O Claude Code pode usar suas próprias ferramentas durante o desenvolvimento, mas o **sistema entregue deve funcionar sem uma assinatura do Claude, ChatGPT ou Gemini**.
10. Ao encontrar incompatibilidade de hardware, quota ou licença, informar o bloqueio e oferecer **fallback gratuito e honesto**, sem fingir que foi gerada uma cena com modelo de vídeo quando foi feita uma animação comum.

### Resultado esperado do Claude Code nesta primeira interação

Produzir uma **avaliação e plano de execução**, sem modificar arquivos ainda:
- diagnóstico do repositório e ambiente local;
- disponibilidade de CPU, RAM, GPU, VRAM, espaço em disco, Python, FFmpeg, Ollama, Docker/WSL2 e suporte a geração de imagens;
- riscos de compatibilidade/licença;
- árvore de diretórios proposta e responsabilidade de cada parte;
- dependências a instalar, tamanho aproximado dos modelos (quando verificado) e comandos planejados;
- desenho detalhado da **Etapa 1** com testes de aceitação;
- perguntas **somente se forem bloqueantes** (ex.: ausência de hardware viável para geração local de imagens);
- solicitar aprovação para implementar apenas a Etapa 1.

---

## 1. Visão do produto

**Nome:** AI Trend Creator.  
**Proposta:** descobrir tendências em vários nichos, selecionar ideias originais com potencial de interesse, produzir até **2 vídeos candidatos por dia** em um formato híbrido de IA, enviar individualmente ao **Telegram** para revisão e preparar os aprovados para publicação no **TikTok**, respeitando políticas oficiais.  
**Público inicial:** um único operador e uma conta de publicação.  
**Objetivo de produto:** prototipar uma linha editorial orientada por dados, sem prometer viralização e sem transformar métricas incompletas em estimativas de viralidade garantida.

### Requisitos confirmados

- Nicho: **multinicho**, com categorias configuráveis.
- Meta: **até dois candidatos renderizados por dia civil** no fuso configurado, não duas publicações automáticas.
- Formato audiovisual: **híbrido** — roteiros com LLM, imagens locais geradas por IA quando o hardware permitir, movimento e tipografia com FFmpeg, narração local e, futuramente, geração local de clipes curtos se viável.
- Revisão: **100% dos vídeos finais**; aceitar, rejeitar ou pedir alteração.
- Publicação: **assistida por padrão**; envio direto apenas quando legalmente e tecnicamente elegível.
- Orçamento de serviços externos: **R$ 0**; bloquear caminhos que possam cobrar.
- Backend: **Python/FastAPI**; qualidade profissional, arquitetura modular, testes.
- Sem painel web no MVP inicial; operação via API/docs, CLI administrativo local e Telegram. Frontend React opcional em fase posterior.

### Fora do escopo inicial

- Replicar vídeos virais, reproduzir rostos/vozes de celebridades ou copiar roteiro de terceiros.
- Scraping irrestrito de TikTok, Instagram, Google Trends, Reddit ou outras redes.
- Garantia de publicação pública automática no TikTok.
- Analisar **todo** vídeo em alta na internet; somente fontes disponíveis e permitidas.
- Vários usuários, times, monetização, multi-conta, painel avançado e geração pesada de text-to-video como requisito de MVP.

---

## 2. Realismo da proposta gratuita

A meta R$ 0 exige **executar inferência e renderização na máquina do usuário**, usando modelos e ferramentas locais. Isso evita faturas de API, mas consome memória, CPU/GPU, disco, energia e horas de processamento. Se a máquina estiver desligada, a rotina local não executará automaticamente — na retomada, política de catch-up configurável sem ultrapassar o limite diário.

O acesso pago a Gemini/Google AI Plus/Pro **não** se transforma em créditos de API consumíveis livremente pelo FastAPI. Em novembro de 2026, a página oficial de preços da Gemini API distingue modelos com camada gratuita de modelos de geração de imagens sem free tier; **não** incluir Gemini Image/Veo como dependência gratuita. Gemini text API somente como opção futura `free_tier_only`, após comprovação da elegibilidade, sem faturamento ativado, com cotas locais e fallback automático para Ollama. Preferir **Ollama local como padrão**, sem dependência do Gemini para o MVP funcionar.

| Capacidade | Padrão R$ 0 | Alternativa/fallback | Condição operacional |
|---|---|---|---|
| Análise/roteiros | Ollama local com modelo adequado e licença verificada | Modelo menor, regras determinísticas para triagem | RAM/CPU suficientes |
| Geração de imagens | ComfyUI local + checkpoint com licença compatível | Imagens disponibilizadas manualmente com direitos, ou gráficos originais em Pillow/SVG | GPU/VRAM pode ser necessária para desempenho aceitável |
| Vídeo final | FFmpeg com imagens, zoom, pan, parallax simples, transições | Kinetic typography / motion graphics locais | Funciona sem gerador de clipes por difusão |
| Text-to-video por difusão | **Desativado** inicialmente | Experimento local somente após benchmark | Muito mais caro em recursos do que animação 2D |
| Narração | Piper (distribuição mantida) com voz pt-BR compatível/licenciada | Narração local gravada pelo usuário; TTS alternativo livre após verificação | Licenças do motor e da voz são separadas |
| Legendas | Segmentação a partir do próprio roteiro/áudio | Whisper.cpp local para timestamps quando necessário | CPU ou GPU conforme tamanho do modelo |
| Tendências | YouTube Data API em quota disponível + feeds RSS autorizados | Feed RSS/manual com arquivo de importação | Sem extrapolar dados de popularidade |
| Aprovação | Telegram Bot API | CLI local se Telegram indisponível | Internet para Telegram |
| Persistência | PostgreSQL local + arquivos locais | SQLite modo leve de desenvolvimento **somente se aprovado** | Sem banco gerenciado pago |
| Filas | Redis + Celery locais | Worker único com fila persistida, se a máquina for limitada | Controlar consumo e concorrência |
| Hospedagem | Computador local | Outra máquina própria existente | Sem uptime garantido e sem nuvem paga |

**Importante:** usar recursos gratuitos de terceiros somente segundo seus termos; não utilizar serviços que cobrem após atingir quota, mesmo se o valor inicial for zero. Falha de cota significa pausar ou usar fallback local, nunca cobrar.

---

## 3. Critérios de hardware e perfis de execução

O Claude Code deve detectar recursos **antes** de escolher modelo de imagem e tamanho do LLM. Não inventar consumo de VRAM ou velocidade para uma configuração ainda desconhecida.

### Perfis

**Perfil A — leve / sem GPU apropriada:**
- LLM pequeno quantizado via Ollama, testado no hardware.
- Geração visual com gráficos originais programáticos, templates, imagens fornecidas/licenciadas. Se ComfyUI rodar em CPU, permitir somente por escolha explícita e alertar sobre tempo.
- FFmpeg com movimento 2D, TTS local e até 2 vídeos como meta condicionada à capacidade de processamento.
- Não descrever vídeos desse modo como contendo imagens geradas por IA se não houver geração real de imagens.

**Perfil B — GPU compatível com memória suficiente:**
- ComfyUI com checkpoint escolhido mediante testes reais.
- Imagens locais de IA + movimento 2D + TTS + FFmpeg.
- Testar formato vertical e produtividade antes de automatizar geração diária.

**Perfil C — GPU muito potente:**
- Somente após o MVP, estudar modelo local de image-to-video/text-to-video, licença e viabilidade.
- Deve permanecer feature flag **desligada** por padrão.

**Gate obrigatório:** produzir um vídeo de amostra com 15–30 s e medir duração real, RAM/VRAM, espaço, qualidade e throughput. Se o hardware não sustentar dois candidatos/dia, registrar capacidade atingida e não prometer o contrário.

---

## 4. Fluxo ponta a ponta

```text
Scheduler local (horário/fuso configuráveis)
    -> Discovery: YouTube/RSS/importação manual
    -> Normalizer/Deduplicator (links, assuntos, fingerprints)
    -> Trend snapshots / clusters
    -> Trend Analyst (ranking transparente)
    -> Content Strategist (seleção multinicho)
    -> Research/Policy Check (fatos, originalidade, riscos)
    -> Scriptwriter (roteiro original + legenda)
    -> Storyboard (cenas, prompts, timeline)
    -> Media Generator (ComfyUI/local templates + Piper)
    -> Renderer FFmpeg (MP4 9:16 + SRT/ASS + thumbnail)
    -> Technical & Content QA
    -> Telegram (prévia + metadados + botões)
        -> REJECTED: encerrar
        -> REVISION_REQUESTED: gerar nova versão e reaprovar
        -> APPROVED: preparar pacote de publicação
            -> ASSISTED_EXPORT: usuário publica no TikTok
            -> OFFICIAL_DIRECT_POST: somente se autorizado e elegível
    -> Armazenar decisões e métricas disponíveis
```

### Limites e políticas

- `daily_candidate_limit=2` por data local configurada (padrão `America/Sao_Paulo`, configurável).
- A seleção pode avaliar várias tendências, mas **não** produzir mais de 2 novos candidatos finais no dia. Regenerações explicitamente solicitadas ficam vinculadas ao mesmo candidato e devem ter limite próprio de tentativas (padrão 2).
- Padrão `auto_publish=false`, `tiktok_direct_post_enabled=false`, `generation_video_diffusion_enabled=false`, `paid_providers_enabled=false`.
- Se não houver fonte válida, não inventar tendências; finalizar execução com `NO_CANDIDATES` e relatório.
- Conteúdo criado deve ser original, sem reupload de terceiros e sem música comercial sem licença adequada.
- Vídeos e imagens de IA devem passar pelas marcações aplicáveis na plataforma de destino; não apresentar um vídeo sintético como gravação real.

---

## 5. Camadas e responsabilidades

### 5.1 Discovery (serviço determinístico)

Responsável por obter **metadados permitidos**, preservar fonte e horário da coleta e armazenar observações. Preferir:

- **YouTube Data API:** `videos.list` para populares por região/categoria e estatísticas disponíveis. Comparar *snapshots* para estimar variação; popularidade instantânea não equivale a crescimento. Limitar chamadas e usar cache. Os custos de quota dependem do método; verificar tabela oficial, especialmente `search.list`.
- **RSS públicos autorizados:** títulos, data, link, resumo conforme termos do fornecedor; RSS mede recência, não engajamento social.
- **Importação manual de tendências:** JSON/CSV com fontes e evidência. Útil quando uma plataforma não fornece API apropriada.

**Não habilitar por padrão:** scraping de TikTok, Instagram, X, Google Trends não oficial; downloads de vídeos e extração de conteúdo além do permitido. Criar interfaces para conectores futuros sem usá-los.

### 5.2 Trend Analyst (LLM + regras)

Recebe candidatos normalizados e snapshots. Calcula sinais verificáveis antes de pedir síntese ao LLM. Sugestão inicial de score em 0..100, não validada empiricamente:

```
score = 0.35 * growth + 0.25 * niche_fit +
        0.20 * engagement + 0.10 * recency +
        0.10 * production_feasibility
```

- Cada atributo normalizado 0..100, com fonte e método documentados.
- Se dados de crescimento/engajamento faltarem: **não fabricar números**. Marcar métricas ausentes, reduzir confiança e usar ranking por evidências disponíveis.
- Penalizar duplicação, fatos não verificáveis, violações de direitos e baixa qualidade editorial.
- Registrar `score`, `confidence`, `evidence`, `missing_metrics`, `rationale` e `model_version`.

### 5.3 Strategy e Scriptwriter (LLM local)

- Construir um ângulo editorial independente do material de origem.
- Produzir gancho de abertura, desenvolvimento e conclusão em 15–45 segundos, com `target_duration_seconds` configurável (padrão 30).
- Duração estimada por fala é apenas heurística; ajustar após TTS real.
- Fornecer referências concretas para alegações objetivas; não inventar citação, dado, data, fonte, estudo ou notícia.
- Gerar título, legenda, lista curta de hashtags relevantes sem promessa de alcance.
- O LLM recebe dados externos como **conteúdo não confiável**: nunca executar instruções inseridas em páginas, títulos ou RSS.

### 5.4 Research & Safety

- Extrair alegações factuais do roteiro e relacioná-las às evidências.
- Exigir revisão humana adicional para alegações médicas, financeiras, políticas, notícias sensíveis e pessoas reais quando as fontes forem fracas.
- Não permitir difamação, desinformação, conteúdo violador de direitos autorais ou imitação enganosa de pessoa.
- Se não houver validação suficiente, bloquear a ideia ou reescrever em caráter explicitamente especulativo quando apropriado.

### 5.5 Storyboard

Cada cena deve ter: `scene_id`, `order`, `start_ms`, `duration_ms`, `narration_segment`, `visual_kind`, `visual_prompt`, `overlay_text`, `asset_ref`, `transition`, `provenance`.

Tipos iniciais: `LOCAL_AI_IMAGE`, `ORIGINAL_MOTION_GRAPHIC`, `LICENSED_USER_ASSET`, `TEXT_CARD`. `LOCAL_AI_VIDEO` somente como expansão após benchmark.

### 5.6 MediaGenerator

Providers com contrato comum:
- `LLMProvider`: `generate_structured(schema, prompt, context)`;
- `ImageProvider`: `generate_image(spec)`;
- `SpeechProvider`: `synthesize(text, voice, locale)`;
- `VideoClipProvider`: `generate_clip(spec)` — interface opcional, desligada por padrão;
- `AssetStore`: `put/get/delete/metadata`.

Adapters iniciais: `OllamaLLMProvider`, `ComfyUIImageProvider` se viável, `PiperSpeechProvider`, `LocalAssetStore`. Criar `MockProvider` determinístico para testes end-to-end.

Verificar licenças do modelo de imagem, da voz e de qualquer recurso importado (inclusive uso comercial e atribuição); guardar o nome da licença, URL, autor e versão. A licença do aplicativo ComfyUI não define a licença de todos os checkpoints.

### 5.7 Rendering e QA

- FFmpeg produz MP4 9:16 (`1080x1920` como alvo quando os assets permitirem; aceitar preview de menor resolução).
- Configuração inicialmente H.264 + AAC, FPS configurável 30.
- Gerar legenda SRT ou ASS, thumbnail e manifest de montagem.
- Validar arquivo com `ffprobe`: resolução, proporção, duração, codecs, stream de áudio, ausência de corrupção evidente.
- Criar timeline com cortes, zoom/pan suave, transição, tipografia legível e margens de segurança para UI do TikTok.
- Evitar upscale enganoso; registrar resolução efetiva dos assets.
- Áudio de fundo é opcional e só usar quando licença comprovada; nunca baixar músicas comerciais do TikTok para reutilização.
- Se falhar uma cena, permitir retry limitado daquela cena sem regenerar o vídeo inteiro.

### 5.8 Approval no Telegram

Mensagem deve incluir: vídeo/preview, ID, versão, título, nicho, duração, fontes e justificativa resumidas, legenda, avisos de direitos/IA e ações `Aprovar`, `Rejeitar`, `Solicitar alterações`.

- Bot identificado por token em segredo, webhook com verificação de segredo ou polling local com controle de idempotência.
- Em desenvolvimento local sem HTTPS público, preferir **long polling** ao invés de abrir porta na internet.
- Whitelist de `telegram_user_id` e `chat_id`; conferir ambos, callback token e versão do conteúdo.
- `callback_data` compacto com identificador e ação; nunca confiar no cliente para estado do vídeo.
- Pedidos de alteração por mensagem associada a um `approval_id` ativo, com timeout e comando de cancelamento.
- Uma aprovação autoriza apenas aquele **hash de arquivo e revisão de metadados**. Qualquer mudança após aprovação invalida a decisão.
- Botões duplicados / múltiplos callbacks são idempotentes. Mostrar confirmação de estado real.

### 5.9 TikTok Publisher

**Implementação inicial obrigatória: `AssistedPublisher`.** Ele prepara:
- MP4 final aprovado;
- thumbnail, legenda e hashtags;
- pacote de exportação em pasta local segura;
- mensagem no Telegram com instruções e arquivo/link autorizado;
- status `READY_FOR_MANUAL_POST`.

O usuário publica pelo aplicativo TikTok e registra opcionalmente o link/ID. Não marcar como publicado sem evidência.

**Implementação opcional posterior: `TikTokOfficialPublisher`.** Só ativar após verificar elegibilidade, OAuth, escopos, aprovação/auditoria, controles de privacidade e requisitos de experiência do usuário. As diretrizes oficiais atuais **não aceitam** utilitário restrito a postar em contas do próprio desenvolvedor/equipe e clientes não auditados têm restrições de privacidade. Se o uso concreto não for elegível, **não implementar workaround**. Não usar Selenium/Playwright para clicar no botão de publicar.

---

## 6. Modelo de estados (máquina de estados transacional)

```text
DISCOVERED -> SCORED -> SELECTED -> SCRIPTED -> STORYBOARDED
 -> GENERATING_ASSETS -> RENDERING -> QUALITY_CHECK
 -> PENDING_APPROVAL
    -> REJECTED
    -> REVISION_REQUESTED -> GENERATING_ASSETS/RENDERING -> QUALITY_CHECK -> PENDING_APPROVAL
    -> APPROVED -> READY_FOR_MANUAL_POST -> MANUALLY_PUBLISHED
    -> APPROVED -> PUBLISHING (somente integration oficial habilitada) -> PUBLISHED

Qualquer etapa executável -> FAILED_RETRYABLE -> RETRYING -> [etapa anterior]
Qualquer etapa executável -> FAILED_TERMINAL
```

Transições permitidas devem ficar explícitas em código, com checagem de versão otimista ou transação. Não aceitar `APPROVED -> PUBLISHED` sem comprovação da publicação. `MANUALLY_PUBLISHED` exige registro manual e fica identificado como não verificado por API, se aplicável.

**Idempotência:** `execution_date + source_key + canonical_trend_key` para descoberta, `candidate_id + revision` para geração e `project_id + revision + destination` para publicação. Qualquer retry deve reutilizar tarefas concluídas e resultados imutáveis sempre que possível.

---

## 7. Modelo de dados

Persistência relacional local (PostgreSQL preferencial); arquivos em disco fora do banco. Usar SQLAlchemy 2.x, Alembic e transações.

| Entidade | Campos mínimos |
|---|---|
| `niches` | id, slug, enabled, weight, restrictions |
| `source_configs` | id, provider, enabled, configuration_json, last_sync_at |
| `trend_items` | id, provider, source_id, original_url, canonical_key, title, published_at, discovered_at, language, niche_guess |
| `trend_snapshots` | id, trend_item_id, captured_at, views, likes, comments, shares, raw_metrics_json |
| `trend_clusters` | id, cluster_key, title, niche_id, created_at |
| `trend_cluster_items` | cluster_id, trend_item_id |
| `content_candidates` | id, cluster_id, score, confidence, rationale, evidence_json, selected_for_date, status |
| `video_projects` | id, candidate_id, revision, state, target_duration_s, video_hash, created_at, updated_at |
| `scripts` | id, project_id, revision, outline_json, script_text, citations_json, duration_estimate_s |
| `storyboard_scenes` | id, project_id, revision, order_index, start_ms, duration_ms, visual_kind, prompt, asset_id |
| `media_assets` | id, owner_project_id, kind, uri, sha256, mime, width, height, duration_ms, provider, model, license_ref, created_at |
| `jobs` | id, kind, project_id, status, attempts, max_attempts, started_at, finished_at, error_type, idempotency_key |
| `approval_requests` | id, project_id, revision, video_sha256, telegram_message_id, telegram_chat_id, status, created_at |
| `approval_decisions` | id, approval_id, actor_id, action, feedback, decided_at |
| `publication_jobs` | id, project_id, revision, destination, mode, status, external_id, exported_path, updated_at |
| `workflow_events` | id, aggregate_id, event_type, payload_json, occurred_at |
| `daily_quotas` | id, local_date, candidates_created, regen_count, source_calls_json |
| `model_registry` | id, provider, model_id, version, license, enabled, health_status |

Regras:
- `UNIQUE(provider, source_id)` onde aplicável; índices em datas/status.
- IDs UUID; todos os timestamps de persistência em UTC; tradução para fuso no agendamento/relatórios.
- Usuário, credenciais e secrets não devem aparecer em logs, eventos ou JSON arbitrário.
- Não guardar vídeo binário em `BYTEA`; `media_assets.uri` deve apontar para storage local.
- Criar migrações reversíveis e modelos de testes.
- Política inicial de retenção parametrizável: rejeitados 7 dias, aprovados 30 dias antes da revisão da política; manter auditoria essencial mesmo após remover arquivos. Não presumir retenção obrigatória legal; confirmar conforme uso.

---

## 8. Contratos entre módulos

Criar Pydantic v2 com validação estrita, versões de schema e exemplos; `extra='forbid'` nos payloads críticos. Não gerar JSON livre para chamadas de IA. Todos os contratos incluem `schema_version`, `trace_id`, timestamps relevantes e identificadores.

### `TrendCandidateV1`

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "trend_id": "uuid",
  "source": "youtube",
  "external_id": "external-id",
  "title": "Assunto em alta",
  "url": "https://www.youtube.com/watch?v=...",
  "observed_at": "2026-11-17T20:00:00Z",
  "published_at": "2026-11-17T12:00:00Z",
  "metrics": {"views": 120000, "likes": null, "comments": null},
  "missing_metrics": ["likes", "comments"],
  "language": "pt",
  "category": "tecnologia"
}
```

Os números acima são **fixtures de exemplo**, nunca dados reais da plataforma.

### Demais modelos obrigatórios

- `TrendAssessmentV1`: `trend_id`, `score` [0..100], `confidence` [0..1], `signals`, `missing_signals`, `rationale`, `safety_flags`, `evidence_refs`.
- `ContentPlanV1`: `candidate_id`, `niche`, `target_audience`, `angle`, `hook`, `key_claims`, `evidence_refs`, `duration_target_seconds`, `style`.
- `ScriptV1`: `project_id`, `revision`, `narration_segments`, `on_screen_text`, `title`, `caption`, `hashtags`, `claim_sources`.
- `StoryboardV1`: `project_id`, `revision`, `scenes[]`, `total_duration_ms`, `license_manifest`.
- `AssetRequestV1`: `project_id`, `scene_id`, `kind`, `prompt`, `width`, `height`, `seed?`, `style_reference?`.
- `AssetResultV1`: `asset_id`, `uri`, `sha256`, `provider`, `model_id`, `license_id`, `metadata`.
- `RenderResultV1`: `project_id`, `revision`, `video_uri`, `sha256`, `thumbnail_uri`, `duration_ms`, `video_codec`, `audio_codec`, `width`, `height`.
- `QualityReportV1`: `passed`, `checks`, `warnings`, `blocking_reasons`, `evidence_refs`.
- `ApprovalDecisionV1`: `approval_id`, `project_id`, `revision`, `video_sha256`, `actor_id`, `decision`, `feedback?`, `decided_at`.
- `PublicationRequestV1`: `project_id`, `revision`, `video_sha256`, `destination`, `mode`, `caption`, `hashtags`, `privacy_options`, `approved_at`.
- `PublicationResultV1`: `mode`, `status`, `external_id?`, `export_path?`, `failure_code?`, `evidence`.

Se o LLM retornar campos ausentes, inválidos ou não parseáveis, fazer no máximo `N` retries limitados e registrar falha, não aceitar JSON parcialmente corrompido.

---

## 9. API e comandos administrativos

Implementar endpoints FastAPI com prefixo `/api/v1`, apenas na máquina local inicialmente, protegidos por autenticação de operador no cenário em que forem expostos fora do loopback.

| Método | Caminho | Ação |
|---|---|---|
| GET | `/health/live` | Processo está vivo |
| GET | `/health/ready` | Banco, filas e provedores essenciais |
| GET | `/api/v1/config` | Configurações públicas/não secretas |
| GET | `/api/v1/trends` | Tendências coletadas |
| POST | `/api/v1/discovery/run` | Descoberta manual idempotente |
| GET | `/api/v1/candidates` | Ranking e status |
| POST | `/api/v1/candidates/{id}/produce` | Solicitar produção respeitando quota |
| GET | `/api/v1/videos` | Listar projetos |
| GET | `/api/v1/videos/{id}` | Estado + versões + QA |
| POST | `/api/v1/videos/{id}/retry` | Retry controlado |
| POST | `/api/v1/videos/{id}/request-review` | Solicitar aprovação no Telegram |
| GET | `/api/v1/approvals` | Auditoria das decisões |
| GET | `/api/v1/publications` | Status de exportação/publicação |
| GET | `/api/v1/quotas` | Uso diário e mensal de quotas |

Endpoints operacionais podem começar como CLI se reduzirem complexidade, desde que o contrato seja registrado e exista teste. Evitar uma rota pública que permita produzir vídeos sem autenticação.

---

## 10. Estrutura de repositório proposta

```text
ai-trend-creator/
├── AGENTS.md                         # Este documento, na raiz
├── README.md                         # Instalação e operação
├── .env.example                      # Variáveis não sensíveis
├── .gitignore
├── pyproject.toml
├── docker-compose.yml                # PostgreSQL/Redis locais (opcional por perfil)
├── backend/
│   └── app/
│       ├── main.py
│       ├── core/                      # Config, logging, segurança, exceptions
│       ├── api/v1/                    # Rotas e dependências HTTP
│       ├── domain/
│       │   ├── entities/
│       │   ├── enums/
│       │   └── policies/              # Quotas, estados, qualidade
│       ├── schemas/                   # Contratos Pydantic v1
│       ├── application/               # Casos de uso
│       ├── agents/                    # Prompts/estratégias sob LLM
│       ├── providers/
│       │   ├── discovery/             # YouTube, RSS, manual, mock
│       │   ├── llm/                   # Ollama, mock
│       │   ├── images/                # ComfyUI, mock, templates
│       │   ├── speech/                # Piper, mock
│       │   ├── storage/               # Local storage
│       │   ├── approvals/             # Telegram, mock
│       │   └── publishing/            # Assisted + interface oficial
│       ├── workflows/                 # Orquestrador e transições
│       ├── workers/                   # Celery/agenda/adapters
│       ├── render/                    # FFmpeg, ffprobe, presets
│       └── db/                        # ORM, migrations integration
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
├── scripts/                           # Diagnóstico e operação local
├── docs/
│   ├── architecture.md
│   ├── contracts.md
│   ├── sources-and-licenses.md
│   ├── security.md
│   ├── runbook.md
│   └── decisions/                   # ADRs
├── data/                              # Gitignored
│   ├── imports/
│   ├── assets/
│   ├── exports/
│   ├── previews/
│   └── models/
└── frontend/                          # Não implementar no MVP
```

Se instalar PostgreSQL + Redis consumir recursos demais para a máquina real, propor **ADR** para perfil leve (SQLite + um worker local) e pedir aprovação antes de alterar essa decisão.

---

## 11. Configurações previstas

No `.env.example`, documentar sem segredos:

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
OLLAMA_MODEL=CHANGE_ME_AFTER_HARDWARE_CHECK
IMAGE_PROVIDER=comfyui_or_template
COMFYUI_URL=http://127.0.0.1:8188
SPEECH_PROVIDER=piper_local
PIPER_VOICE=CHANGE_ME_AFTER_LICENSE_CHECK

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

Nunca adicionar API key em frontend. Nunca habilitar cobrança por meio de uma flag; `ALLOW_PAID_PROVIDERS=false` deve ser controlado **também no factory dos providers**, rejeitando qualquer adapter com `cost_class != zero`, e não apenas em UI.

---

## 12. Qualidade e testes obrigatórios

### Testes de unidade

- Score normalizado, dado ausente, confiança, ordenação, penalidades.
- Deduplicação por URL canônica, IDs externos e clusters.
- Limite diário de 2 e quota de regeneração.
- Transições permitidas/proibidas da máquina de estados.
- Idempotência por projeto/revisão/ação.
- Validação Pydantic de todos os contratos.
- Fuso horário e mudanças de dia sem duplas execuções.

### Testes de integração

- YouTube e RSS com mocks HTTP; nenhum teste depende de quota real.
- Ollama/ComfyUI/Piper com mocks que geram arquivos de amostra válidos.
- PostgreSQL/Redis locais apenas quando disponíveis.
- Telegram callback com usuário permitido/negado; repetição e replay de callback.
- ffprobe sobre MP4 realmente produzido por FFmpeg com fixtures locais.
- Falhas de provedor e retomada sem duplicar outputs.

### Testes end-to-end

Usar uma tendência **simulada e identificada como fixture**, passar por ranking, roteiro, storyboard, montagem, QA, solicitação de aprovação e exportação assistida, sem chamadas pagas e **sem publicar no TikTok**. Confirmar o MP4, manifesto de origem, log de decisão e state transitions.

### Gates de aceitação

- Testes offline não precisam de chaves reais.
- `pytest` passa, lint/format e análise estática configurados.
- Um vídeo de 15–30 segundos exportado e inspecionado automaticamente.
- Qualquer vídeo alterado exige nova aprovação.
- Não existe caminho de publish sem aprovação válida.
- Projeto executa em `R$0` de consumo de APIs pagas.
- Todo caso de fallback informa no manifesto se a imagem é gerada por IA, licenciada/manual ou visual programático.

---

## 13. Segurança e conformidade

- Proteção de endpoints, logs e tokens; não mostrar valores de segredo em exceções.
- LLM output e conteúdos de RSS são dados não confiáveis. Sanitizar entradas e evitar execução de comandos gerados por LLM.
- `ffmpeg` e outros binários sempre invocados com argumentos estruturados, não `shell=True` com texto interpolado.
- Recursos de upload/URL precisam de validação de esquema, domínio, tamanho e prevenção de SSRF/path traversal.
- Limites de arquivo, resolução, timeout, RAM, GPU e concorrência por worker.
- Modelos locais baixados apenas de fontes confiáveis, com integridade e licenças verificadas.
- Política de direitos autorais: reutilizar tendências apenas como **insights**; nunca redistribuir vídeos, músicas, thumbnails ou fotografias de terceiros sem direitos.
- Política factual: informação sobre pessoas e eventos precisa de fonte e verificação proporcional ao risco.
- Rotulagem de IA e transparência para público conforme regras aplicáveis ao canal.
- TikTok: respeitar requisitos oficiais de UI/privacidade/autorização. Não adicionar marcas ou watermarks proibidos.
- Não iniciar servidor de inferência local aberto para toda a rede ou Internet sem autenticação e barreiras.

---

## 14. Observabilidade e operação

Registrar eventos estruturados com `trace_id`, `workflow_id`, `project_id`, `provider`, `step`, `duration_ms`, `success`, `error_code` e tipo de fallback. **Nunca** logar tokens, prompts com segredos ou dados pessoais desnecessários.

Métricas:
- tendências coletadas, deduplicadas e aprovadas para roteiro;
- tempo e falhas por estágio;
- número de imagens renderizadas e tentativas;
- uso CPU/GPU/VRAM observado quando viável;
- quotas consumidas por fonte;
- taxa de aprovação e rejeição;
- vídeos candidatos criados por dia e backlog;
- publicações assistidas efetivamente confirmadas pelo usuário.

O sistema precisa de um *runbook* para iniciar/parar serviços, testar saúde, limpar arquivos, fazer backup do banco, restaurar, refazer tarefa e redefinir bot/token.

---

## 15. Plano incremental com aprovação humana

### Etapa 0 — diagnóstico (obrigatória, sem alterar código)

1. Inspecionar arquivos existentes; não sobrescrever trabalho.
2. Detectar hardware/OS/WSL2, Python/FFmpeg, GPU/VRAM, espaço e rede.
3. Comparar configurações de modelos locais com viabilidade medida/documentada.
4. Verificar licenças das opções de LLM, imagem e voz.
5. Entregar plano e pedir autorização para Etapa 1.

### Etapa 1 — fundação do backend

**Implementar após aprovação:** FastAPI, config, logger, health checks, contratos base Pydantic, esquema inicial, migrations, workflow states, quotas diárias, provider interfaces, mocks, testes e README. Não instalar IA grande nem conectar Telegram/TikTok ainda. Critério: API inicia e testes passam sem internet e sem gasto.

### Etapa 2 — descoberta e intelligence

Conector RSS, importação manual e opcional YouTube (se houver chave e quota gratuita), snapshots, dedupe, scoring, endpoints e testes. Critério: rankings reproduzíveis com evidências e dados ausentes tratados.

### Etapa 3 — roteiro com Ollama

Provedor local, prompt templates versionados, resultados estruturados, validação de alegações, `ContentPlanV1` e `ScriptV1`; mock em CI. Critério: um candidato produz plano e roteiro válidos sem pagar API.

### Etapa 4 — storyboard e geração visual

ComfyUI local se o benchmark permitir; caso contrário, modo visual alternativo **declarado**. Reaproveitamento de assets, proveniência, geração de amostra. Critério: recursos produzidos e indexados localmente.

### Etapa 5 — áudio e renderização

Piper licenciado, segmentação de legendas, FFmpeg, ffprobe, QA e MP4. Critério: um vídeo completo de 15–30 s, 9:16, com fala, legendas e imagem/elementos originais.

### Etapa 6 — bot do Telegram

Configuração segura, polling local, envio de prévia, aprovar/rejeitar/revisar, registro de decisão por versão. Critério: vídeo rejeitado não avança, revisão invalida aprovação anterior.

### Etapa 7 — publicação assistida

Pacote exportável e notificação ao Telegram. Critério: mídia aprovada exportada, com metadados, sem automação irregular do TikTok.

### Etapa 8 — rotina completa de 2 candidatos/dia

Scheduler, quotas, recuperação, analytics local, relatórios e benchmark de uso. Critério: rodada integrada offline em fixtures, e rodada real sob supervisão, sem exceder limite.

**Proibido iniciar etapas posteriores antes de reportar teste e receber aceite explícito.**

---

## 16. Padrão de relatório após cada etapa

Claude Code deve responder de forma objetiva:

1. **Objetivo da etapa** e escopo aprovado.
2. **Arquivos criados/alterados** com responsabilidade e justificativa.
3. **Decisões arquiteturais** (ADR quando houver trade-off).
4. **Comandos executados** e resultados relevantes.
5. **Testes**: quantidade executada, aprovados, falhas e bloqueios.
6. **Limitações técnicas** e custo financeiro esperado **R$0** (explicitar qualquer incerteza).
7. **Problemas pendentes e próximos passos**, sem iniciar automaticamente a próxima etapa.

Nunca afirmar “testado” sem ter executado. Não ocultar exceções; não usar mocks para fingir integração real.

---

## 17. Fontes oficiais para verificar antes de integrar

Consultar a documentação vigente na data de implementação e registrar o status em `docs/sources-and-licenses.md`:

- Gemini API pricing / free-tier por modelo: https://ai.google.dev/gemini-api/docs/pricing
- Gemini API billing e quotas: https://ai.google.dev/gemini-api/docs/billing
- Ollama API: https://docs.ollama.com/api
- ComfyUI local: https://github.com/Comfy-Org/ComfyUI
- Piper mantido (motor GPL-3.0, licenças das vozes individuais): https://github.com/OHF-Voice/piper1-gpl
- FFmpeg filtros: https://ffmpeg.org/ffmpeg-filters.html
- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- YouTube Data API quota: https://developers.google.com/youtube/v3/determine_quota_cost
- YouTube Data API overview: https://developers.google.com/youtube/v3/getting-started
- Telegram Bot API: https://core.telegram.org/bots/api
- TikTok Content Posting: https://developers.tiktok.com/products/content-posting-api/
- TikTok Content Sharing Guidelines: https://developers.tiktok.com/docs/en/content-sharing-guidelines
- TikTok App Review Guidelines: https://developers.tiktok.com/docs/en/app-review-guidelines

Licenças dos pesos dos modelos, checkpoints, vozes e templates devem ser verificadas **individualmente**. O fato de uma ferramenta ser open source não garante licença livre para todo modelo ou recurso que a acompanha.

---

## 18. Definição de pronto do MVP

O MVP está pronto apenas quando:

- [ ] Encontra assuntos por fontes autorizadas ou importação manual verificável.
- [ ] Analisa e classifica candidatos sem dados fabricados.
- [ ] Seleciona até 2 novos vídeos candidatos por dia, por fuso configurado.
- [ ] Produz vídeo original híbrido local, com narração/legendas/manifesto de origem.
- [ ] Grava artefatos, estados, versões, erros e evidências.
- [ ] Reprova conteúdo inseguro, direitos incertos ou vídeo tecnicamente inválido.
- [ ] Envia prévia e dados ao Telegram e exige aprovação individual.
- [ ] Invalida aprovação quando conteúdo ou metadados mudam.
- [ ] Permite exportação assistida do vídeo aprovado para o TikTok.
- [ ] Não oferece publicação automática pública como promessa nem contorna políticas.
- [ ] Não usa serviços pagos e pode executar o fluxo com dados simulados sem API externa.
- [ ] Documenta o limite real de throughput e eventuais capacidades não suportadas pelo computador.
- [ ] Inclui testes, documentação e procedimentos reproduzíveis.

## 19. Mensagem inicial de execução para o Claude Code

> Leia integralmente o `AGENTS.md` na raiz do repositório e trate as restrições de custo zero, aprovação humana e conformidade como mandatórias. Antes de programar, inspecione o repositório e ambiente, diagnostique hardware e dependências, compare a viabilidade das ferramentas gratuitas, proponha o plano detalhado da Etapa 1 e liste arquivos/contratos/testes. Não escreva código nem instale serviços pesados antes de minha aprovação. Após cada etapa aprovada, execute testes, apresente resultados e aguarde novo aceite. Não use APIs pagas nem configure qualquer billing.

---

**Princípio final:** construir um produto funcional com custo monetário externo zero e capacidade comprovada pelo hardware real; nunca trocar honestidade técnica por uma falsa promessa de automação totalmente gratuita, publicação irrestrita ou geração ilimitada de vídeos por IA.
