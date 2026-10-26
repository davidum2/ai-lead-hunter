from __future__ import annotations

import time
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lead_hunter.analyzer import analyze_lead
from lead_hunter.collectors import (
    collect_freelancer_tasks,
    collect_github_bounties,
    collect_hackernews_help,
    collect_reddit_stuck_people,
    collect_reddit_tasks,
)
from lead_hunter.db import LeadDatabase
from lead_hunter.models import AnalyzedLead, RawLead
from lead_hunter.notifier import generate_markdown_report, notify_desktop
from lead_hunter.stealth_browser import collect_with_stealth_browser

app = typer.Typer(
    name="lead-hunter",
    help="Buscador de personas atoradas con sus proyectos que ofrecen pago por tarea/solución (Software e IA).",
    add_completion=False,
)
console = Console()


def run_collection_cycle(
    use_stealth: bool = True,
    custom_dork: str | None = None,
    use_llm: bool = False,
    min_score: int = 35,
) -> tuple[list[AnalyzedLead], list[AnalyzedLead]]:
    db = LeadDatabase()
    raw_leads: list[RawLead] = []

    with console.status("[bold cyan]Buscando personas que necesitan ayuda puntual y pagan por tarea...[/bold cyan]") as status:
        status.update("[bold cyan]1/5 Escaneando micro-tareas en Reddit (r/slavelabour [TASK], r/DoneDirtCheap, r/forhire, r/HireAProgrammer)...[/bold cyan]")
        raw_leads.extend(collect_reddit_tasks())

        status.update("[bold cyan]2/5 Buscando en todo Reddit personas atoradas con código/IA ofreciendo pago ('willing to pay', 'stuck', 'fix')...[/bold cyan]")
        raw_leads.extend(collect_reddit_stuck_people())

        status.update("[bold cyan]3/5 Escaneando tareas urgentes, scripts y bug-fixes en Freelancer.com...[/bold cyan]")
        raw_leads.extend(collect_freelancer_tasks())

        status.update("[bold cyan]4/5 Escaneando recompensas por issue (GitHub Bounties) y peticiones en Hacker News...[/bold cyan]")
        raw_leads.extend(collect_github_bounties())
        raw_leads.extend(collect_hackernews_help())

        if use_stealth:
            status.update("[bold cyan]5/5 Ejecutando navegador indetectable Patchright para Dorks de tareas y ayuda...[/bold cyan]")
            raw_leads.extend(collect_with_stealth_browser(custom_query=custom_dork))

    analyzed: list[AnalyzedLead] = []
    for raw in raw_leads:
        item = analyze_lead(raw, use_llm=use_llm)
        if item and item.score >= min_score:
            analyzed.append(item)

    analyzed.sort(key=lambda x: x.score, reverse=True)
    new_saved = db.save_leads(analyzed)
    notify_desktop(new_saved)
    all_top = db.list_leads(min_score=min_score, limit=50)
    return new_saved, all_top


def _render_table(leads: list[AnalyzedLead], title: str) -> None:
    table = Table(title=title, show_lines=False, header_style="bold magenta")
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Score", justify="center", style="bold green")
    table.add_column("Fuente", style="yellow", no_wrap=True)
    table.add_column("Tipo", style="blue", no_wrap=True)
    table.add_column("Problema / Tarea Solicitada", style="white")
    table.add_column("Pago / Presupuesto", style="green")
    table.add_column("Señales / Skills", style="cyan")

    for l in leads:
        signals = ", ".join((l.buying_signals[:2] + l.matched_ai_skills[:2] + l.matched_dev_skills[:2]))
        score_str = f"{l.score}"
        if l.score >= 75:
            score_str = f"[bold bright_green]🔥 {l.score}[/bold bright_green]"
        elif l.score >= 55:
            score_str = f"[bold yellow]⭐ {l.score}[/bold yellow]"
        table.add_row(
            str(l.id or "-"),
            score_str,
            l.source,
            l.category,
            l.title[:65],
            l.budget_detected[:22],
            signals[:34],
        )
    console.print(table)


@app.command("scan")
def scan_command(
    stealth: bool = typer.Option(True, "--stealth/--no-stealth", help="Usar navegador indetectable Patchright para Dorks."),
    dork: str | None = typer.Option(None, "--dork", "-q", help="Dork o consulta personalizada para el navegador indetectable."),
    llm: bool = typer.Option(False, "--llm", help="Enriquecer propuestas con Gemini/OpenAI si hay API key configurada."),
    min_score: int = typer.Option(40, "--min-score", "-m", help="Puntaje mínimo (0-100) para guardar y mostrar."),
    limit: int = typer.Option(20, "--limit", "-n", help="Cantidad de resultados a mostrar en tabla."),
    reset: bool = typer.Option(False, "--reset", help="Limpiar la base de datos antes de escanear."),
) -> None:
    """Escanea foros y plataformas buscando personas atoradas que pagan por tarea/solución."""
    db = LeadDatabase()
    if reset and db.db_path.exists():
        db.db_path.unlink()
        db = LeadDatabase()

    new_leads, top_leads = run_collection_cycle(
        use_stealth=stealth, custom_dork=dork, use_llm=llm, min_score=min_score
    )
    report_path = generate_markdown_report(top_leads)
    console.print(
        f"\n[bold green]✔ Escaneo completado:[/bold green] [bold]{len(new_leads)}[/bold] tareas/solicitudes nuevas guardadas "
        f"(Total calificadas en base de datos: [bold]{len(top_leads)}[/bold])."
    )
    console.print(f"[bold cyan]📄 Reporte diario actualizado en:[/bold cyan] {report_path}\n")
    _render_table(top_leads[:limit], f"Top {min(limit, len(top_leads))} Personas que Necesitan Ayuda / Pago por Tarea")
    console.print("\n💡 Usa [bold yellow]lead-hunter show <ID>[/bold yellow] para ver el problema completo y copiar el mensaje directo.")


