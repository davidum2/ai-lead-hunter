from __future__ import annotations

from datetime import datetime, timezone
import feedparser
import httpx

from lead_hunter.models import RawLead

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def collect_reddit_tasks(limit_per_sub: int = 30) -> list[RawLead]:
    """Recolecta tareas pagadas ([TASK] y [Hiring]) en subreddits de micro-tareas y proyectos rápidos."""
    subreddits = [
        ("slavelabour", "TASK", "tarea"),
        ("DoneDirtCheap", "", "tarea"),
        ("forhire", "Hiring", "tarea"),
        ("HireAProgrammer", "", "tarea"),
        ("freelance_forhire", "Hiring", "tarea"),
    ]
    leads: list[RawLead] = []
    with httpx.Client(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
        for sub, required_tag, cat in subreddits:
            url = f"https://www.reddit.com/r/{sub}/new.json?limit={limit_per_sub}"
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    feed = feedparser.parse(f"https://www.reddit.com/r/{sub}/new/.rss")
                    for entry in feed.entries[:limit_per_sub]:
                        title = entry.get("title", "")
                        if required_tag and required_tag.lower() not in title.lower():
                            continue
                        if "[offer]" in title.lower() or "[for hire]" in title.lower():
                            continue
                        leads.append(
                            RawLead(
                                external_id=f"reddit:{entry.get('id', entry.get('link', ''))}",
                                source=f"Reddit r/{sub}",
                                category=cat,
                                title=title,
                                description=entry.get("summary", ""),
                                url=entry.get("link", ""),
                                author=entry.get("author", ""),
                                published_at=entry.get("published", datetime.now(timezone.utc).isoformat()),
                            )
                        )
                    continue

                data = resp.json()
                children = data.get("data", {}).get("children", [])
                for item in children:
                    post = item.get("data", {})
                    title = post.get("title", "")
                    if required_tag and required_tag.lower() not in title.lower():
                        continue
                    if "[offer]" in title.lower() or "[for hire]" in title.lower():
                        continue
                    created_utc = post.get("created_utc")
                    pub_iso = (
                        datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
                        if created_utc
                        else datetime.now(timezone.utc).isoformat()
                    )
                    leads.append(
                        RawLead(
                            external_id=f"reddit:{post.get('id')}",
                            source=f"Reddit r/{sub}",
                            category=cat,
                            title=title,
                            description=post.get("selftext", ""),
                            url=f"https://www.reddit.com{post.get('permalink', '')}",
                            author=post.get("author", ""),
                            published_at=pub_iso,
                        )
                    )
            except Exception:
                continue
    return leads


def collect_reddit_stuck_people(limit_per_query: int = 20) -> list[RawLead]:
    """
    Busca en Reddit personas que están atoradas con su código/proyecto de IA/automatización
    y ofrecen pago por tarea o ayuda puntual (vía RSS para evitar bloqueos de API).
    """
    from urllib.parse import quote_plus

    rss_urls = [
        (
            f"https://www.reddit.com/r/slavelabour/search.rss?q={quote_plus('TASK (python OR script OR bot OR AI OR scrape OR automation OR bug OR api)')}&restrict_sr=on&sort=new&t=week",
            "Reddit r/slavelabour",
            "tarea",
        ),
        (
            f"https://www.reddit.com/r/DoneDirtCheap/search.rss?q={quote_plus('python OR script OR bot OR AI OR scrape OR automation OR fix')}&restrict_sr=on&sort=new&t=week",
            "Reddit r/DoneDirtCheap",
            "tarea",
        ),
        (
            f"https://www.reddit.com/r/forhire/search.rss?q={quote_plus('Hiring (script OR bug OR fix OR bot OR python OR AI OR automation OR quick)')}&restrict_sr=on&sort=new&t=week",
            "Reddit r/forhire",
            "tarea",
        ),
        (
            f"https://www.reddit.com/search.rss?q={quote_plus('(\"willing to pay\" OR \"will pay\" OR \"need someone to fix\") AND (python OR script OR bot OR AI OR bug OR automation)')}&sort=new&t=week&type=link",
            "Reddit (Stuck/Help)",
            "ayuda",
        ),
    ]
    leads: list[RawLead] = []
    for url, source_label, cat in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit_per_query]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                if "/comments/" not in link:
                    continue
                if "[for hire]" in title.lower() or "[offer]" in title.lower():
                    continue
                leads.append(
                    RawLead(
                        external_id=f"reddit_rss:{entry.get('id', link)}",
                        source=source_label,
                        category=cat,
                        title=title,
                        description=entry.get("summary", ""),
                        url=link,
                        author=entry.get("author", ""),
                        published_at=entry.get("published", datetime.now(timezone.utc).isoformat()),
                    )
                )
        except Exception:
            continue
    return leads


