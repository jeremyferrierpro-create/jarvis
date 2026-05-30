# -*- coding: utf-8 -*-
"""
Moteur développeur fullstack senior pour JARVIS.
Scaffolds professionnels, validation de code, détection de stack.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

_MIN_CSS_CHARS = 400
_MIN_HTML_CHARS = 350
_MIN_JS_CHARS = 80
_MIN_PY_CHARS = 100


def detecter_stack(texte: str) -> str:
    t = (texte or "").lower()
    if any(x in t for x in ("next.js", "nextjs", "next js")):
        return "nextjs"
    if any(x in t for x in ("nuxt", "vue 3", "vuejs", "vue.js")):
        return "vue"
    if "react" in t:
        return "react_vite"
    if "angular" in t:
        return "angular"
    if "django" in t:
        return "django"
    if any(x in t for x in ("fastapi", "api python", "backend python")):
        return "fastapi"
    if "flask" in t:
        return "flask"
    if any(x in t for x in ("express", "node.js", "nodejs", "backend node")):
        return "nodejs"
    if "php" in t or "fil rouge" in t:
        return "php"
    if any(x in t for x in ("laravel", "symfony")):
        return "php"
    if any(x in t for x in ("fullstack", "full stack", "front et back")):
        return "fullstack_static_fastapi"
    return "static"


def _parse_pages(pages_str: str) -> list[tuple[str, str]]:
    raw = re.split(r"[,;]+|\bet\b", pages_str or "accueil, contact")
    out: list[tuple[str, str]] = []
    for p in raw:
        p = p.strip()
        if not p or len(p) < 2:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", p.lower().strip()).strip("-") or "page"
        if slug in ("accueil", "home", "index"):
            slug, titre = "index", p.title() if p else "Accueil"
        else:
            titre = p.strip().title()
        if (slug, titre) not in out:
            out.append((slug, titre))
    if not out or out[0][0] != "index":
        out.insert(0, ("index", "Accueil"))
    return out[:12]


def _nav_html(pages: list[tuple[str, str]], current: str) -> str:
    links = []
    for slug, titre in pages:
        href = "index.html" if slug == "index" else f"{slug}.html"
        active = ' aria-current="page"' if slug == current else ""
        links.append(f'                <li><a href="{href}"{active}>{titre}</a></li>')
    return "\n".join(links)


def _page_html(nom_site: str, slug: str, titre: str, pages: list[tuple[str, str]], theme: str) -> str:
    if slug == "index":
        body_extra = f"""
        <section class="hero">
            <h1>{nom_site}</h1>
            <p class="hero-lead">{theme or "Bienvenue sur notre site."}</p>
            <a class="btn btn-primary" href="contact.html">Nous contacter</a>
        </section>
        <section class="features">
            <article class="card"><h2>Contenu de qualité</h2><p>Structure professionnelle, responsive et accessible.</p></article>
            <article class="card"><h2>Design moderne</h2><p>CSS variables, grille flexible, typographie soignée.</p></article>
            <article class="card"><h2>Performance</h2><p>HTML sémantique, assets optimisés.</p></article>
        </section>"""
    elif slug == "contact":
        body_extra = """
        <section class="page-content">
            <h1>Contact</h1>
            <form class="contact-form" action="#" method="post">
                <label for="nom">Nom</label>
                <input type="text" id="nom" name="nom" required autocomplete="name">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required autocomplete="email">
                <label for="message">Message</label>
                <textarea id="message" name="message" rows="5" required></textarea>
                <button type="submit" class="btn btn-primary">Envoyer</button>
            </form>
        </section>"""
    else:
        body_extra = f"""
        <section class="page-content">
            <h1>{titre}</h1>
            <p>Contenu de la page {titre}. Personnalisez selon le thème du site.</p>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{nom_site} — {titre}">
    <title>{titre} | {nom_site}</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
    <a class="skip-link" href="#main">Aller au contenu</a>
    <header class="site-header">
        <div class="container header-inner">
            <a class="logo" href="index.html">{nom_site}</a>
            <button type="button" class="nav-toggle" aria-label="Menu" aria-expanded="false" aria-controls="main-nav">
                <span></span><span></span><span></span>
            </button>
            <nav id="main-nav" class="main-nav" aria-label="Navigation principale">
                <ul>
{_nav_html(pages, slug)}
                </ul>
            </nav>
        </div>
    </header>
    <main id="main" class="container">
{body_extra}
    </main>
    <footer class="site-footer">
        <div class="container"><p>&copy; {nom_site} — Développé avec JARVIS</p></div>
    </footer>
    <script src="assets/js/app.js"></script>
