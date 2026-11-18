"""
Contenido editable de la plataforma (textos, vídeos y ETFs) guardado en content.json.

Persistencia:
  1. Se escribe en el disco del servidor -> los cambios se ven al instante.
  2. Si hay GITHUB_TOKEN en los secrets, se hace commit de content.json en el
     repositorio -> los cambios sobreviven a reinicios y redespliegues.
     (El disco de Streamlit Cloud se borra al reiniciar: sin el commit se perderían.)
"""
import base64
import copy
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONTENT_FILE = ROOT / "content.json"
VIDEO_DIRS = (ROOT / "videos", ROOT)

REQUIRED_KEYS = {"textos", "etfs", "videos", "benchmark"}


def load() -> dict:
    with open(CONTENT_FILE, encoding="utf-8") as f:
        return json.load(f)


def validate(data: dict) -> list[str]:
    """Comprobaciones mínimas para no publicar un contenido roto."""
    errors = []
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        errors.append(f"Faltan secciones: {', '.join(sorted(missing))}")
    for e in data.get("etfs", []):
        if not str(e.get("ticker", "")).strip():
            errors.append(f"El ETF «{e.get('sector', '?')}» no tiene ticker.")
        if not str(e.get("sector", "")).strip():
            errors.append("Hay un ETF sin nombre de sector.")
    ids = [v.get("id") for v in data.get("videos", [])]
    if len(ids) != len(set(ids)):
        errors.append("Hay vídeos con el mismo identificador.")
    for v in data.get("videos", []):
        if not str(v.get("titulo", "")).strip():
            errors.append(f"El vídeo {v.get('id')} no tiene título.")
    return errors


def to_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def save_local(data: dict) -> None:
    tmp = CONTENT_FILE.with_suffix(".tmp")
    tmp.write_text(to_json(data), encoding="utf-8")
    tmp.replace(CONTENT_FILE)   # escritura atómica


def commit_to_github(data: dict, token: str, repo: str, branch: str = "main",
                     message: str = "Actualiza contenido desde el panel de administración") -> tuple[bool, str]:
    """Sube content.json al repositorio con la API de GitHub."""
    url = f"https://api.github.com/repos/{repo}/contents/content.json"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    try:
        r = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
        sha = r.json().get("sha") if r.status_code == 200 else None
        body = {"message": message, "branch": branch,
                "content": base64.b64encode(to_json(data).encode("utf-8")).decode("ascii")}
        if sha:
            body["sha"] = sha
        r = requests.put(url, headers=headers, json=body, timeout=20)
        if r.status_code in (200, 201):
            return True, "Publicado en GitHub."
        return False, f"GitHub respondió {r.status_code}: {r.json().get('message', '')}"
    except requests.RequestException as e:
        return False, f"No se pudo conectar con GitHub: {e}"


def find_video_file(name: str) -> Path | None:
    if not name:
        return None
    name = Path(name).name   # evita rutas fuera de la carpeta
    for d in VIDEO_DIRS:
        p = d / name
        if p.is_file():
            return p
    return None


def youtube_id(url: str) -> str | None:
    """Extrae el ID de cualquier enlace de YouTube (watch, youtu.be, shorts, embed)."""
    import re
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None


def playable_source(video: dict) -> str | None:
    """Lo que se le pasa a st.video: URL de YouTube normalizada, otra URL o fichero local."""
    url = (video.get("url") or "").strip()
    if url:
        yid = youtube_id(url)
        return f"https://www.youtube.com/watch?v={yid}" if yid else url
    p = find_video_file(video.get("archivo", ""))
    return str(p) if p else None


def clone(data: dict) -> dict:
    return copy.deepcopy(data)
