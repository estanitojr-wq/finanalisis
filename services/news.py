"""
Noticias automáticas vía RSS (sin intervención manual).

Fuentes:
  - Yahoo Finance: titulares por ticker.
  - Google News: búsqueda por nombre de empresa (en español) y feed macro.
Los resultados se cachean unos minutos para no saturar los feeds.
"""
import time
from calendar import timegm
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser

_CACHE: dict[str, tuple[float, list]] = {}
USER_AGENT = "Mozilla/5.0 (FinAnalisis RSS reader)"

MACRO_QUERY = '("Reserva Federal" OR BCE OR inflación OR "tipos de interés" OR PIB) economía'


def _yahoo_url(ticker: str) -> str:
    return f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote_plus(ticker)}&region=US&lang=en-US"


def _gnews_url(query: str, lang="es", country="ES") -> str:
    return (f"https://news.google.com/rss/search?q={quote_plus(query)}+when:7d"
            f"&hl={lang}&gl={country}&ceid={country}:{lang}")


def _parse(url: str, source_name: str, limit: int) -> list[dict]:
    feed = feedparser.parse(url, agent=USER_AGENT)
    items = []
    for e in feed.entries[:limit]:
        published = None
        if getattr(e, "published_parsed", None):
            published = datetime.fromtimestamp(timegm(e.published_parsed), tz=timezone.utc)
        items.append({
            "title": e.get("title", "").strip(),
            "link": e.get("link", ""),
            "published": published,
            "source": (e.get("source") or {}).get("title") or source_name,
        })
    return items


def _cached(key: str, ttl: int, loader):
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    try:
        data = loader()
    except Exception:
        data = hit[1] if hit else []   # si falla la red, sirve lo último bueno
    _CACHE[key] = (time.time(), data)
    return data


def _dedupe_sort(items: list[dict], limit: int) -> list[dict]:
    seen, out = set(), []
    for it in items:
        k = it["title"].lower()[:80]
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    out.sort(key=lambda x: x["published"] or epoch, reverse=True)
    return out[:limit]


def company_news(ticker: str, company_name: str = "", limit: int = 12, ttl: int = 600) -> list[dict]:
    def load():
        items = _parse(_yahoo_url(ticker), "Yahoo Finance", 15)
        if company_name:
            items += _parse(_gnews_url(f'"{company_name}"'), "Google News", 15)
        return _dedupe_sort(items, limit)
    return _cached(f"co:{ticker}", ttl, load)


def macro_news(limit: int = 8, ttl: int = 600) -> list[dict]:
    return _cached("macro", ttl, lambda: _dedupe_sort(_parse(_gnews_url(MACRO_QUERY), "Google News", 20), limit))
