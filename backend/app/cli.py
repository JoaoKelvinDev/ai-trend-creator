"""CLI administrativo para o AI Trend Creator."""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from backend.app.core.config import get_settings
from backend.app.db.session import init_db, get_db_context
from backend.app.db.models import (
    VideoProject, ContentCandidate, TrendItem, TrendCluster,
    DailyQuota, Job, ApprovalRequest
)
from backend.app.application.use_cases import (
    run_discovery_use_case,
    score_trends_use_case,
    generate_script_use_case,
    create_storyboard_use_case,
    generate_assets_use_case,
    render_video_use_case,
    quality_check_use_case,
    request_approval_use_case,
    export_package_use_case,
    run_daily_pipeline_use_case,
)
from backend.app.providers.factory import get_provider_factory

# Windows fix: psycopg não suporta ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

console = Console()
settings = get_settings()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """AI Trend Creator - CLI Administrativo"""
    pass


# ──────────────────────────────────────────────
# Database Commands
# ──────────────────────────────────────────────

@cli.group()
def db():
    """Comandos de banco de dados."""
    pass


@db.command("init")
def db_init():
    """Inicializa banco de dados (cria tabelas)."""
    console.print("[yellow]Inicializando banco de dados...[/yellow]")
    asyncio.run(init_db())
    console.print("[green]✓ Banco de dados inicializado[/green]")


@db.command("status")
def db_status():
    """Mostra status do banco de dados."""
    async def _status():
        async with get_db_context() as db:
            from sqlalchemy import select, func
            tables = [
                ("TrendItem", TrendItem),
                ("TrendCluster", TrendCluster),
                ("ContentCandidate", ContentCandidate),
                ("VideoProject", VideoProject),
                ("Job", Job),
                ("ApprovalRequest", ApprovalRequest),
                ("DailyQuota", DailyQuota),
            ]
            table = Table(title="Status do Banco de Dados")
            table.add_column("Tabela", style="cyan")
            table.add_column("Registros", style="green", justify="right")

            for name, model in tables:
                result = await db.execute(select(func.count()).select_from(model))
                count = result.scalar()
                table.add_row(name, str(count))

            console.print(table)

    asyncio.run(_status())


# ──────────────────────────────────────────────
# Discovery Commands
# ──────────────────────────────────────────────

@cli.group()
def discovery():
    """Comandos de descoberta de tendências."""
    pass


