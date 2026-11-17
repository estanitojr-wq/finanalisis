"""
FinAnálisis: versión web GRATUITA (Streamlit).

Misma lógica que la plataforma de pago (carpeta services/), sin login ni Stripe.
- Datos fundamentales en vivo con yfinance (cacheados 15 min).
- Precio en directo que se refresca solo cada 60 s.
- Valoración Barato / Razonable / Caro ajustada por sector.
- Comparador de hasta 4 empresas.
- Noticias de la empresa y contexto macro por RSS (se renuevan cada 10 min).

Local:        streamlit run streamlit_app.py
Publicación:  Streamlit Community Cloud (ver LEEME.md)
"""
import html
import re

import streamlit as st
import yfinance as yf

from services import news
from services.market_data import fetch_company
from services.ratios import compute_ratios
from services.valuation import benchmark_for, evaluate

st.set_page_config(page_title="FinAnálisis", page_icon="📈", layout="wide")

RATIO_ORDER = ["per", "ev_ebitda", "fcf_yield", "div_yield", "nd_ebitda"]
TICKER_RE = re.compile(r"^[A-Za-z0-9.\-^=]{1,15}$")
MAX_COMPARE = 4

# ------------------------------------------------------------------ estilos
st.markdown("""
<style>
.tag{display:inline-block;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:600;white-space:nowrap}
.cheap{background:rgba(31,157,85,.18);color:#2fbf71}
.fair{background:rgba(214,158,46,.20);color:#d69e2e}
.expensive{background:rgba(229,62,62,.18);color:#e5534b}
.neutral{background:rgba(128,128,128,.18);color:#999}
.verdict{border:2px solid;border-radius:12px;padding:12px 18px;text-align:center}
.verdict b{display:block;font-size:26px}
.verdict.cheap{border-color:#2fbf71}.verdict.fair{border-color:#d69e2e}
.verdict.expensive{border-color:#e5534b}.verdict.neutral{border-color:#888}
table.fa{width:100%;border-collapse:collapse;font-size:15px}
table.fa th,table.fa td{padding:9px 8px;border-bottom:1px solid rgba(128,128,128,.25);text-align:left;vertical-align:top}
table.fa th{opacity:.7;font-weight:500}
table.fa td.num{text-align:right;white-space:nowrap}
.small{opacity:.7;font-size:13px}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ datos (cacheados)
@st.cache_data(ttl=900, show_spinner=False)
def analyse(ticker: str) -> dict:
    data = fetch_company(ticker, cache_seconds=0)   # la caché la gestiona Streamlit
    ratios = compute_ratios(data)
    verdicts, overall = evaluate(ratios, data.sector)
    return {"data": data, "ratios": ratios, "verdicts": verdicts,
            "overall": overall, "benchmark": benchmark_for(data.sector)}


@st.cache_data(ttl=30, show_spinner=False)
def live_quote(ticker: str) -> dict | None:
    try:
        fi = yf.Ticker(ticker).fast_info
        price, prev = fi.get("last_price"), fi.get("previous_close")
        chg = (price / prev - 1) * 100 if price and prev else None
        return {"price": price, "chg": chg, "currency": fi.get("currency") or ""}
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def company_news(ticker: str, name: str) -> list:
    return news.company_news(ticker, name, ttl=0)


@st.cache_data(ttl=600, show_spinner=False)
def macro_news() -> list:
    return news.macro_news(ttl=0)


# ------------------------------------------------------------------ helpers de formato
def big(x, cur=""):
    if x is None:
        return "N/D"
    s, x = ("-" if x < 0 else ""), abs(x)
    for d, suf in ((1e12, " T"), (1e9, " B"), (1e6, " M")):
        if x >= d:
            return f"{s}{x / d:,.2f}{suf} {cur}".strip()
    return f"{s}{x:,.0f} {cur}".strip()


def tag(v) -> str:
    return f'<span class="tag {v.css}">{html.escape(v.label)}</span>'


def bench_txt(ratio, v) -> str:
    if v.benchmark is None:
        return "–"
    return f"{v.benchmark * 100:.1f} %" if ratio.fmt == "%" else f"{v.benchmark:.1f}x"


def news_block(items, empty="Sin titulares recientes."):
    if not items:
        st.caption(empty)
        return
    rows = []
    for n in items:
        when = n["published"].strftime("%d/%m %H:%M") + " UTC" if n["published"] else ""
        rows.append(
            f'<div style="padding:7px 0;border-bottom:1px solid rgba(128,128,128,.2)">'
            f'<a href="{html.escape(n["link"], quote=True)}" target="_blank" rel="noopener">'
            f'{html.escape(n["title"])}</a><br>'
            f'<span class="small">{html.escape(n["source"])} · {when}</span></div>')
    st.markdown("".join(rows), unsafe_allow_html=True)


def clean_tickers(raw: str) -> list[str]:
    ts = [t.strip().upper() for t in re.split(r"[,\s;]+", raw) if t.strip()]
    return [t for t in dict.fromkeys(ts) if TICKER_RE.match(t)]


# ------------------------------------------------------------------ precio en directo
@st.fragment(run_every="60s")
def live_price_box(ticker: str):
    q = live_quote(ticker)
    if q and q["price"]:
        st.metric(f"Precio en vivo ({q['currency']})", f"{q['price']:,.2f}",
                  f"{q['chg']:+.2f} %" if q["chg"] is not None else None)
        st.caption("Se actualiza solo cada minuto · retraso habitual de Yahoo: ~15 min en algunos mercados")
    else:
        st.caption("Precio en vivo no disponible ahora mismo.")


# ------------------------------------------------------------------ vistas
def view_analyse():
    default = st.query_params.get("t", "NFLX")
    c1, c2 = st.columns([4, 1])
    ticker = c1.text_input("Ticker", value=default, placeholder="NFLX, AAPL, SAN.MC, ITX.MC…",
                           label_visibility="collapsed").strip().upper()
    c2.button("Analizar", type="primary", use_container_width=True)

    if not ticker:
        return
    if not TICKER_RE.match(ticker):
        st.error("Ticker no válido.")
        return
    st.query_params["t"] = ticker

    main, side = st.columns([2.2, 1], gap="large")
    with main:
        try:
            with st.spinner(f"Descargando datos de {ticker}…"):
                r = analyse(ticker)
        except ValueError as e:
            st.error(str(e))
            return
        except Exception:
            st.error("Yahoo Finance no responde ahora mismo (puede ser un límite temporal). "
                     "Prueba de nuevo en un par de minutos.")
            return

        d = r["data"]
        h1, h2 = st.columns([3, 1.3])
        h1.subheader(f"{d.name} ({d.ticker})")
        h1.caption(f"{d.sector or 'Sector desconocido'}{' · ' + d.industry if d.industry else ''}")
        ov = r["overall"]
        score = f"<br><span class='small'>puntuación {ov.score:+.2f}</span>" if ov.score is not None else ""
        h2.markdown(f'<div class="verdict {ov.css}"><span class="small">Valoración global</span>'
                    f'<b>{html.escape(ov.label)}</b>{score}</div>', unsafe_allow_html=True)

        m = st.columns(4)
        with m[0]:
            live_price_box(ticker)
        m[1].metric("Capitalización", big(d.market_cap, d.currency))
        m[2].metric("Enterprise Value", big(r["ratios"]["_ev"].value, d.currency))
        m[3].metric("Deuda neta", big(r["ratios"]["_net_debt"].value, d.currency))
        m = st.columns(4)
        m[0].metric(f"Beneficio neto ({d.basis.get('Beneficio neto') or '–'})", big(d.net_income, d.currency))
        m[1].metric(f"EBITDA ({d.basis.get('EBITDA') or '–'})", big(d.ebitda, d.currency))
        m[2].metric(f"FCF ({d.basis.get('FCF') or '–'})", big(d.free_cash_flow, d.currency))
        m[3].metric("Dividendo/acción 12m",
                    f"{d.dividends_per_share:.2f}" if d.dividends_per_share is not None else "N/D")

        rows = []
        for k in RATIO_ORDER:
            ra, v = r["ratios"][k], r["verdicts"][k]
            note = f' <span class="small">({html.escape(ra.note)})</span>' if ra.note else ""
            detail = f' <span class="small">{html.escape(v.detail)}</span>' if v.detail else ""
            rows.append(f"<tr><td>{ra.label}</td><td class='num'>{ra.display()}{note}</td>"
                        f"<td class='num small'>{bench_txt(ra, v)}</td><td>{tag(v)}{detail}</td></tr>")
        st.markdown("<table class='fa'><thead><tr><th>Ratio</th><th style='text-align:right'>Valor</th>"
                    "<th style='text-align:right'>Ref. sector</th><th>Clasificación</th></tr></thead>"
                    f"<tbody>{''.join(rows)}</tbody></table>", unsafe_allow_html=True)
        for w in d.warnings:
            st.warning(w)
        st.caption("TTM = suma de los 4 últimos trimestres publicados. Deuda neta/EBITDA mide solvencia, "
                   "no precio, y no entra en la valoración global.")

        st.markdown(f"#### Últimas noticias de {d.name}")
        news_block(company_news(ticker, d.name))

    with side:
        st.markdown("#### Contexto macro")
        news_block(macro_news())


def view_compare():
    raw = st.text_input("Tickers a comparar (hasta 4, separados por comas)",
                        value=st.query_params.get("c", "NFLX, DIS, WBD"))
    tickers = clean_tickers(raw)[:MAX_COMPARE]
    if not tickers:
        return
    st.query_params["c"] = ",".join(tickers)

    results = []
    with st.spinner("Descargando datos…"):
        for t in tickers:
            try:
                results.append(analyse(t))
            except Exception as e:
                st.error(f"{t}: {e}")
    if not results:
        return

    head = "".join(f"<th>{r['data'].ticker}<br><span class='small'>{html.escape(r['data'].name)}</span></th>"
                   for r in results)
    body = []
    body.append("<tr><td>Sector</td>" + "".join(f"<td>{html.escape(r['data'].sector or '–')}</td>" for r in results) + "</tr>")
    body.append("<tr><td>Capitalización</td>" + "".join(f"<td class='num'>{big(r['data'].market_cap, r['data'].currency)}</td>" for r in results) + "</tr>")
    body.append("<tr><td>Deuda neta</td>" + "".join(f"<td class='num'>{big(r['ratios']['_net_debt'].value, r['data'].currency)}</td>" for r in results) + "</tr>")
    for k in RATIO_ORDER:
        label = results[0]["ratios"][k].label
        cells = "".join(f"<td class='num'>{r['ratios'][k].display()}<br>{tag(r['verdicts'][k])}</td>" for r in results)
        body.append(f"<tr><td>{label}</td>{cells}</tr>")
    cells = "".join(
        f"<td class='num'>{tag(r['overall'])}"
        f"{'<br><span class=small>' + format(r['overall'].score, '+.2f') + '</span>' if r['overall'].score is not None else ''}</td>"
        for r in results)
    body.append(f"<tr><td><b>Valoración global</b></td>{cells}</tr>")

    st.markdown(f"<div style='overflow-x:auto'><table class='fa'><thead><tr><th></th>{head}</tr></thead>"
                f"<tbody>{''.join(body)}</tbody></table></div>", unsafe_allow_html=True)
    st.caption("Cada empresa se compara con la referencia de SU sector. La puntuación (negativa = más barata) "
               "permite comparar entre sectores distintos.")


def view_method():
    st.markdown("""
**Cómo se clasifica cada ratio**

Cada ratio se compara con un valor de referencia de su sector:

`s = ln(valor / referencia) / ln(1 + tolerancia)`

- **s < −1 → Barato** · **−1 ≤ s ≤ 1 → Razonable** · **s > 1 → Caro**
- Múltiplos (PER, EV/EBITDA): tolerancia ±20 %. Rentabilidades (FCF, dividendo): ±25 % y signo invertido
  (más rentabilidad = más barato).
- La escala logarítmica es simétrica: un PER al doble de la referencia está igual de lejos que uno a la mitad.
- Bancos y aseguradoras: EV/EBITDA, FCF y deuda neta no aplican.
- **Valoración global** = media de las puntuaciones (umbral ±0,5).
""")
    from services.valuation import SECTOR_BENCHMARKS
    st.markdown("**Referencias por sector**")
    st.dataframe(
        [{"Sector": s, "PER": b["per"], "EV/EBITDA": b["ev_ebitda"],
          "FCF yield %": b["fcf_yield"] and round(b["fcf_yield"] * 100, 1),
          "Div. yield %": b["div_yield"] and round(b["div_yield"] * 100, 1),
          "DN/EBITDA": b["nd_ebitda"]} for s, b in SECTOR_BENCHMARKS.items()],
        hide_index=True, use_container_width=True)


# ------------------------------------------------------------------ layout
st.title("FinAnálisis")
st.caption("Análisis fundamental en tiempo real, con valoración ajustada por sector")

tab1, tab2, tab3 = st.tabs(["Analizar", "Comparar", "Metodología"])
with tab1:
    view_analyse()
with tab2:
    view_compare()
with tab3:
    view_method()

st.divider()
st.caption("Información con fines exclusivamente educativos e informativos. No constituye recomendación "
           "personalizada de inversión. Datos de Yahoo Finance y Google News, sin garantía de exactitud.")
