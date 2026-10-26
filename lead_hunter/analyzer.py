from __future__ import annotations

import re
from html import unescape

from lead_hunter.config import settings
from lead_hunter.models import AnalyzedLead, RawLead

BUDGET_REGEX = re.compile(
    r"(?:\$\s?\d[\d,.]*(?:\s?[-–to]+\s?\$\s?\d[\d,.]*)?(?:\s?(?:usd|USD|eur|EUR|/hr|/h|per hour|per task|flat))?|\d+\s?(?:USD|EUR|€|\$|USDT)\b)",
    re.IGNORECASE,
)

# Rechazar sueldos anuales tipo $120,000 o $150k que indican vacante de empleo fijo y no tarea puntual
CORPORATE_SALARY_REGEX = re.compile(
    r"\$\s?(?:[5-9]\d,\d{3}|[1-9]\d{2},\d{3}|\d{2,3}\s?k\b)",
    re.IGNORECASE,
)

SPANISH_WORDS = {
    "busco",
    "necesito",
    "programador",
    "desarrollador",
    "proyecto",
    "automatización",
    "inteligencia",
    "presupuesto",
    "sistema",
    "aplicación",
    "ayuda",
    "atorado",
    "arreglar",
    "error",
    "tarea",
    "pago",
}


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_language(text: str) -> str:
    tokens = set(re.findall(r"[a-záéíóúñ]+", text.lower()))
    es_hits = len(tokens.intersection(SPANISH_WORDS))
    return "es" if es_hits >= 2 else "en"


def extract_budget(text: str, hint: str = "") -> str:
    if hint:
        return hint
    matches = BUDGET_REGEX.findall(text)
    if matches:
        unique: list[str] = []
        for m in matches[:2]:
            m_clean = m.strip()
            if m_clean not in unique:
                unique.append(m_clean)
        return " | ".join(unique)
    return "A convenir / Por tarea"


def _match_keywords(text_lower: str, keywords: list[str]) -> list[str]:
    matched: list[str] = []
    for kw in keywords:
        if len(kw) <= 3:
            pattern = rf"\b{re.escape(kw.lower())}\b"
            if re.search(pattern, text_lower):
                matched.append(kw)
        else:
            if kw.lower() in text_lower:
                matched.append(kw)
    return matched


def build_heuristic_pitch(
    lead: RawLead,
    lang: str,
    ai_skills: list[str],
    dev_skills: list[str],
    pain_signals: list[str],
    budget: str,
) -> str:
    profile = settings.profile
    skills_combined = ai_skills[:3] + dev_skills[:3]
    skills_str = ", ".join(skills_combined) if skills_combined else "Python, IA aplicada, APIs y automatización"

    if lang == "es":
        return (
            f"¡Hola{f' {lead.author}' if lead.author else ''}! 👋\n\n"
            f"Leí tu publicación («{lead.title[:85]}») y veo exactamente dónde necesitas apoyo.\n"
            f"Soy desarrollador en varios lenguajes con Máster en IA Aplicada y experiencia directa en {skills_str}.\n\n"
            f"Puedo entrar a revisarlo hoy mismo, destrabar el problema / completar la tarea y entregártelo funcionando sin rodeos.\n"
            f"Si quieres, pásame los detalles o el repositorio por mensaje directo y te digo en cuánto tiempo te lo tengo listo.\n\n"
            f"— {profile.name} | GitHub: https://github.com/{profile.github_user} | {profile.email}"
        )

    skills_str_en = ", ".join(skills_combined) if skills_combined else "Python, Applied AI, APIs & automation"
    return (
        f"Hey{f' {lead.author}' if lead.author else ''}! 👋\n\n"
        f"I just read your post (\"{lead.title[:85]}\") and can help you knock this out right away.\n"
        f"I'm a polyglot software developer with a Master's in Applied AI and hands-on experience in {skills_str_en}.\n\n"
        f"Whether you're stuck on a tricky bug, need a clean script/automation, or want a working integration fast, "
        f"I can jump in today and get it working for you.\n\n"
        f"Feel free to DM me the details or repo link and we can get started immediately.\n\n"
        f"— {profile.name} | GitHub: https://github.com/{profile.github_user} | {profile.email}"
    )


