# Contratos de Dados (Pydantic v2)

Todos os contratos seguem o padrão:
- `schema_version` - Versão do contrato (ex: "1.0")
- `trace_id` - UUID para rastreamento distribuído
- `extra="forbid"` - Rejeita campos não declarados
- Validação estrita de tipos e ranges

---

## 1. TrendCandidateV1 (Discovery → Analyst)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "trend_id": "uuid",
  "source": "youtube|rss|manual",
  "external_id": "string",
  "title": "string (1-500 chars)",
  "url": "https://...",
  "observed_at": "2026-11-17T20:00:00Z",
  "published_at": "2026-11-17T12:00:00Z",
  "metrics": {
    "views": 120000,
    "likes": 5000,
    "comments": 300,
    "shares": 100,
    "watch_time_avg_sec": 45.5,
    "growth_rate": 1.25
  },
  "missing_metrics": ["comments", "shares"],
  "language": "pt|en|es",
  "category": "tecnologia|ciencia|saude|...",
  "raw_data": {}
}
```

**Campos obrigatórios**: `trace_id`, `trend_id`, `source`, `external_id`, `title`, `url`, `observed_at`, `metrics`, `language`

---

## 2. TrendAssessmentV1 (Analyst → Strategist)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "trend_id": "uuid",
  "score": 85.5,
  "confidence": 0.9,
  "signals": {
    "growth": 80.0,
    "niche_fit": 90.0,
    "engagement": 70.0,
    "recency": 85.0,
    "production_feasibility": 95.0
  },
  "missing_signals": [],
  "rationale": "Tendência forte em tecnologia com alto engagement...",
  "safety_flags": [],
  "evidence_refs": ["snapshot-123", "cluster-456"],
  "model_version": "llama3.1:8b-instruct-q4_K_M"
}
```

**Fórmula de score**: `0.35*growth + 0.25*niche_fit + 0.20*engagement + 0.10*recency + 0.10*production_feasibility`

**Range**: `score` 0-100, `confidence` 0-1, cada signal 0-100

---

## 3. ContentPlanV1 (Strategist → Scriptwriter)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "project_id": "uuid",
  "candidate_id": "uuid",
  "niche": "tecnologia",
  "target_audience": "Desenvolvedores 25-40 anos interessados em IA",
  "angle": "Como LLMs locais estão democratizando IA generativa",
  "hook": "E se você pudesse rodar GPT-4 no seu laptop sem internet?",
  "key_claims": [
    "Ollama roda modelos 7B em 4GB RAM",
    "ComfyUI gera imagens em 10s na RTX 3050"
  ],
  "evidence_refs": ["https://ollama.com", "https://github.com/comfyanonymous/ComfyUI"],
  "duration_target_seconds": 30,
  "style": "informativo_dinamico",
  "hashtags": ["IA", "Ollama", "ComfyUI", "TechLocal"]
}
```

---

## 4. ScriptV1 (Scriptwriter → Storyboarder)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "project_id": "uuid",
  "revision": 1,
  "narration_segments": [
    {
      "segment_id": "seg-1",
      "text": "Você já imaginou rodar IA poderosa no seu computador?",
      "start_estimate_ms": 0,
      "duration_estimate_ms": 3500,
      "scene_id": "scene-1"
    },
    {
      "segment_id": "seg-2",
      "text": "Com Ollama e ComfyUI, isso é realidade hoje.",
      "start_estimate_ms": 3500,
      "duration_estimate_ms": 4000,
      "scene_id": "scene-2"
    }
  ],
  "on_screen_text": [
    {
      "text_id": "txt-1",
      "text": "IA Local: Privacidade + Custo Zero",
      "start_ms": 1000,
      "duration_ms": 3000,
      "position": "center",
      "style": "highlight"
    }
  ],
  "title": "IA Poderosa no Seu PC - Custo Zero",
  "caption": "Descubra como rodar LLMs e gerar imagens localmente 🚀 #IA #LocalFirst #Tech",
  "hashtags": ["IA", "LocalFirst", "Tech", "Ollama", "ComfyUI"],
  "claim_sources": [
    {
      "claim": "Ollama roda modelos 7B em 4GB RAM",
      "source_url": "https://ollama.com",
      "source_type": "official",
      "verified": true,
      "confidence": 0.95
    }
  ],
  "duration_estimate_seconds": 30.5
}
```

---

## 5. StoryboardV1 (Storyboarder → MediaGenerator)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "project_id": "uuid",
  "revision": 1,
  "scenes": [
    {
      "scene_id": "scene-1",
      "order": 0,
      "start_ms": 0,
      "duration_ms": 5000,
      "narration_segment": "Você já imaginou rodar IA poderosa no seu computador?",
      "visual_kind": "text_card",
      "visual_prompt": null,
      "overlay_text": "IA Local: Privacidade + Custo Zero",
      "asset_ref": null,
      "transition": "fade",
      "provenance": "generated"
    },
    {
      "scene_id": "scene-2",
      "order": 1,
      "start_ms": 5000,
      "duration_ms": 8000,
      "narration_segment": "Com Ollama e ComfyUI, isso é realidade hoje.",
      "visual_kind": "local_ai_image",
      "visual_prompt": "Futuristic laptop with glowing neural network graphics, neon blue/purple, cyberpunk aesthetic, 9:16",
      "overlay_text": "Ollama + ComfyUI",
      "asset_ref": "uuid-asset-123",
      "transition": "cut",
      "provenance": "generated"
    }
  ],
  "total_duration_ms": 13000,
  "license_manifest": [
    {
      "asset_id": "uuid-asset-123",
      "license_type": "custom",
      "license_url": "https://github.com/comfyanonymous/ComfyUI/blob/master/LICENSE",
      "author": "ComfyUI Community",
      "commercial_use_allowed": true,
      "attribution_required": true,
      "attribution_text": "Generated with ComfyUI"
    }
  ]
}
```

**VisualKind valores**: `local_ai_image`, `original_motion_graphic`, `licensed_user_asset`, `text_card`, `local_ai_video` (futuro)

---

## 6. AssetRequestV1 (Storyboarder → ImageProvider)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "project_id": "uuid",
  "scene_id": "scene-2",
  "kind": "image",
  "prompt": "Futuristic laptop with glowing neural network graphics, neon blue/purple, cyberpunk aesthetic, 9:16",
  "width": 1080,
  "height": 1920,
  "seed": 12345,
  "style_reference": "uuid-asset-ref",
  "negative_prompt": "watermark, text, low quality, blurry",
  "steps": 20,
  "cfg_scale": 7.0
}
```

