from __future__ import annotations

import hashlib
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from lead_hunter.config import BROWSER_PROFILE_DIR
from lead_hunter.models import RawLead

DEFAULT_DORKS = [
    ('site:reddit.com ("willing to pay" OR "will pay" OR "[TASK]") ("python" OR "AI" OR "script" OR "fix" OR "bot")', "Reddit Task/Help"),
    ('site:reddit.com/r/slavelabour "[TASK]" ("python" OR "script" OR "scrape" OR "bot" OR "AI" OR "automate")', "r/slavelabour Tasks"),
    ('site:x.com ("need someone to build" OR "willing to pay" OR "busco programador") ("AI" OR "script" OR "bot" OR "python")', "X/Twitter Help"),
    ('site:upwork.com/freelance-jobs ("fix" OR "bug" OR "script" OR "troubleshooting") ("Python" OR "AI" OR "API")', "Upwork Quick Tasks"),
]


def _find_chrome_executable() -> str | None:
    """Busca un binario real de Chrome/Chromium en el sistema para Patchright."""
    import shutil
    from pathlib import Path

    candidates = [
        "/var/lib/flatpak/app/com.google.Chrome/current/active/files/extra/chrome",
        shutil.which("google-chrome-stable"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    return None


def collect_with_stealth_browser(
    custom_query: str | None = None,
    headless: bool = True,
) -> list[RawLead]:
    """
    Usa Patchright (Playwright parcheado sin fugas de Runtime.enable ni navigator.webdriver)
    para ejecutar búsquedas de personas atoradas con su proyecto que ofrecen pago por tarea.
    """
    leads: list[RawLead] = []
    queries = (
        [(custom_query, "Búsqueda Personalizada")]
        if custom_query
        else DEFAULT_DORKS
    )

    try:
        from patchright.sync_api import sync_playwright

        executable = _find_chrome_executable()
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            launch_kwargs: dict[str, object] = {
                "user_data_dir": str(BROWSER_PROFILE_DIR),
                "headless": headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            }
            if executable:
                launch_kwargs["executable_path"] = executable

            context = p.chromium.launch_persistent_context(**launch_kwargs)
            page = context.new_page()

            for dork, label in queries:
                try:
                    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(dork)}"
                    page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")
                    for res in soup.select(".result")[:10]:
                        a_tag = res.select_one(".result__a")
                        snippet_tag = res.select_one(".result__snippet")
                        if not a_tag:
                            continue
                        title = a_tag.get_text(" ", strip=True)
                        href = a_tag.get("href", "")
                        snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
                        if not href or not title:
                            continue
                        uid = hashlib.md5(href.encode("utf-8")).hexdigest()[:12]
                        leads.append(
                            RawLead(
                                external_id=f"dork:{uid}",
                                source=f"Stealth ({label})",
                                category="ayuda",
                                title=title,
                                description=snippet,
                                url=href,
                            )
                        )
                except Exception:
                    continue

            context.close()
    except Exception:
        pass

    return leads