def try_llm_pitch(lead: RawLead, base_pitch: str, lang: str) -> str:
    if settings.gemini_api_key:
        try:
            from google import genai

            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = (
                f"Act as {settings.profile.name} ({settings.profile.headline_en}, "
                f"GitHub: github.com/{settings.profile.github_user}, Email: {settings.profile.email}).\n"
                f"Someone posted asking for help with a task/project they are stuck on or need built:\n"
                f"Title: {lead.title}\n"
                f"Description: {lead.description[:1000]}\n"
                f"Write a friendly, direct, problem-solving DM in {'Spanish' if lang == 'es' else 'English'} "
                f"(max 100 words) offering to jump in today and solve this specific task."
            )
            resp = client.models.generate_content(
                model=settings.gemini_model, contents=prompt
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception:
            pass
    return base_pitch


def analyze_lead(raw: RawLead, use_llm: bool = False) -> AnalyzedLead | None:
    title_clean = clean_text(raw.title)
    desc_clean = clean_text(raw.description)
    full_text = f"{title_clean}\n{desc_clean} {' '.join(raw.tags)}"
    text_lower = full_text.lower()
    title_lower = title_clean.lower()

    # 1. Excluir ofertas de empleo corporativo y autopromoción [For Hire]
    for excl in settings.profile.exclude_signals:
        if excl in title_lower or excl in text_lower:
            return None

    # Excluir si parece salario anual corporativo ($120,000, $150k, etc.)
    if CORPORATE_SALARY_REGEX.search(full_text):
        return None

    ai_skills = _match_keywords(text_lower, settings.profile.ai_keywords)
    dev_skills = _match_keywords(text_lower, settings.profile.dev_keywords)
    pain_hits = _match_keywords(text_lower, settings.profile.pain_signals)
    task_pay_hits = _match_keywords(text_lower, settings.profile.task_payment_signals)
    budget = extract_budget(full_text, raw.budget_hint)

    # Debe tener relación con software o IA
    if not ai_skills and not dev_skills:
        return None

    # Debe tener al menos una señal de problema/ayuda o de pago por tarea/freelance/bounty
    if not pain_hits and not task_pay_hits and raw.category not in ("tarea", "bounty", "ayuda"):
        return None

    # Cálculo de Score (0–100) enfocado en: "Persona atorada / Tarea puntual + Pago + IA/Software"
    score = 10
    if pain_hits:
        score += min(32, 14 + len(pain_hits) * 5)
    if task_pay_hits:
        score += min(25, 10 + len(task_pay_hits) * 5)
    if budget != "A convenir / Por tarea":
        score += 15
    if ai_skills:
        score += min(20, 10 + len(ai_skills) * 4)
    if dev_skills:
        score += min(15, 6 + len(dev_skills) * 3)

    score = max(0, min(100, score))

    lang = detect_language(full_text)
    summary = desc_clean[:280] + ("..." if len(desc_clean) > 280 else "")
    buying_combined = list(dict.fromkeys(pain_hits + task_pay_hits))
    pitch = build_heuristic_pitch(raw, lang, ai_skills, dev_skills, pain_hits, budget)
    if use_llm and score >= 70:
        pitch = try_llm_pitch(raw, pitch, lang)

    return AnalyzedLead(
        external_id=raw.external_id,
        source=raw.source,
        category=raw.category,
        title=title_clean,
        description=desc_clean,
        url=raw.url,
        author=raw.author,
        published_at=raw.published_at,
        score=score,
        matched_ai_skills=ai_skills,
        matched_dev_skills=dev_skills,
        buying_signals=buying_combined,
        budget_detected=budget,
        language=lang,
        summary=summary,
        pitch=pitch,
    )
