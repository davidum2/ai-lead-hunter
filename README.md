# 🎯 AI Lead Hunter (`lead-hunter`)

Herramienta CLI y servicio en segundo plano diseñado para encontrar clientes, contratos freelance, bounties y proyectos remotos de **Desarrollo de Software e Inteligencia Artificial Aplicada**.

## 🚀 Características Principales

1. **Recolección Multicanal (5 conectores integrados):**
   - **Comunidades y Foros:** Reddit (`r/forhire`, `r/slavelabour`, `r/HireAProgrammer`, `r/freelance_forhire`) filtrando exclusivamente publicaciones `[Hiring]` / `[TASK]`, y **Hacker News** (Algolia API en tiempo real).
   - **Plataformas Freelance y Bounties:** API pública de **Freelancer.com** (proyectos activos con presupuesto) y **GitHub Bounties** (issues pagados con etiqueta `bounty`).
   - **Portales Remotos de IA/Software:** **RemoteOK**, **Remotive** y **WeWorkRemotely**.
   - **Navegador Indetectable (Patchright + Google Chrome):** Ejecuta *Dorks* especializados en **LinkedIn, Upwork, Wellfound y Reddit** sin activar `navigator.webdriver` ni fugas de protocolo CDP (`Runtime.enable`).
2. **Calificación Inteligente (Score 0–100):**
   - Pondera coincidencias con tu perfil de **Máster en IA Aplicada** (`LLM`, `RAG`, `Agents`, `LangChain`, `Machine Learning`, `Python`, `Automation`, `MCP`, etc.) y **Desarrollo de Software Políglota** (`TypeScript`, `React`, `FastAPI`, `Node.js`, `Go`, `Rust`, `Docker`, etc.), además de detectar presupuesto explícito (`$`, `USD`, `hourly`) y señales de urgencia.
3. **Generador Automático de Propuestas (Pitch Bilingüe):**
   - Detecta automáticamente si la publicación está en **español o inglés** y redacta un borrador de contacto personalizado listo para copiar y enviar (con soporte opcional para enriquecimiento vía Gemini API).
4. **Notificaciones de Escritorio y Reportes Diarios:**
   - Envía alertas nativas a tu escritorio **Linux Mint** (`notify-send`) cuando detecta oportunidades de alto valor y genera reportes diarios en Markdown dentro de `reportes/`.

---

## 💻 Uso desde la Terminal

El comando `lead-hunter` ya está instalado globalmente en `~/.local/bin/lead-hunter`:

```bash
# 1. Ejecutar un escaneo completo (APIs + Navegador indetectable Patchright)
lead-hunter scan

# 2. Escaneo rápido (solo APIs/RSS, sin abrir navegador)
lead-hunter scan --no-stealth

# 3. Buscar con un Dork personalizado en el navegador indetectable
lead-hunter scan --dork 'site:linkedin.com/posts "busco desarrollador" "IA"'

# 4. Ver los detalles completos y copiar el Pitch personalizado de una oportunidad
lead-hunter show <ID>

# 5. Listar oportunidades guardadas en la base de datos SQLite
lead-hunter list --min-score 60 --category freelance

# 6. Actualizar el estado de un prospecto (nuevo, favorito, contactado, descartado)
lead-hunter status <ID> contactado

# 7. Ejecutar en segundo plano continuamente (ej. cada 30 minutos)
lead-hunter daemon --interval 30
```
