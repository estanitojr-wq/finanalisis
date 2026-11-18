"""Estilos, formato y cargadores de datos compartidos por todas las páginas."""
import html

import pandas as pd
import streamlit as st

from services import content as content_svc
from services import etf_data

# ------------------------------------------------------------------ estilos
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
:root{--bg:#0b0f14;--panel:#111821;--panel2:#16202b;--line:#1f2b38;--ink:#e6edf3;--muted:#8b98a5;
--accent:#4f8cff;--pos:#2fbf71;--neg:#ef5350;--warn:#e0a83a}
html,body,[class*="css"],.stMarkdown,.stText{font-family:'Inter',system-ui,sans-serif}
.block-container{padding-top:2.2rem;max-width:1240px}
h1,h2,h3{letter-spacing:-.01em}
.mono,.num{font-family:'JetBrains Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums}
.pos{color:var(--pos)}.neg{color:var(--neg)}.muted{color:var(--muted)}
.small{font-size:13px;color:var(--muted)}
/* hero */
.hero{border:1px solid var(--line);border-radius:16px;padding:34px 34px 28px;
 background:radial-gradient(900px 300px at 85% -20%,rgba(79,140,255,.18),transparent 60%),var(--panel)}
.hero h1{font-size:clamp(30px,4vw,46px);line-height:1.05;margin:0 0 12px;font-weight:800}
.hero p{font-size:17px;color:#b8c4d0;max-width:700px;margin:0}
.kicker{font-size:13px;color:var(--accent);font-weight:600;margin-bottom:10px}
/* tiles de sectores */
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px}
.tile{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:var(--panel)}
.tile .s{font-size:13px;color:var(--muted)}.tile .t{font-size:12px;color:var(--muted)}
.tile .v{font-size:22px;font-weight:600;margin-top:4px}
.tile.up{background:linear-gradient(180deg,rgba(47,191,113,.10),transparent),var(--panel)}
.tile.down{background:linear-gradient(180deg,rgba(239,83,80,.10),transparent),var(--panel)}
/* tabla terminal */
table.term{width:100%;border-collapse:collapse;font-size:14px}
table.term th{font-weight:500;color:var(--muted);text-align:right;padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
table.term th:first-child,table.term td:first-child{text-align:left}
table.term td{padding:10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
table.term tr:hover td{background:var(--panel2)}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}
.bar{height:6px;border-radius:3px;background:var(--line);overflow:hidden;min-width:70px}
.bar>i{display:block;height:100%;background:var(--accent)}
/* tarjetas de vídeo */
.vcard{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--panel);margin-bottom:6px}
.thumb{aspect-ratio:16/9;position:relative;display:flex;align-items:flex-end;padding:14px;
 background-size:cover;background-position:center}
.thumb .day{font-family:'JetBrains Mono',monospace;font-size:44px;font-weight:600;line-height:1;color:#fff;opacity:.95}
.thumb .lbl{position:absolute;top:12px;left:14px;font-size:12px;font-weight:600;color:#fff;
 background:rgba(0,0,0,.35);padding:3px 9px;border-radius:999px}
.thumb .soon{position:absolute;top:12px;right:14px;font-size:12px;color:#fff;background:rgba(0,0,0,.45);padding:3px 9px;border-radius:999px}
.vbody{padding:12px 14px 14px}.vbody b{display:block;font-size:15px;margin-bottom:4px}
.vbody span{font-size:13px;color:var(--muted)}
.badge{display:inline-block;font-size:12px;padding:3px 10px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.badge.admin{border-color:var(--warn);color:var(--warn)}
</style>
"""

MODULE_COLORS = {
    "Semana 1": ("#1d4ed8", "#3b82f6"), "Semana 2": ("#047857", "#10b981"),
    "Semana 3": ("#b45309", "#f59e0b"), "Semana 4": ("#7e22ce", "#a855f7"),
    "Cierre": ("#be123c", "#f43f5e"), "Extras": ("#334155", "#64748b"),
}


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------ formato
def es(x, dec=2) -> str:
    return f"{x:,.{dec}f}".translate(str.maketrans(",.", ".,"))


def pct(x, dec=1, sign=True, color=True) -> str:
    if x is None:
        return '<span class="muted">—</span>'
    txt = f"{'+' if sign and x > 0 else ''}{es(x * 100, dec)} %"
    if not color:
        return txt
    cls = "pos" if x > 0 else "neg" if x < 0 else "muted"
    return f'<span class="{cls}">{txt}</span>'


def esc(s) -> str:
    return html.escape(str(s or ""))


def module_colors(modulo: str):
    for k, v in MODULE_COLORS.items():
        if modulo.startswith(k):
            return v
    return MODULE_COLORS["Extras"]


# ------------------------------------------------------------------ datos
def get_content() -> dict:
    """Contenido actual (se relee si un administrador acaba de guardar)."""
    return content_svc.load()


@st.cache_data(ttl=3600, show_spinner=False)
def market(tickers: tuple[str, ...]):
    closes = etf_data.download_closes(list(tickers))
    empty = pd.Series(dtype=float)
    stats = {t: etf_data.metrics(closes[t] if t in closes.columns else empty) for t in tickers}
    return closes, stats


def market_safe(content: dict):
    """(closes, stats, error). Nunca rompe la página si Yahoo falla."""
    tickers = tuple([e["ticker"] for e in content["etfs"]] + [content["benchmark"]["ticker"]])
    try:
        closes, stats = market(tickers)
        return closes, stats, None
    except Exception as e:
        return None, {}, str(e)


def market_notice(err):
    if err:
        st.warning("Las cotizaciones en vivo no están disponibles ahora mismo (Yahoo Finance limita "
                   "las consultas desde el servidor). Se muestran los datos fijos de cada ETF; "
                   "vuelve a intentarlo en unos minutos.")