</body>
</html>
"""


def _css_senior(couleurs: str) -> str:
    accent = "#50736d"
    cl = couleurs.lower()
    if "bordeaux" in cl or "or" in cl:
        accent = "#8a7254"
    elif "bleu" in cl:
        accent = "#2563eb"
    return f"""/* Design system — senior fullstack scaffold */
:root {{
    --color-bg: #faf9f6;
    --color-text: #2b2b2b;
    --color-accent: {accent};
    --color-accent-dark: #3d5652;
    --color-muted: #6b7280;
    --color-card: #ffffff;
    --font-sans: 'Segoe UI', system-ui, sans-serif;
    --space-sm: 1rem;
    --space-md: 1.5rem;
    --space-lg: 2.5rem;
    --space-xl: 4rem;
    --radius: 8px;
    --shadow: 0 4px 20px rgba(0,0,0,0.08);
    --max-width: 1100px;
}}
*, *::before, *::after {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{ margin: 0; font-family: var(--font-sans); line-height: 1.6; color: var(--color-text); background: var(--color-bg); }}
.container {{ max-width: var(--max-width); margin: 0 auto; padding: 0 var(--space-md); }}
.skip-link {{ position: absolute; top: -100px; left: 1rem; background: var(--color-accent); color: #fff; padding: 0.5rem 1rem; z-index: 1000; }}
.skip-link:focus {{ top: 1rem; }}
.site-header {{ background: var(--color-card); box-shadow: var(--shadow); position: sticky; top: 0; z-index: 100; }}
.header-inner {{ display: flex; align-items: center; justify-content: space-between; min-height: 4rem; }}
.logo {{ font-weight: 700; font-size: 1.25rem; color: var(--color-accent); text-decoration: none; }}
.main-nav ul {{ display: flex; gap: var(--space-md); list-style: none; margin: 0; padding: 0; }}
.main-nav a {{ color: var(--color-text); text-decoration: none; font-weight: 500; padding: 0.5rem 0; border-bottom: 2px solid transparent; }}
.main-nav a:hover, .main-nav a[aria-current="page"] {{ color: var(--color-accent); border-bottom-color: var(--color-accent); }}
.nav-toggle {{ display: none; flex-direction: column; gap: 5px; background: none; border: none; cursor: pointer; }}
.nav-toggle span {{ display: block; width: 24px; height: 2px; background: var(--color-text); }}
.hero {{ text-align: center; padding: var(--space-xl) 0; }}
.hero h1 {{ font-size: clamp(2rem, 5vw, 3rem); color: var(--color-accent-dark); }}
.hero-lead {{ font-size: 1.25rem; color: var(--color-muted); max-width: 40rem; margin: 0 auto var(--space-lg); }}
.features {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--space-md); padding-bottom: var(--space-xl); }}
.card {{ background: var(--color-card); padding: var(--space-md); border-radius: var(--radius); box-shadow: var(--shadow); }}
.card h2 {{ margin-top: 0; color: var(--color-accent); }}
.page-content {{ padding: var(--space-lg) 0; }}
.contact-form {{ display: grid; gap: var(--space-sm); max-width: 32rem; }}
.contact-form input, .contact-form textarea {{ width: 100%; padding: 0.5rem 1rem; border: 1px solid #ddd; border-radius: var(--radius); font: inherit; }}
.btn {{ display: inline-block; padding: 1rem 1.5rem; border-radius: var(--radius); text-decoration: none; font-weight: 600; border: none; cursor: pointer; }}
.btn-primary {{ background: var(--color-accent); color: #fff; }}
.site-footer {{ background: var(--color-accent-dark); color: #fff; text-align: center; padding: var(--space-md); margin-top: var(--space-xl); }}
@media (max-width: 768px) {{
    .nav-toggle {{ display: flex; }}
    .main-nav {{ position: absolute; top: 100%; left: 0; right: 0; background: var(--color-card); box-shadow: var(--shadow); display: none; padding: var(--space-md); }}
    .main-nav.is-open {{ display: block; }}
    .main-nav ul {{ flex-direction: column; }}
}}
"""


def _js_senior() -> str:
    return """(function () {
    const toggle = document.querySelector('.nav-toggle');
    const nav = document.querySelector('.main-nav');
    if (!toggle || !nav) return;
    toggle.addEventListener('click', function () {
        const open = nav.classList.toggle('is-open');
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
})();
"""


def _fastapi_main() -> str:
    return '''"""API FastAPI — scaffold senior JARVIS."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"healthy": True}
'''


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def scaffold_projet(chemin_abs: str, stack: str, briefing: dict[str, Any]) -> list[str]:
    nom = briefing.get("nom_site") or briefing.get("theme") or "Mon Site"
    theme = briefing.get("theme", "")
    couleurs = briefing.get("couleurs", "")
    pages = _parse_pages(briefing.get("pages", "accueil, contact"))
    created: list[str] = []

    def rel(p: str) -> str:
        return os.path.relpath(p, chemin_abs).replace("\\", "/")

    os.makedirs(chemin_abs, exist_ok=True)

    if stack in ("static", "fullstack_static_fastapi"):
        for sub in ("assets/css", "assets/js", "assets/images"):
            os.makedirs(os.path.join(chemin_abs, sub), exist_ok=True)
        for slug, titre in pages:
            fname = "index.html" if slug == "index" else f"{slug}.html"
            path = os.path.join(chemin_abs, fname)
            _write(path, _page_html(nom, slug, titre, pages, theme))
            created.append(rel(path))
        css_path = os.path.join(chemin_abs, "assets", "css", "style.css")
        _write(css_path, _css_senior(couleurs))
        created.append(rel(css_path))
        js_path = os.path.join(chemin_abs, "assets", "js", "app.js")
        _write(js_path, _js_senior())
        created.append(rel(js_path))
        readme = os.path.join(chemin_abs, "README.md")
        _write(readme, f"# {nom}\n\nSite HTML/CSS/JS — scaffold senior JARVIS.\n")
        created.append(rel(readme))

    elif stack == "php":
        for sub in ("assets/css", "assets/js", "includes"):
            os.makedirs(os.path.join(chemin_abs, sub), exist_ok=True)
        _write(os.path.join(chemin_abs, "index.php"), f"<?php $page_title='{nom}'; require 'includes/header.php'; ?><main class='container'><h1>{nom}</h1></main><?php require 'includes/footer.php'; ?>")
        created.append("index.php")
        _write(os.path.join(chemin_abs, "includes", "header.php"), '<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="assets/css/style.css"><title><?= htmlspecialchars($page_title??"") ?></title></head><body><header class="site-header"><div class="container"><a href="index.php">Accueil</a></div></header>')
        _write(os.path.join(chemin_abs, "includes", "footer.php"), '<footer class="site-footer"><div class="container"><p>&copy; Site</p></div></footer></body></html>')
        _write(os.path.join(chemin_abs, "assets", "css", "style.css"), _css_senior(couleurs))
        created.extend(["includes/header.php", "includes/footer.php", "assets/css/style.css"])

    elif stack == "react_vite":
        os.makedirs(os.path.join(chemin_abs, "src"), exist_ok=True)
        slug = re.sub(r"[^a-z0-9-]", "-", nom.lower())[:32] or "app"
        _write(os.path.join(chemin_abs, "package.json"), json.dumps({"name": slug, "private": True, "type": "module", "scripts": {"dev": "vite", "build": "vite build"}, "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"}, "devDependencies": {"@vitejs/plugin-react": "^4.3.1", "vite": "^5.4.0"}}, indent=2))
        created.append("package.json")
        _write(os.path.join(chemin_abs, "index.html"), f'<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{nom}</title></head><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>')
        _write(os.path.join(chemin_abs, "src", "main.jsx"), "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App.jsx';\nimport './index.css';\nReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);\n")
        _write(os.path.join(chemin_abs, "src", "App.jsx"), f"export default function App(){{return(<main style={{padding:'2rem'}}><h1>{nom}</h1><p>{theme or 'React app'}</p></main>);}}\n")
        _write(os.path.join(chemin_abs, "src", "index.css"), _css_senior(couleurs))
        _write(os.path.join(chemin_abs, "vite.config.js"), "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\nexport default defineConfig({ plugins: [react()] });\n")
        created.extend(["index.html", "src/main.jsx", "src/App.jsx", "src/index.css", "vite.config.js"])

    elif stack == "fastapi":
        os.makedirs(os.path.join(chemin_abs, "app"), exist_ok=True)
        _write(os.path.join(chemin_abs, "app", "main.py"), _fastapi_main())
        _write(os.path.join(chemin_abs, "requirements.txt"), "fastapi>=0.110.0\nuvicorn[standard]>=0.27.0\n")
        created.extend(["app/main.py", "requirements.txt"])

    elif stack == "nodejs":
        _write(os.path.join(chemin_abs, "package.json"), json.dumps({"name": "api", "type": "module", "scripts": {"start": "node server.js"}, "dependencies": {"express": "^4.21.0", "cors": "^2.8.5"}}, indent=2))
        _write(os.path.join(chemin_abs, "server.js"), "import express from 'express';\nconst app=express();\napp.get('/',(req,res)=>res.json({status:'ok'}));\napp.listen(3000,()=>console.log('http://localhost:3000'));\n")
        created.extend(["package.json", "server.js"])

    if stack == "fullstack_static_fastapi":
        api = os.path.join(chemin_abs, "backend")
        os.makedirs(api, exist_ok=True)
        _write(os.path.join(api, "main.py"), _fastapi_main())
        _write(os.path.join(api, "requirements.txt"), "fastapi>=0.110.0\nuvicorn[standard]>=0.27.0\n")
        created.extend(["backend/main.py", "backend/requirements.txt"])

    return created


def valider_html(contenu: str) -> list[str]:
    errs: list[str] = []
    if len(contenu.strip()) < _MIN_HTML_CHARS:
        errs.append(f"HTML trop court ({len(contenu)} car., min {_MIN_HTML_CHARS})")
    if "<!doctype html>" not in contenu.lower():
        errs.append("DOCTYPE html manquant")
    if "viewport" not in contenu:
        errs.append("Meta viewport manquante")
    if "<body" in contenu and "</body>" not in contenu:
        errs.append("Balise </body> manquante")
    return errs


def valider_css(contenu: str) -> list[str]:
    errs: list[str] = []
    if len(contenu.strip()) < _MIN_CSS_CHARS:
        errs.append(f"CSS trop minimal ({len(contenu)} car., min {_MIN_CSS_CHARS})")
    if contenu.count("{") != contenu.count("}"):
        errs.append("Accolades CSS déséquilibrées")
    return errs


def valider_js(contenu: str) -> list[str]:
    if not contenu.strip():
        return []
    errs: list[str] = []
    if len(contenu.strip()) < _MIN_JS_CHARS:
        errs.append(f"JS quasi vide ({len(contenu)} car.)")
    return errs


def valider_python(contenu: str) -> list[str]:
    errs: list[str] = []
    if len(contenu.strip()) < _MIN_PY_CHARS:
        errs.append(f"Python trop court ({len(contenu)} car.)")
    try:
        compile(contenu, "<string>", "exec")
    except SyntaxError as e:
        errs.append(f"Syntaxe Python L{e.lineno}: {e.msg}")
    return errs


def valider_apres_ecriture(chemin_fichier: str, contenu: str) -> list[str]:
    ext = os.path.splitext(chemin_fichier)[1].lower()
    if ext in (".html", ".htm"):
        return valider_html(contenu)
    if ext == ".php":
        return valider_html(re.sub(r"<\?php.*?\?>", "", contenu, flags=re.DOTALL))
    if ext == ".css":
        return valider_css(contenu)
    if ext in (".js", ".jsx", ".ts", ".tsx"):
        return valider_js(contenu)
    if ext == ".py":
        return valider_python(contenu)
    if ext == ".json":
        try:
            json.loads(contenu)
        except json.JSONDecodeError as e:
            return [f"JSON invalide: {e.msg}"]
    return []


def auditer_projet(chemin_abs: str, stack: str | None = None) -> dict[str, Any]:
    stack = stack or "static"
    errors: list[str] = []
    warnings: list[str] = []
    files_checked = 0
    if not os.path.isdir(chemin_abs):
        return {"ok": False, "errors": ["Dossier introuvable"], "warnings": [], "files": 0, "stack": stack}

    if stack in ("static", "fullstack_static_fastapi"):
        for req in ("index.html", "assets/css/style.css"):
            if not os.path.isfile(os.path.join(chemin_abs, req)):
                errors.append(f"Fichier requis manquant : {req}")

    skip = {"node_modules", ".git", "__pycache__", "venv", "dist"}
    for root, dirs, files in os.walk(chemin_abs):
        dirs[:] = [d for d in dirs if d not in skip]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in (".html", ".css", ".js", ".jsx", ".py", ".json", ".php"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            files_checked += 1
            rel = os.path.relpath(fpath, chemin_abs)
            for err in valider_apres_ecriture(fpath, content):
                msg = f"{rel}: {err}"
                if "trop" in err.lower() or "manquant" in err.lower() or "Syntaxe" in err:
                    errors.append(msg)
                else:
                    warnings.append(msg)

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings, "files": files_checked, "stack": stack}


def formater_rapport_audit(audit: dict[str, Any]) -> str:
    lines = [f"Audit — {audit.get('files', 0)} fichiers — stack {audit.get('stack')}"]
    lines.append("OK" if audit.get("ok") else "ERREURS À CORRIGER IMMÉDIATEMENT")
    for e in audit.get("errors", [])[:20]:
        lines.append(f"[ERREUR] {e}")
    for w in audit.get("warnings", [])[:10]:
        lines.append(f"[AVERT] {w}")
    return "\n".join(lines)


PROMPT_SENIOR_FULLSTACK = """
IDENTITÉ : Développeur FULLSTACK SENIOR (15+ ans). Toutes technologies.

FRONTEND : HTML5, CSS3, JS/TS, React, Next.js, Vue/Nuxt, Angular, Tailwind, Vite, Webpack.
BACKEND : Node/Express/Nest, Python FastAPI/Django/Flask, PHP Laravel/Symfony, Java Spring, .NET, Go.
DATA : PostgreSQL, MySQL, MongoDB, Redis, Prisma, SQLAlchemy.
DEVOPS : Git, Docker, npm/pip, tests Jest/pytest, CI/CD.

MÉTHODE SANS ERREUR :
1. webdev_analyser_structure + webdev_lire_fichier avant modification.
2. Code COMPLET — jamais placeholder ou fichier d'une ligne.
3. Corriger tout [VALIDATION] après webdev_ecrire_fichier.
4. Terminer par webdev_valider_projet jusqu'à OK.
5. Échec → webdev_recherche_web → webdev_auto_apprendre → réessayer.
6. Windows : webdev_creer_dossier / webdev_ecrire_fichier (pas bash).
"""