---

## 7. AssetResultV1 (ImageProvider → Renderer)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "asset_id": "uuid",
  "uri": "/data/assets/uuid.png",
  "sha256": "a1b2c3...",
  "provider": "comfyui",
  "model_id": "sd_xl_base_1.0_fp16.safetensors",
  "license_id": "custom-comfyui",
  "metadata": {
    "width": 1080,
    "height": 1920,
    "steps": 20,
    "cfg_scale": 7.0,
    "sampler": "euler_ancestral",
    "seed": 12345
  },
  "width": 1080,
  "height": 1920,
  "mime_type": "image/png"
}
```

---

## 8. RenderResultV1 (Renderer → QualityCheck)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "project_id": "uuid",
  "revision": 1,
  "video_uri": "/data/exports/project-uuid_rev1.mp4",
  "sha256": "f1e2d3...",
  "thumbnail_uri": "/data/exports/project-uuid_rev1_thumb.jpg",
  "duration_ms": 30500,
  "video_codec": "h264",
  "audio_codec": "aac",
  "width": 1080,
  "height": 1920,
  "fps": 30.0,
  "file_size_bytes": 8500000,
  "ffmpeg_cmd": "ffmpeg -y -i ... -c:v libx264 -preset medium -crf 23 ...",
  "render_time_ms": 12000
}
```

---

## 9. QualityReportV1 (QualityCheck → Approval)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "project_id": "uuid",
  "passed": true,
  "checks_performed": [
    "resolution", "aspect_ratio", "duration",
    "video_codec", "audio_codec", "audio_stream",
    "file_integrity", "no_corruption",
    "safe_margins", "subtitles_sync"
  ],
  "issues": [],
  "warnings": ["Margens de segurança não verificadas"],
  "evidence_refs": ["ffprobe-output.json"],
  "metadata": {
    "actual_width": 1080,
    "actual_height": 1920,
    "actual_duration_ms": 30500,
    "actual_video_codec": "h264",
    "actual_audio_codec": "aac"
  }
}
```

**QualityCheck valores**: `resolution`, `aspect_ratio`, `duration`, `video_codec`, `audio_codec`, `audio_stream`, `file_integrity`, `no_corruption`, `safe_margins`, `subtitles_sync`

**QualitySeverity**: `info`, `warning`, `blocking`

---

## 10. ApprovalDecisionV1 (Telegram Bot → Workflow)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "approval_id": "uuid",
  "project_id": "uuid",
  "revision": 1,
  "video_sha256": "f1e2d3...",
  "actor_id": 123456789,
  "decision": "approve|reject|request_revision",
  "feedback": "O gancho está fraco, tornar mais impactante",
  "decided_at": "2026-11-17T21:30:00Z"
}
```

---

## 11. PublicationRequestV1 (Workflow → Publisher)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "project_id": "uuid",
  "revision": 1,
  "video_sha256": "f1e2d3...",
  "destination": "tiktok",
  "mode": "assisted|official",
  "caption": "Legenda final para TikTok",
  "hashtags": ["IA", "LocalFirst", "Tech"],
  "privacy_options": {
    "who_can_view": "public",
    "allow_comments": true,
    "allow_duet": false,
    "allow_stitch": false
  },
  "approved_at": "2026-11-17T21:35:00Z"
}
```

---

## 12. PublicationResultV1 (Publisher → Workflow)

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "mode": "assisted",
  "status": "exported",
  "external_id": null,
  "export_path": "/data/exports/project-uuid_rev1_package.zip",
  "failure_code": null,
  "evidence": {
    "exported_at": "2026-11-17T21:36:00Z",
    "package_contents": ["video.mp4", "thumb.jpg", "caption.txt", "metadata.json"]
  }
}
```

**PublicationMode**: `assisted` (padrão), `official` (requer elegibilidade)
**PublicationStatus**: `pending`, `exported`, `publishing`, `published`, `failed`

---

## Versionamento

- Todos os contratos iniciam em `schema_version: "1.0"`
- Mudanças breaking = nova versão (1.1, 2.0)
- Mudanças não-breaking = patch (1.0.1) - apenas campos opcionais adicionados
- Consumers devem tolerar campos extras desconhecidos (mas Pydantic `extra="forbid"` impede envio)

---

## Validação em Runtime

```python
# Exemplo de validação estrita
from backend.app.schemas.trends import TrendCandidateV1

try:
    candidate = TrendCandidateV1.model_validate(json_data)
except ValidationError as e:
    # Log estruturado + reject
    logger.error("Schema validation failed", extra={"errors": e.errors()})
    raise SchemaValidationError("TrendCandidateV1 inválido", e.errors())
```