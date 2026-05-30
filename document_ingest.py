# -*- coding: utf-8 -*-
"""
Ingestion et analyse de documents pour JARVIS (briefing site, dev, général).
"""
from __future__ import annotations

import base64
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any

MAX_FILE_BYTES = 12 * 1024 * 1024
MAX_TEXT_STORE = 200_000
MAX_TEXT_PROMPT = 14_000

TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx",
    ".json", ".xml", ".csv", ".py", ".php", ".sql", ".yaml", ".yml", ".ini", ".env",
    ".log", ".rtf",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
DOC_EXTENSIONS = {".pdf", ".docx", ".doc", ".odt", ".xlsx", ".xls", ".pptx"}

_jarvis_root = ""
_uploads_dir = ""
_index_file = ""
_session_docs: list[dict[str, Any]] = []


def init(jarvis_root: str) -> None:
    global _jarvis_root, _uploads_dir, _index_file
    _jarvis_root = jarvis_root
    _uploads_dir = os.path.join(jarvis_root, "jarvis_uploads")
    _index_file = os.path.join(_uploads_dir, "_index.json")
    os.makedirs(_uploads_dir, exist_ok=True)
    _charger_index()


def _charger_index() -> None:
    global _session_docs
    if not os.path.isfile(_index_file):
        _session_docs = []
        return
    try:
        with open(_index_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        _session_docs = data if isinstance(data, list) else []
    except Exception:
        _session_docs = []


def _sauvegarder_index() -> None:
    try:
        with open(_index_file, "w", encoding="utf-8") as f:
            json.dump(_session_docs[-50:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def lister_documents(context: str | None = None) -> list[dict[str, Any]]:
    if context:
        return [d for d in _session_docs if d.get("context") == context]
    return list(_session_docs)


def _ext(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def extraire_texte_fichier(path: str, filename: str) -> tuple[str, str]:
    """Retourne (texte, methode)."""
    ext = _ext(filename)

    if ext in TEXT_EXTENSIONS:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()[:MAX_TEXT_STORE], "texte_brut"
        except Exception as e:
            return f"(Lecture impossible : {e})", "erreur"

    if ext == ".pdf":
        text = ""
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            parts = []
            for page in reader.pages[:80]:
                parts.append(page.extract_text() or "")
            text = "\n".join(parts).strip()
            if len(text) > 80:
                return text[:MAX_TEXT_STORE], "pdf_pypdf"
        except ImportError:
            pass
        except Exception as e:
            print(f"[DOC] pypdf : {e}")
        # OCR / vision : PDF scanné ou texte insuffisant
        gemini_text = _extraire_pdf_gemini(path)
        if gemini_text and len(gemini_text) > 50:
            return gemini_text[:MAX_TEXT_STORE], "pdf_gemini_ocr"
        if text:
            return text[:MAX_TEXT_STORE], "pdf_pypdf_partiel"
        return gemini_text or "(PDF illisible — ajoutez GEMINI_API_KEY pour OCR)", "pdf_erreur"

    if ext == ".docx":
        try:
            from docx import Document
            doc = Document(path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            if text:
                return text[:MAX_TEXT_STORE], "docx"
        except ImportError:
            return "(Installez python-docx pour lire les .docx : pip install python-docx)", "erreur"
        except Exception as e:
            return f"(DOCX : {e})", "erreur"

    if ext in IMAGE_EXTENSIONS:
        return _extraire_image_vision_sync(
            path,
            "OCR et analyse UI pour développement web. Extrais : "
            "1) TOUT texte visible (OCR) 2) Couleurs hex ou noms 3) Structure layout "
            "4) Composants UI 5) Contenu à coder en HTML/CSS. Sois exhaustif.",
        ), "image_ocr_vision"

    if ext in (".xlsx", ".xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            rows = []
            for sheet in wb.worksheets[:3]:
                rows.append(f"=== {sheet.title} ===")
                for i, row in enumerate(sheet.iter_rows(max_row=200, values_only=True)):
                    if i > 200:
                        break
                    line = "\t".join(str(c) if c is not None else "" for c in row)
                    if line.strip():
                        rows.append(line)
            wb.close()
            return "\n".join(rows)[:MAX_TEXT_STORE], "xlsx"
        except ImportError:
            return "(Installez openpyxl pour Excel : pip install openpyxl)", "erreur"
        except Exception as e:
            return f"(Excel : {e})", "erreur"

    # Dernier recours : binaire illisible
    try:
        with open(path, "rb") as f:
            sample = f.read(8000)
        if sample.count(b"\x00") > 50:
            return "(Fichier binaire — type non supporté pour extraction texte)", "binaire"
        return sample.decode("utf-8", errors="replace")[:MAX_TEXT_STORE], "fallback_utf8"
    except Exception as e:
        return f"(Impossible de lire : {e})", "erreur"


def _extraire_pdf_gemini(path: str) -> str:
    """OCR / extraction PDF via Gemini (texte scanné, images dans PDF)."""
    try:
        import builtins
        client = getattr(builtins, "client", None)
        if not client:
            return ""
        with open(path, "rb") as f:
            data = f.read()
        if len(data) > 15 * 1024 * 1024:
            data = data[: 15 * 1024 * 1024]
        model = getattr(builtins, "CHOSEN_MODEL", "gemini-2.5-flash")
        if model and "gpt" in str(model).lower():
            model = "gemini-2.5-flash"
        prompt = (
            "Extrais INTÉGRALEMENT le contenu textuel de ce PDF pour un développeur web. "
            "Inclus titres, listes, tableaux, spécifications, couleurs, pages du site. "
            "Structure par sections. Français."
        )
        try:
            from google.genai import types
            part = types.Part.from_bytes(data=data, mime_type="application/pdf")
            resp = client.models.generate_content(model=model, contents=[part, prompt])
        except Exception:
            resp = client.models.generate_content(
                model=model,
                contents=[prompt, f"(PDF binaire {len(data)} octets — extraction demandée)"],
            )
        return (resp.text or "").strip()
    except Exception as e:
        print(f"[DOC] PDF Gemini : {e}")
        return ""


def _extraire_image_vision_sync(path: str, prompt: str) -> str:
    try:
        import builtins
        client = getattr(builtins, "client", None)
        if not client:
            return "(Vision indisponible — configurez GEMINI_API_KEY dans .env)"
        from PIL import Image
        model = getattr(builtins, "CHOSEN_MODEL", "gemini-2.5-flash")
        if model and "gpt" in str(model).lower():
            model = "gemini-2.5-flash"
        img = Image.open(path)
        resp = client.models.generate_content(model=model, contents=[prompt, img])
        return (resp.text or "").strip()[:MAX_TEXT_STORE]
    except Exception as e:
        return f"(Analyse visuelle échouée : {e})"


def _detecter_type_cahier_charges(texte: str) -> bool:
    t = texte.lower()
    mots = ("cahier des charges", "spécifications", "specifications", "site web", "pages", "objectif", "charte graphique")
    return sum(1 for m in mots if m in t) >= 2


def _extraire_champs_briefing(texte: str) -> dict[str, str]:
    """Heuristiques pour pré-remplir le briefing depuis un cahier des charges."""
    champs: dict[str, str] = {}
    t = texte
    tl = t.lower()

    for pat, key in [
        (r"(?:nom du site|nom de l['']application|titre du projet)\s*[:\-]\s*(.+)", "nom_site"),
        (r"(?:th[èe]me|sujet)\s*[:\-]\s*(.+)", "theme"),
        (r"(?:objectif|but)\s*[:\-]\s*(.+)", "objectif"),
        (r"(?:pages?|rubriques?)\s*[:\-]\s*(.+)", "pages"),
        (r"(?:technolog|stack|framework)\s*[:\-]\s*(.+)", "stack"),
        (r"(?:couleurs?|charte graphique|identit[ée] visuelle)\s*[:\-]\s*(.+)", "couleurs"),
        (r"(?:fonctionnalit[ée]s?)\s*[:\-]\s*(.+)", "fonctionnalites"),
    ]:
        m = re.search(pat, t, re.I | re.M)
        if m:
            val = m.group(1).strip().split("\n")[0][:300]
            if val and key not in champs:
                champs[key] = val

    if "orchid" in tl and "theme" not in champs:
        champs.setdefault("theme", "orchidées")
    return champs


def enregistrer_document(
    filename: str,
    raw_bytes: bytes,
    context: str = "general",
    note: str = "",
) -> dict[str, Any]:
    if len(raw_bytes) > MAX_FILE_BYTES:
        return {"ok": False, "error": f"Fichier trop volumineux (max {MAX_FILE_BYTES // (1024*1024)} Mo)"}

    safe_name = re.sub(r"[^\w.\- ]", "_", filename)[:120] or "document"
    doc_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    stored_name = f"{doc_id}_{safe_name}"
    path = os.path.join(_uploads_dir, stored_name)

    with open(path, "wb") as f:
        f.write(raw_bytes)

    texte, methode = extraire_texte_fichier(path, safe_name)
    is_cdc = _detecter_type_cahier_charges(texte)
    champs_briefing = _extraire_champs_briefing(texte) if is_cdc else {}

    resume = texte[:800] + ("…" if len(texte) > 800 else "")
    if len(texte) > 3000:
        resume = (
            f"[Document long — {len(texte)} caractères — méthode {methode}]\n"
            + texte[:2500]
            + "\n…(suite disponible pour le développement)"
        )

    entry = {
        "id": doc_id,
        "filename": safe_name,
        "stored_path": path,
        "context": context,
        "note": note[:200],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "methode": methode,
        "chars": len(texte),
        "is_cahier_charges": is_cdc,
        "champs_briefing": champs_briefing,
        "resume": resume,
        "texte": texte[:MAX_TEXT_STORE],
    }
    _session_docs.append(entry)
    _sauvegarder_index()
    return {"ok": True, "document": entry}


def get_uploads_dir() -> str:
    return _uploads_dir


def lister_chemins_indexes() -> set[str]:
    return {d.get("stored_path") for d in _session_docs if d.get("stored_path")}


def synchroniser_fichiers_disque(context: str = "briefing") -> list[dict[str, Any]]:
    """Importe les fichiers déposés manuellement dans jarvis_uploads/."""
    if not os.path.isdir(_uploads_dir):
        return []
    deja = lister_chemins_indexes()
    importes = []
    for name in os.listdir(_uploads_dir):
        if name.startswith("_") or name.endswith(".json"):
            continue
        path = os.path.join(_uploads_dir, name)
        if not os.path.isfile(path) or path in deja:
            continue
        try:
            with open(path, "rb") as f:
                raw = f.read()
            display = re.sub(r"^\d{8}_\d{6}_[a-f0-9]{8}_", "", name)
            r = enregistrer_document(display, raw, context, note="import_dossier")
            if r.get("ok"):
                importes.append(r["document"])
        except Exception as e:
            print(f"[DOC] Import {name} : {e}")
    return importes


def contexte_pour_prompt(context: str | None = None, max_chars: int = MAX_TEXT_PROMPT) -> str:
    # Toujours inclure TOUS les docs du dossier (pas seulement le contexte filtré)
    docs = list(_session_docs)
    if context:
        ctx_docs = [d for d in docs if d.get("context") == context]
        if ctx_docs:
            docs = ctx_docs + [d for d in docs if d not in ctx_docs]
    if not docs:
        return ""
    parts = ["\n=== DOCUMENTS jarvis_uploads/ (source de vérité) ===\n"]
    total = 0
    for d in docs[-8:]:
        bloc = (
            f"\n--- Document : {d['filename']} ({d['date']}) — {d['methode']} — {d['chars']} car. ---\n"
            f"{d.get('note') and 'Note: ' + d['note'] + chr(10) or ''}"
            f"{d['texte'][:4000]}\n"
        )
        if total + len(bloc) > max_chars:
            bloc = bloc[: max_chars - total]
        parts.append(bloc)
        total += len(bloc)
        if total >= max_chars:
            break
    parts.append(
        "\nUtilise ces documents comme source de vérité pour le briefing et le développement du site.\n"
    )
    return "".join(parts)


def decoder_upload_b64(data_b64: str) -> bytes:
    if "," in data_b64[:80]:
        data_b64 = data_b64.split(",", 1)[1]
    return base64.b64decode(data_b64)