@discovery.command("run")
@click.option("--source", type=click.Choice(["rss", "manual", "mock", "all"]), default="all")
@click.option("--limit", type=int, default=50)
def discovery_run(source: str, limit: int):
    """Executa descoberta de tendências."""
    console.print(Panel(f"Executando descoberta: [cyan]{source}[/cyan], limite: [cyan]{limit}[/cyan]"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Descobrindo tendências...", total=None)

        import asyncio
        from backend.app.providers.factory import get_provider_factory

        async def _run_discovery():
            factory = get_provider_factory()

            if source == "all":
                providers = factory.get_all_discovery_providers()
            else:
                providers = [factory.get_discovery_provider(source)]

            all_trends = []
            all_errors = []
            total_calls = {}
            start_time = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)

            for provider in providers:
                try:
                    result = await provider.fetch_trends(limit=limit)
                    all_trends.extend(result.trends)
                    all_errors.extend(result.errors)
                    for k, v in result.source_calls.items():
                        total_calls[k] = total_calls.get(k, 0) + v
                except Exception as e:
                    all_errors.append(f"{provider.provider_name}: {e}")

            # Persistir trends
            new_count = 0
            updated_count = 0

            from backend.app.db.session import get_db_context
            from backend.app.db.models import TrendItem, TrendSnapshot

            async with get_db_context() as db:
                for trend in all_trends:
                    existing = await db.execute(
                        TrendItem.__table__.select().where(
                            TrendItem.canonical_key == trend.canonical_key
                        )
                    )
                    existing = existing.scalar_one_or_none()

                    if existing:
                        snapshot = TrendSnapshot(
                            trend_item_id=existing.id,
                            captured_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc),
                            views=trend.metrics.views,
                            likes=trend.metrics.likes,
                            comments=trend.metrics.comments,
                            shares=trend.metrics.shares,
                            raw_metrics_json=trend.raw_data,
                        )
                        db.add(snapshot)
                        updated_count += 1
                    else:
                        trend_item = TrendItem(
                            provider=trend.source,
                            source_id=trend.external_id,
                            original_url=str(trend.url),
                            canonical_key=trend.canonical_key,
                            title=trend.title,
                            published_at=trend.published_at,
                            discovered_at=trend.observed_at,
                            language=trend.language,
                            niche_guess=trend.category if trend.category else None,
                        )
                        db.add(trend_item)
                        await db.flush()

                        snapshot = TrendSnapshot(
                            trend_item_id=trend_item.id,
                            captured_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc),
                            views=trend.metrics.views,
                            likes=trend.metrics.likes,
                            comments=trend.metrics.comments,
                            shares=trend.metrics.shares,
                            raw_metrics_json=trend.raw_data,
                        )
                        db.add(snapshot)
                        new_count += 1

                await db.commit()

            duration_ms = int((__import__('datetime').datetime.now(__import__('datetime').timezone.utc) - start_time).total_seconds() * 1000)

            from backend.app.application.use_cases import DiscoveryResult
            return DiscoveryResult(
                trends_found=len(all_trends),
                trends_new=new_count,
                trends_updated=updated_count,
                clusters_created=0,
                duration_ms=duration_ms,
                errors=all_errors,
            )

        result = asyncio.run(_run_discovery())
        progress.update(task, completed=True)

    console.print("[green]✓ Descoberta concluída[/green]")
    console.print(f"  Trends encontrados: {result.trends_found}")
    console.print(f"  Novos: {result.trends_new}")
    console.print(f"  Atualizados: {result.trends_updated}")
    console.print(f"  Clusters: {result.clusters_created}")
    console.print(f"  Duração: {result.duration_ms}ms")
    if result.errors:
        console.print(f"  [yellow]Erros: {len(result.errors)}[/yellow]")
        for e in result.errors[:5]:
            console.print(f"    - {e}")


@discovery.command("list")
@click.option("--limit", type=int, default=20)
@click.option("--source", type=click.Choice(["youtube", "rss", "manual", "all"]), default="all")
def discovery_list(limit: int, source: str):
    """Lista tendências descobertas."""
    async def _list():
        async with get_db_context() as db:
            from sqlalchemy import select, desc
            from sqlalchemy.orm import selectinload
            query = select(TrendItem).options(selectinload(TrendItem.snapshots)).order_by(desc(TrendItem.discovered_at)).limit(limit)
            if source != "all":
                query = query.where(TrendItem.provider == source)
            result = await db.execute(query)
            trends = result.scalars().all()

            table = Table(title=f"Tendências ({source})")
            table.add_column("ID", style="dim", max_width=36)
            table.add_column("Fonte", style="cyan")
            table.add_column("Título", max_width=50)
            table.add_column("Descoberto em", style="green")
            table.add_column("Views", justify="right")

            for t in trends:
                latest_snapshot = t.snapshots[-1] if t.snapshots else None
                table.add_row(
                    str(t.id)[:8] + "...",
                    t.provider,
                    t.title[:48] + "..." if len(t.title) > 48 else t.title,
                    t.discovered_at.strftime("%Y-%m-%d %H:%M"),
                    str(latest_snapshot.views) if latest_snapshot else "N/A",
                )
            console.print(table)

    asyncio.run(_list())


# ──────────────────────────────────────────────
# Candidate Commands
# ──────────────────────────────────────────────

@cli.group()
def candidate():
    """Comandos de candidatos."""
    pass


@candidate.command("score")
@click.argument("cluster_id")
def candidate_score(cluster_id: str):
    """Executa scoring para um cluster."""
    console.print(f"Scoring cluster: [cyan]{cluster_id}[/cyan]")
    result = score_trends_use_case(UUID(cluster_id))
    console.print(f"[green]✓ Candidatos criados: {result.candidates_created}[/green]")
    if result.top_candidate_id:
        console.print(f"  Top candidate: {result.top_candidate_id}")


