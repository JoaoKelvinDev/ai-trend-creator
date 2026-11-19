# Fontes e Licenças - Verificação Obrigatória

> **Regra do AGENTS.md**: Licenças dos pesos dos modelos, checkpoints, vozes e templates devem ser verificadas **individualmente**. O fato de uma ferramenta ser open source não garante licença livre para todo modelo ou recurso que a acompanha.

---

## 1. LLMs (Ollama)

| Modelo | Licença | Uso Comercial | Fonte | Verificado em |
|--------|---------|---------------|-------|---------------|
| llama3.1:8b-instruct-q4_K_M | Meta Llama 3.1 Community License | ✅ Sim (com restrições) | ollama.com/library/llama3.1 | 2026-11-17 |
| llama3.2:3b-instruct-q4_K_M | Meta Llama 3.2 Community License | ✅ Sim | ollama.com/library/llama3.2 | Pendente |
| mistral:7b-instruct-q4_K_M | Apache 2.0 | ✅ Sim | ollama.com/library/mistral | Pendente |
| phi3:mini-4k-instruct-q4_K_M | MIT | ✅ Sim | ollama.com/library/phi3 | Pendente |

**Notas**:
- Llama 3.x: Requer aceitação de termos, restrição de uso para >700M usuários mensais
- Verificar `ollama show <modelo> --license` antes de usar
- Modelos quantizados (q4_K_M) herdam licença do original

---

## 2. Geração de Imagens (ComfyUI + Checkpoints)

### ComfyUI (Framework)
- **Licença**: GPL-3.0
- **Repo**: https://github.com/comfyanonymous/ComfyUI
- **Nota**: A licença do framework **não** cobre checkpoints

### Checkpoints Principais

| Checkpoint | Licença | Uso Comercial | Fonte | Verificado |
|------------|---------|---------------|-------|------------|
| SDXL Base 1.0 | CreativeML OpenRAIL++-M | ⚠️ Restrito | HuggingFace stabilityai/stable-diffusion-xl-base-1.0 | Pendente |
| SDXL Refiner 1.0 | CreativeML OpenRAIL++-M | ⚠️ Restrito | HuggingFace stabilityai/stable-diffusion-xl-refiner-1.0 | Pendente |
| SD 1.5 | CreativeML OpenRAIL-M | ⚠️ Restrito | HuggingFace runwayml/stable-diffusion-v1-5 | Pendente |
| SD 2.1 | CreativeML OpenRAIL++-M | ⚠️ Restrito | HuggingFace stabilityai/stable-diffusion-2-1 | Pendente |
| Juggernaut XL | CreativeML OpenRAIL++-M | ⚠️ Restrito | CivitAI | Pendente |
| DreamShaper XL | CreativeML OpenRAIL++-M | ⚠️ Restrito | CivitAI | Pendente |

**CreativeML OpenRAIL++-M Restrições**:
- Não uso para gerar conteúdo ilegal, prejudicial, enganoso
- Não uso para vigilância, reconhecimento facial
- Atribuição recomendada
- **Uso comercial permitido** com as restrições acima

**Ação necessária**: Baixar e arquivar licença de cada checkpoint usado em `docs/licenses/`

---

## 3. Text-to-Speech (Piper)

### Piper Engine
- **Licença**: GPL-3.0 (motor)
- **Repo**: https://github.com/OHF-Voice/piper1-gpl
- **Nota**: Licença das vozes é **separada** do motor

### Vozes pt-BR Disponíveis

| Voz | Licença | Uso Comercial | Fonte |
|-----|---------|---------------|-------|
| pt_BR-faber-medium | CC-BY-4.0 | ✅ Sim | huggingface.co/rhasspy/piper-voices |
| pt_BR-faber-low | CC-BY-4.0 | ✅ Sim | huggingface.co/rhasspy/piper-voices |
| pt_BR-alessandro-medium | CC-BY-4.0 | ✅ Sim | huggingface.co/rhasspy/piper-voices |

**Ação**: Verificar licença específica em `https://huggingface.co/rhasspy/piper-voices/tree/main/pt_BR`

---

## 4. Fontes de Tendências

### YouTube Data API v3
- **Termos**: https://developers.google.com/youtube/terms
- **Quota**: 10.000 unidades/dia (gratuito)
- **Custo**: `search.list` = 100 unidades, `videos.list` = 1 unidade
- **Restrições**: Não armazenar dados >30 dias, não re-expor API

### Feeds RSS
- **Licença**: Depende de cada feed
- **Política**: Usar apenas feeds com termos claros de redistribuição
- **Exemplos confiáveis**:
  - GitHub Trending: `https://github.com/trending/rss` (MIT)
  - Hacker News: `https://hnrss.org/` (MIT)
  - Reddit (subreddits): `https://www.reddit.com/r/<sub>/.rss` (User Agreement)

### Importação Manual
- **Responsabilidade**: Operador garante direitos sobre conteúdo importado
- **Formato**: JSON/CSV com campos `source`, `url`, `title`, `evidence`

---

## 5. Plataformas de Publicação

### TikTok Content Posting API
- **Docs**: https://developers.tiktok.com/products/content-posting-api/
- **Requisitos**: App aprovado, OAuth, escopos `video.publish`, `video.upload`
- **Restrições**: Contas pessoais não elegíveis, requer Business Account
- **Política de Conteúdo**: https://developers.tiktok.com/docs/en/content-sharing-guidelines

### Telegram Bot API
- **Termos**: https://core.telegram.org/bots/faq
- **Rate Limits**: 30 msg/s por bot, 20 msg/min por chat
- **Grátis**: Sim, sem quota paga

---

## 6. Ferramentas de Sistema

| Ferramenta | Licença | Uso |
|------------|---------|-----|
| FFmpeg | LGPL-2.1 / GPL-2.0 | Renderização vídeo |
| PostgreSQL 16 | PostgreSQL License | Banco de dados |
| Redis 7 | BSD-3-Clause | Cache/Filas |
| Python 3.13 | PSF License | Runtime |
| SQLAlchemy 2.x | MIT | ORM |
| FastAPI | MIT | Web Framework |
| Pydantic v2 | MIT | Validação |
| Celery | BSD-3-Clause | Filas assíncronas |
| APScheduler | MIT | Agendamento |

---

## 7. Checklist de Verificação (por release)

- [ ] Licença de cada modelo LLM verificada e arquivada
- [ ] Licença de cada checkpoint ComfyUI verificada e arquivada
- [ ] Licença de cada voz Piper verificada e arquivada
- [ ] Termos de YouTube Data API revisados
- [ ] Feeds RSS com licença compatível confirmados
- [ ] TikTok App Review status verificado (se official mode)
- [ ] Nenhuma dependência com licença viral (GPL) vinculada estaticamente no distribuível
- [ ] Arquivo `docs/licenses/` atualizado com cópias das licenças

---

## 8. Arquivo de Licenças (exemplo estrutura)

```
docs/licenses/
├── ollama/
│   ├── llama3.1-8b-instruct.LICENSE
│   └── mistral-7b-instruct.LICENSE
├── comfyui/
│   ├── sd_xl_base_1.0.LICENSE
│   └── sd_1.5.LICENSE
├── piper/
│   ├── pt_BR-faber-medium.LICENSE
│   └── piper-engine-GPL-3.0.txt
├── youtube-api/
│   └── terms-of-service.html
└── tiktok/
    └── content-posting-api-terms.html
```