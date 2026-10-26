from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import httpx

from lead_hunter.config import REPORTS_DIR, settings
from lead_hunter.models import AnalyzedLead


def notify_desktop(new_leads: list[AnalyzedLead]) -> None:
    """Envía notificación nativa al escritorio de Linux Mint para prospectos de alto puntaje."""
    high_value = [l for l in new_leads if l.score >= settings.min_score_notify]
    if not high_value:
        return

    top = high_value[0]
    if shutil.which("notify-send"):
        title = f"🎯 {len(high_value)} nuevas oportunidades detectadas (Top: {top.score}/100)"
        body = f"[{top.source}] {top.title[:85]}\nPresupuesto: {top.budget_detected}"
        try:
            subprocess.run(
                ["notify-send", "-u", "normal", "-i", "dialog-information", title, body],
                check=False,
                timeout=5,
            )
        except Exception:
            pass

    if settings.telegram_bot_token and settings.telegram_chat_id:
        lines = [f"🎯 *{len(high_value)} Nuevas Oportunidades de Software / IA*\n"]
        for lead in high_value[:5]:
            lines.append(
                f"• *[{lead.score}/100]* [{lead.title[:70]}]({lead.url}) ({lead.source}) — `{lead.budget_detected}`"
            )
        try:
            httpx.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": "\n".join(lines),
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=10.0,
            )
        except Exception:
            pass


def generate_markdown_report(leads: list[AnalyzedLead]) -> Path:
    """Genera un reporte diario en Markdown con los mejores prospectos y propuestas listas."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"reporte_{today_str}.md"

    lines: list[str] = [
        f"# 🎯 Reporte de Oportunidades de Software e IA Aplicada ({today_str})",
        "",
        f"- **Perfil:** {settings.profile.name} — *{settings.profile.headline_es}*",
        f"- **Total de oportunidades en este reporte:** {len(leads)}",
        "",
        "## 📊 Top Oportunidades Priorizadas",
        "",
        "| ID | Score | Fuente | Categoría | Título | Presupuesto | Skills IA / Dev |",
        "|---:|:-----:|:-------|:----------|:-------|:------------|:----------------|",
    ]

    for lead in leads[:30]:
        skills = ", ".join((lead.matched_ai_skills + lead.matched_dev_skills)[:5])
        safe_title = lead.title.replace("|", "-").strip()[:70]
        lines.append(
            f"| {lead.id or '-'} | **{lead.score}/100** | {lead.source} | `{lead.category}` | [{safe_title}]({lead.url}) | {lead.budget_detected} | {skills} |"
        )

    lines.extend(["", "---", "", "## ✉️ Propuestas Personalizadas Listas para Enviar (Top 10)", ""])

    for lead in leads[:10]:
        ai_str = ", ".join(lead.matched_ai_skills) or "N/A"
        dev_str = ", ".join(lead.matched_dev_skills) or "N/A"
        lines.extend(
            [
                f"### [{lead.score}/100] #{lead.id or '-'} — {lead.title}",
                f"- **Fuente:** {lead.source} (`{lead.category}`) | **Autor/Empresa:** `{lead.author or 'N/A'}`",
                f"- **Enlace directo:** {lead.url}",
                f"- **Presupuesto / Señal:** `{lead.budget_detected}`",
                f"- **Coincidencia IA:** `{ai_str}` | **Coincidencia Dev:** `{dev_str}`",
                f"- **Resumen:** {lead.summary}",
                "",
                "**Propuesta sugerida (Pitch):**",
                "```text",
                lead.pitch,
                "```",
                "",
            ]
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