@candidate.command("list")
@click.option("--date", type=str, help="Data no formato YYYY-MM-DD")
@click.option("--status", type=str, help="Filtrar por status")
def candidate_list(date: Optional[str], status: Optional[str]):
    """Lista candidatos."""
    async def _list():
        async with get_db_context() as db:
            from sqlalchemy import select
            query = select(ContentCandidate)
            if date:
                query = query.where(ContentCandidate.selected_for_date == date)
            if status:
                query = query.where(ContentCandidate.status == status)
            query = query.order_by(ContentCandidate.created_at.desc())
            result = await db.execute(query)
            candidates = result.scalars().all()

            table = Table(title="Candidatos")
            table.add_column("ID", style="dim", max_width=36)
            table.add_column("Cluster", style="dim", max_width=36)
            table.add_column("Score", justify="right", style="cyan")
            table.add_column("Confiança", justify="right", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Data", style="blue")
            table.add_column("Rationale", max_width=50)

            for c in candidates:
                table.add_row(
                    str(c.id)[:8] + "...",
                    str(c.cluster_id)[:8] + "...",
                    f"{c.score:.1f}",
                    f"{c.confidence:.2f}",
                    c.status,
                    str(c.selected_for_date) if c.selected_for_date else "N/A",
                    c.rationale[:48] + "..." if len(c.rationale) > 48 else c.rationale,
                )
            console.print(table)

    asyncio.run(_list())


# ──────────────────────────────────────────────
# Project Commands
# ──────────────────────────────────────────────

@cli.group()
def project():
    """Comandos de projetos de vídeo."""
    pass


@project.command("list")
@click.option("--state", type=str, help="Filtrar por estado")
@click.option("--limit", type=int, default=20)
def project_list(state: Optional[str], limit: int):
    """Lista projetos de vídeo."""
    async def _list():
        async with get_db_context() as db:
            from sqlalchemy import select
            query = select(VideoProject)
            if state:
                query = query.where(VideoProject.state == state)
            query = query.order_by(VideoProject.created_at.desc()).limit(limit)
            result = await db.execute(query)
            projects = result.scalars().all()

            table = Table(title="Projetos de Vídeo")
            table.add_column("ID", style="dim", max_width=36)
            table.add_column("Candidate", style="dim", max_width=36)
            table.add_column("Rev", justify="right")
            table.add_column("Estado", style="cyan")
            table.add_column("Duração (s)", justify="right")
            table.add_column("Criado em", style="green")

            for p in projects:
                table.add_row(
                    str(p.id)[:8] + "...",
                    str(p.candidate_id)[:8] + "...",
                    str(p.revision),
                    p.state,
                    str(p.target_duration_s),
                    p.created_at.strftime("%Y-%m-%d %H:%M"),
                )
            console.print(table)

    asyncio.run(_list())


@project.command("run")
@click.argument("project_id")
@click.option("--step", type=click.Choice([
    "script", "storyboard", "assets", "render", "quality", "approve", "export", "all"
]), default="all")
def project_run(project_id: str, step: str):
    """Executa etapa(s) do pipeline para um projeto."""
    pid = UUID(project_id)
    console.print(f"Executando [cyan]{step}[/cyan] para projeto [cyan]{project_id}[/cyan]")

    steps_map = {
        "script": (generate_script_use_case, "Gerando roteiro..."),
        "storyboard": (create_storyboard_use_case, "Criando storyboard..."),
        "assets": (generate_assets_use_case, "Gerando assets..."),
        "render": (render_video_use_case, "Renderizando vídeo..."),
        "quality": (quality_check_use_case, "Verificando qualidade..."),
        "approve": (request_approval_use_case, "Solicitando aprovação..."),
        "export": (export_package_use_case, "Exportando pacote..."),
    }

    if step == "all":
        for name, (func, desc) in steps_map.items():
            console.print(f"  [yellow]▶ {desc}[/yellow]")
            try:
                result = func(pid)
                console.print(f"    [green]✓ {name} concluído[/green]")
            except Exception as e:
                console.print(f"    [red]✗ {name} falhou: {e}[/red]")
                break
    else:
        func, desc = steps_map[step]
        console.print(f"  [yellow]▶ {desc}[/yellow]")
        try:
            result = func(pid)
            console.print(f"  [green]✓ {step} concluído[/green]")
        except Exception as e:
            console.print(f"  [red]✗ {step} falhou: {e}[/red]")
            sys.exit(1)


# ──────────────────────────────────────────────
# Quota Commands
# ──────────────────────────────────────────────

@cli.group()
def quota():
    """Comandos de quotas diárias."""
    pass


@quota.command("status")
@click.option("--date", type=str, help="Data no formato YYYY-MM-DD (padrão: hoje)")
def quota_status(date: Optional[str]):
    """Mostra status de quota do dia."""
    from backend.app.domain.policies.quotas import timezone_policy
    from datetime import date as date_type
    target_date_str = date or timezone_policy.today_local().isoformat()
    target_date = date_type.fromisoformat(target_date_str)

    async def _status():
        async with get_db_context() as db:
            from sqlalchemy import select
            result = await db.execute(select(DailyQuota).where(DailyQuota.local_date == target_date))
            quota = result.scalar_one_or_none()
            if not quota:
                console.print(f"[yellow]Nenhuma quota registrada para {target_date_str}[/yellow]")
                return

            table = Table(title=f"Quota Diária - {target_date_str}")
            table.add_column("Métrica", style="cyan")
            table.add_column("Valor", style="green", justify="right")
            table.add_column("Limite", style="yellow", justify="right")
            table.add_column("Restante", style="blue", justify="right")

            limit = settings.APP_CANDIDATE_LIMIT_PER_DAY
            remaining = max(0, limit - quota.candidates_created)

            table.add_row("Candidatos criados", str(quota.candidates_created), str(limit), str(remaining))
            table.add_row("Regenerações", str(quota.regen_count), str(settings.APP_MAX_REGENERATIONS_PER_CANDIDATE), "—")

            console.print(table)

            # Mostrar chamadas de fonte
            if quota.source_calls_json:
                console.print("\n[cyan]Chamadas de fonte:[/cyan]")
                for src, count in quota.source_calls_json.items():
                    console.print(f"  {src}: {count}")

    asyncio.run(_status())


@quota.command("reset")
@click.option("--date", type=str, help="Data no formato YYYY-MM-DD (padrão: hoje)")
@click.confirmation_option(prompt="Tem certeza que deseja resetar a quota?")
def quota_reset(date: Optional[str]):
    """Reseta quota do dia (use com cuidado)."""
    from backend.app.domain.policies.quotas import timezone_policy
    from datetime import date as date_type
    target_date_str = date or timezone_policy.today_local().isoformat()
    target_date = date_type.fromisoformat(target_date_str)

    async def _reset():
        async with get_db_context() as db:
            from sqlalchemy import select
            result = await db.execute(select(DailyQuota).where(DailyQuota.local_date == target_date))
            quota = result.scalar_one_or_none()
            if quota:
                quota.candidates_created = 0
                quota.regen_count = 0
                quota.source_calls_json = {}
                await db.commit()
                console.print(f"[green]✓ Quota de {target_date_str} resetada[/green]")
            else:
                console.print(f"[yellow]Nenhuma quota para {target_date_str}[/yellow]")

    asyncio.run(_reset())


# ──────────────────────────────────────────────
# Pipeline Commands
# ──────────────────────────────────────────────

@cli.command()
def daily_pipeline():
    """Executa pipeline diário completo (descoberta → até 2 candidatos)."""
    console.print(Panel("[bold]Executando Pipeline Diário[/bold]"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executando pipeline diário...", total=None)
        result = run_daily_pipeline_use_case()
        progress.update(task, completed=True)

    console.print(f"[green]✓ Pipeline diário concluído[/green]")
    console.print(f"  Candidatos processados: {result.candidates_processed}")


# ──────────────────────────────────────────────
# Provider Commands
# ──────────────────────────────────────────────

@cli.group()
def provider():
    """Comandos de provedores."""
    pass


@provider.command("list")
def provider_list():
    """Lista providers em cache."""
    factory = get_provider_factory()
    cached = factory.get_cached_providers()

    table = Table(title="Providers Instanciados")
    table.add_column("Chave", style="cyan")
    table.add_column("Tipo", style="green")

    for key, provider_type in cached.items():
        table.add_row(key, provider_type)

    console.print(table)


@provider.command("health")
def provider_health():
    """Verifica saúde de todos os providers."""
    import asyncio

    async def _health():
        factory = get_provider_factory()

        providers_to_check = [
            ("Discovery (RSS)", factory.get_discovery_provider("rss")),
            ("Discovery (Manual)", factory.get_discovery_provider("manual")),
            ("Discovery (Mock)", factory.get_discovery_provider("mock")),
            ("LLM (Ollama)", factory.get_llm_provider("ollama")),
            ("LLM (Mock)", factory.get_llm_provider("mock")),
            ("Image (Template)", factory.get_image_provider("template")),
            ("Image (Mock)", factory.get_image_provider("mock")),
            ("Speech (Mock)", factory.get_speech_provider("mock")),
            ("Storage (Local)", factory.get_asset_store()),
            ("Approval (Mock)", factory.get_approval_provider("mock")),
            ("Publisher (Assisted)", factory.get_publisher("assisted")),
        ]

        table = Table(title="Health Check dos Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")

        for name, provider in providers_to_check:
            try:
                healthy = await provider.health_check()
                status = "[green]OK[/green]" if healthy else "[red]FALHOU[/red]"
            except Exception as e:
                status = f"[red]ERRO: {e}[/red]"
            table.add_row(name, status)

        console.print(table)

    asyncio.run(_health())


# ──────────────────────────────────────────────
# Config Command
# ──────────────────────────────────────────────

@cli.command()
def config():
    """Mostra configurações atuais (sem segredos)."""
    table = Table(title="Configuração Ativa")
    table.add_column("Variável", style="cyan")
    table.add_column("Valor", style="green")

    config_vars = [
        ("APP_ENV", settings.APP_ENV),
        ("APP_TIMEZONE", settings.APP_TIMEZONE),
        ("APP_HOST", settings.APP_HOST),
        ("APP_PORT", str(settings.APP_PORT)),
        ("APP_CANDIDATE_LIMIT_PER_DAY", str(settings.APP_CANDIDATE_LIMIT_PER_DAY)),
        ("APP_MAX_REGENERATIONS_PER_CANDIDATE", str(settings.APP_MAX_REGENERATIONS_PER_CANDIDATE)),
        ("APP_ALLOW_PAID_PROVIDERS", str(settings.APP_ALLOW_PAID_PROVIDERS)),
        ("APP_TIKTOK_DIRECT_POST_ENABLED", str(settings.APP_TIKTOK_DIRECT_POST_ENABLED)),
        ("LLM_PROVIDER", settings.LLM_PROVIDER),
        ("OLLAMA_MODEL", settings.OLLAMA_MODEL),
        ("IMAGE_PROVIDER", settings.IMAGE_PROVIDER),
        ("SPEECH_PROVIDER", settings.SPEECH_PROVIDER),
        ("YOUTUBE_ENABLED", str(settings.YOUTUBE_ENABLED)),
        ("RSS_ENABLED", str(settings.RSS_ENABLED)),
        ("TELEGRAM_ENABLED", str(settings.TELEGRAM_ENABLED)),
        ("TIKTOK_PUBLISH_MODE", settings.TIKTOK_PUBLISH_MODE),
        ("DATABASE_URL", settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL),
        ("REDIS_URL", settings.REDIS_URL),
        ("LOCAL_STORAGE_ROOT", str(settings.LOCAL_STORAGE_ROOT)),
    ]

    for name, value in config_vars:
        table.add_row(name, value)

    console.print(table)

    # Verificar violações de custo
    violations = settings.validate_cost_controls()
    if violations:
        console.print("\n[red]! Violações de controle de custo (R$ 0):[/red]")
        for v in violations:
            console.print(f"  - {v}")
    else:
        console.print("\n[green]OK Controles de custo OK (R$ 0)[/green]")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    cli()