@app.command("list")
def list_command(
    min_score: int = typer.Option(40, "--min-score", "-m", help="Puntaje mínimo."),
    status: str | None = typer.Option(None, "--status", "-s", help="Filtrar por estado: nuevo, favorito, contactado, descartado."),
    category: str | None = typer.Option(None, "--category", "-c", help="Filtrar por tipo: tarea, ayuda, bounty."),
    limit: int = typer.Option(25, "--limit", "-n", help="Número máximo de prospectos a listar."),
) -> None:
    """Lista las tareas y solicitudes de ayuda guardadas ordenadas por urgencia y puntaje."""
    db = LeadDatabase()
    leads = db.list_leads(min_score=min_score, status=status, category=category, limit=limit)
    if not leads:
        console.print("[yellow]No se encontraron tareas con esos filtros. Ejecuta 'lead-hunter scan' primero.[/yellow]")
        return
    _render_table(leads, f"Tareas y Solicitudes de Ayuda Guardadas ({len(leads)})")


@app.command("show")
def show_command(lead_id: int = typer.Argument(..., help="ID de la oportunidad a inspeccionar.")) -> None:
    """Muestra el problema completo del cliente, el link directo y el mensaje listo para enviar."""
    db = LeadDatabase()
    lead = db.get_lead(lead_id)
    if not lead:
        console.print(f"[red]No existe ninguna oportunidad con ID {lead_id}.[/red]")
        raise typer.Exit(1)

    ai_skills = ", ".join(lead.matched_ai_skills) or "Ninguno específico"
    dev_skills = ", ".join(lead.matched_dev_skills) or "Ninguno específico"
    signals = ", ".join(lead.buying_signals) or "Tarea / Proyecto"

    info = (
        f"[bold]Título:[/bold] {lead.title}\n"
        f"[bold]Fuente:[/bold] {lead.source} ({lead.category}) | [bold]Estado:[/bold] {lead.status}\n"
        f"[bold]Usuario/Cliente:[/bold] {lead.author or 'N/A'} | [bold]Fecha:[/bold] {lead.published_at}\n"
        f"[bold]Score:[/bold] [bold green]{lead.score}/100[/bold green] | [bold]Pago / Presupuesto:[/bold] [bold yellow]{lead.budget_detected}[/bold yellow]\n"
        f"[bold]Señales de urgencia/pago:[/bold] [magenta]{signals}[/magenta]\n"
        f"[bold]Skills IA:[/bold] [cyan]{ai_skills}[/cyan] | [bold]Skills Software:[/bold] [cyan]{dev_skills}[/cyan]\n"
        f"[bold]Enlace directo:[/bold] [underline bright_blue]{lead.url}[/underline bright_blue]\n\n"
        f"[bold]Lo que necesita el cliente:[/bold]\n{lead.description[:1500]}"
    )
    console.print(Panel(info, title=f"🛠️ Tarea / Solicitud de Ayuda #{lead.id}", border_style="cyan"))
    console.print(
        Panel(
            lead.pitch,
            title=f"💬 Mensaje Directo (DM) Listo para Enviar ({'Español' if lead.language == 'es' else 'Inglés'})",
            border_style="green",
        )
    )


@app.command("status")
def status_command(
    lead_id: int = typer.Argument(..., help="ID de la tarea."),
    new_status: str = typer.Argument(..., help="Nuevo estado: nuevo, favorito, contactado, descartado."),
) -> None:
    """Actualiza el estado de seguimiento de una tarea (nuevo, favorito, contactado, descartado)."""
    db = LeadDatabase()
    if db.update_status(lead_id, new_status):
        console.print(f"[green]✔ Tarea #{lead_id} marcada como '{new_status}'.[/green]")
    else:
        console.print(f"[red]No se encontró la tarea #{lead_id}.[/red]")


@app.command("daemon")
def daemon_command(
    interval_minutes: int = typer.Option(30, "--interval", "-i", help="Minutos entre cada escaneo automático."),
    stealth: bool = typer.Option(True, "--stealth/--no-stealth", help="Incluir navegador indetectable en cada ciclo."),
    min_score: int = typer.Option(50, "--min-score", "-m", help="Puntaje mínimo."),
) -> None:
    """Ejecuta el buscador en segundo plano de forma continua con alertas de escritorio."""
    console.print(
        Panel(
            f"Buscando personas atoradas / tareas pagadas cada [bold]{interval_minutes} minutos[/bold].\n"
            f"Recibirás notificaciones en tu escritorio Linux Mint cuando alguien publique una tarea.",
            title="🤖 AI Lead Hunter - Modo Segundo Plano (Daemon)",
            border_style="bright_green",
        )
    )
    try:
        while True:
            new_leads, top_leads = run_collection_cycle(use_stealth=stealth, min_score=min_score)
            report_path = generate_markdown_report(top_leads)
            console.print(
                f"[dim]{time.strftime('%Y-%m-%d %H:%M:%S')}[/dim] Ciclo completado: "
                f"[bold green]{len(new_leads)}[/bold green] nuevas tareas | Reporte: {report_path}"
            )
            time.sleep(interval_minutes * 60)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoreo en segundo plano detenido por el usuario.[/yellow]")


if __name__ == "__main__":
    app()