def collect_freelancer_tasks(limit: int = 35) -> list[RawLead]:
    """
    Consulta la API pública de Freelancer.com enfocada en tareas puntuales:
    corregir errores (bug fix), scripts rápidos, bots, web scraping e integraciones de IA.
    """
    leads: list[RawLead] = []
    url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
    queries = [
        "fix bug error python script automation bot",
        "AI LLM RAG agent chatbot n8n integration",
        "scraping playwrightapi quick task help",
    ]
    with httpx.Client(headers=HEADERS, timeout=15.0) as client:
        for q in queries:
            try:
                params = {
                    "query": q,
                    "limit": limit // len(queries) + 5,
                    "full_description": "true",
                    "job_details": "true",
                }
                resp = client.get(url, params=params)
                if resp.status_code != 200:
                    continue
                projects = resp.json().get("result", {}).get("projects", [])
                for p in projects:
                    pid = p.get("id")
                    title = p.get("title", "")
                    desc = p.get("description") or p.get("preview_description") or ""
                    seo_url = p.get("seo_url", "")
                    stats = p.get("budget", {})
                    currency = p.get("currency", {}).get("code", "USD")
                    min_b = stats.get("minimum")
                    max_b = stats.get("maximum")
                    budget_hint = f"${min_b} - ${max_b} {currency}" if min_b and max_b else ""
                    jobs = [j.get("name", "") for j in (p.get("jobs") or []) if isinstance(j, dict)]
                    leads.append(
                        RawLead(
                            external_id=f"freelancer:{pid}",
                            source="Freelancer (Tarea)",
                            category="tarea",
                            title=title,
                            description=desc,
                            url=f"https://www.freelancer.com/projects/{seo_url}" if seo_url else f"https://www.freelancer.com/projects/{pid}",
                            budget_hint=budget_hint,
                            tags=jobs,
                        )
                    )
            except Exception:
                continue
    return leads


def collect_github_bounties(limit: int = 25) -> list[RawLead]:
    """Busca issues abiertos donde ofrecen pago directo (bounties / $) por resolver un bug o feature puntual."""
    leads: list[RawLead] = []
    url = "https://api.github.com/search/issues"
    params = {
        "q": 'is:issue is:open label:bounty ("$" OR "AI" OR "python" OR "typescript" OR "bug" OR "fix")',
        "sort": "created",
        "order": "desc",
        "per_page": limit,
    }
    try:
        with httpx.Client(headers=HEADERS, timeout=15.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                for item in resp.json().get("items", []):
                    labels = [lb.get("name", "") for lb in item.get("labels", [])]
                    leads.append(
                        RawLead(
                            external_id=f"gh_bounty:{item.get('id')}",
                            source="GitHub Bounty",
                            category="bounty",
                            title=f"[Bounty] {item.get('title', '')}",
                            description=item.get("body") or "",
                            url=item.get("html_url", ""),
                            author=item.get("user", {}).get("login", ""),
                            published_at=item.get("created_at", ""),
                            tags=labels,
                        )
                    )
    except Exception:
        pass
    return leads


def collect_hackernews_help(limit: int = 20) -> list[RawLead]:
    """Busca en Hacker News personas pidiendo ayuda puntual o buscando un freelancer para un proyecto específico."""
    leads: list[RawLead] = []
    queries = [
        ("need help with python OR AI OR LLM OR script", "story"),
        ("looking for freelancer OR contractor AI python", "comment"),
    ]
    with httpx.Client(headers=HEADERS, timeout=15.0) as client:
        for q, tag in queries:
            try:
                resp = client.get(
                    "https://hn.algolia.com/api/v1/search_by_date",
                    params={"query": q, "tags": tag, "hitsPerPage": limit // len(queries)},
                )
                if resp.status_code != 200:
                    continue
                hits = resp.json().get("hits", [])
                for h in hits:
                    obj_id = h.get("objectID", "")
                    text = h.get("comment_text") or h.get("story_text") or h.get("title") or ""
                    title = h.get("title") or h.get("story_title") or f"HN Task ({h.get('author', 'user')})"
                    if not text:
                        continue
                    first_line = text.replace("<p>", " ").split(".")[0][:110]
                    if tag == "comment":
                        title = f"[HN] {first_line}"
                    leads.append(
                        RawLead(
                            external_id=f"hn:{obj_id}",
                            source="Hacker News",
                            category="ayuda",
                            title=title,
                            description=text,
                            url=f"https://news.ycombinator.com/item?id={obj_id}",
                            author=h.get("author", ""),
                            published_at=h.get("created_at", datetime.now(timezone.utc).isoformat()),
                        )
                    )
            except Exception:
                continue
    return leads
