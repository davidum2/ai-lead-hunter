from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reportes"
BROWSER_PROFILE_DIR = DATA_DIR / "browser_profile"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class UserProfile:
    name: str = "David"
    github_user: str = "davidum2"
    email: str = "davidum215@gmail.com"
    headline_es: str = (
        "Desarrollador de Software Políglota & Máster en IA Aplicada"
    )
    headline_en: str = (
        "Polyglot Software Developer & M.Sc. in Applied AI"
    )
    # Señales de que alguien está atorado, necesita destrabar su proyecto o pide ayuda puntual
    pain_signals: list[str] = field(
        default_factory=lambda: [
            "need help",
            "help me",
            "help with",
            "stuck",
            "struggling",
            "fix",
            "fixing",
            "bug",
            "error",
            "issue",
            "broken",
            "not working",
            "doesn't work",
            "troubleshoot",
            "debug",
            "debugging",
            "urgent",
            "asap",
            "quick",
            "small project",
            "small task",
            "simple script",
            "automate",
            "scrape",
            "integrate",
            "build a script",
            "build a bot",
            "need someone to",
            "looking for someone to",
            "anyone available",
            "ayuda",
            "atorado",
            "arreglar",
            "reparar",
            "problema con",
            "urgente",
            "tarea",
            "alguien que sepa",
            "necesito alguien",
        ]
    )
    # Señales de pago por tarea / proyecto corto / recompensa
    task_payment_signals: list[str] = field(
        default_factory=lambda: [
            "[task]",
            "[hiring]",
            "willing to pay",
            "will pay",
            "can pay",
            "paying",
            "pay per",
            "fixed price",
            "one-off",
            "one time",
            "quick task",
            "bounty",
            "budget",
            "paypal",
            "crypto",
            "usdt",
            "venmo",
            "wise",
            "zelle",
            "cashapp",
            "pago",
            "presupuesto",
            "doy",
            "ofrezco",
        ]
    )
    ai_keywords: list[str] = field(
        default_factory=lambda: [
            "ai",
            "ia",
            "llm",
            "gpt",
            "chatgpt",
            "openai",
            "claude",
            "anthropic",
            "gemini",
            "ollama",
            "rag",
            "agent",
            "agents",
            "agente",
            "langchain",
            "langgraph",
            "crewai",
            "machine learning",
            "deep learning",
            "nlp",
            "computer vision",
            "ocr",
            "pytorch",
            "tensorflow",
            "embeddings",
            "vector db",
            "chromadb",
            "pinecone",
            "chatbot",
            "voice ai",
            "whisper",
            "automation",
            "automatización",
            "n8n",
            "make.com",
            "zapier",
            "mcp",
            "prompt",
        ]
    )
    dev_keywords: list[str] = field(
        default_factory=lambda: [
            "python",
            "typescript",
            "javascript",
            "node",
            "nodejs",
            "react",
            "nextjs",
            "fastapi",
            "django",
            "flask",
            "backend",
            "frontend",
            "fullstack",
            "api",
            "webhook",
            "scraper",
            "scraping",
            "playwright",
            "selenium",
            "puppeteer",
            "bot",
            "telegram",
            "discord",
            "whatsapp",
            "saas",
            "mvp",
            "webapp",
            "script",
            "postgresql",
            "sql",
            "supabase",
            "firebase",
            "docker",
            "linux",
            "bash",
            "rust",
            "golang",
            "java",
            "c++",
            "php",
        ]
    )
    # Excluir ofertas de empleo corporativo, diseño gráfico y otros freelancers ofreciéndose
    exclude_signals: list[str] = field(
        default_factory=lambda: [
            "[for hire]",
            "[offer]",
            "for hire:",
            "available for work",
            "looking for work",
            "ofrezco mis servicios",
            "willing to relocate",
            "remote: yes",
            "location:",
            "show hn:",
            "launch hn:",
            "tell hn:",
            "graphic designer",
            "print-design",
            "adobe illustrator",
            "photoshop",
            "virtual assistant",
            "video editor",
            "full-time",
            "full time",
            "/yr",
            "per year",
            "annual salary",
            "401k",
            "health insurance",
            "equal opportunity employer",
            "years of experience required",
            "senior software engineer @",
            "principal software engineer",
            "staff engineer",
            "tech lead",
        ]
    )


@dataclass
class Settings:
    db_path: Path = DATA_DIR / "leads.db"
    min_score_notify: int = int(os.getenv("MIN_SCORE_NOTIFY", "65"))
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
    profile: UserProfile = field(default_factory=UserProfile)


settings = Settings()
