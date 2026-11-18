"""Página Sectores: los 10 sectores del MSCI World a través de ETFs."""
from datetime import timedelta

import streamlit as st

from services import etf_data

from . import ui

SORTS = {"Peso en el índice": "peso", "Rentabilidad 1 año": "r1y", "Rentabilidad en el año": "ytd",
         "3 años anualizada": "r3y", "Volatilidad": "vol", "Comisión (TER)": "ter"}
PERIODS = {"1 año": 365, "3 años": 3 * 365, "5 años": 5 * 365}


def render():
    content = ui.get_content()
    etfs, bench = content["etfs"], content["benchmark"]
    closes, stats, err = ui.market_safe(content)

    st.markdown('<div class="kicker">Mercado global · ETFs sectoriales</div>', unsafe_allow_html=True)
    st.title("Los sectores de la economía mundial")
    st.markdown("Cada sector del índice **MSCI World** (unas 1.250 grandes empresas de 23 países "
                "desarrollados) tiene su propio ETF. Así puedes ver qué parte de la economía tira del "
                "mercado, cuánto pesa y cuánto cuesta invertir en ella.")
    ui.market_notice(err)

    # ---------------- tabla principal
    c1, c2 = st.columns([2, 1])
    order = c1.segmented_control("Ordenar por", list(SORTS), default="Peso en el índice",
                                 label_visibility="collapsed") or "Peso en el índice"
    key = SORTS[order]

    def sort_value(e):
        if key in ("peso", "ter"):
            return e.get(key) or 0
        v = stats.get(e["ticker"], {}).get(key)
        return v if v is not None else float("-inf")
    rows = sorted(etfs, key=sort_value, reverse=key != "ter")
    max_w = max((e.get("peso") or 0) for e in etfs) or 1

    body = []
    for e in rows:
        m = stats.get(e["ticker"], {})
        price = f'{ui.es(m["price"])} €' if m.get("price") else '<span class="muted">—</span>'
        w = e.get("peso") or 0
        body.append(
            f"<tr><td><b>{ui.esc(e['sector'])}</b><br><span class='small mono'>{ui.esc(e['ticker'])}</span></td>"
            f"<td class='num'>{ui.es(w, 1)} %<div class='bar'><i style='width:{w / max_w * 100:.0f}%'></i></div></td>"
            f"<td class='num'>{price}</td><td class='num'>{ui.pct(m.get('day'), 2)}</td>"
            f"<td class='num'>{ui.pct(m.get('ytd'))}</td><td class='num'>{ui.pct(m.get('r1y'))}</td>"
            f"<td class='num'>{ui.pct(m.get('r3y'))}</td><td class='num'>{ui.pct(m.get('r5y'))}</td>"
            f"<td class='num'>{ui.pct(m.get('vol'), 1, sign=False, color=False) if m.get('vol') else '—'}</td>"
            f"<td class='num'>{ui.pct(m.get('maxdd'))}</td>"
            f"<td class='num'>{ui.es(e.get('ter') or 0, 2)} %</td></tr>")
    bm = stats.get(bench["ticker"], {})
    body.append(
        f"<tr><td><b>MSCI World</b><br><span class='small mono'>{ui.esc(bench['ticker'])} · referencia</span></td>"
        f"<td class='num'>100 %</td><td class='num'>{ui.es(bm['price']) + ' €' if bm.get('price') else '—'}</td>"
        f"<td class='num'>{ui.pct(bm.get('day'), 2)}</td><td class='num'>{ui.pct(bm.get('ytd'))}</td>"
        f"<td class='num'>{ui.pct(bm.get('r1y'))}</td><td class='num'>{ui.pct(bm.get('r3y'))}</td>"
        f"<td class='num'>{ui.pct(bm.get('r5y'))}</td>"
        f"<td class='num'>{ui.pct(bm.get('vol'), 1, sign=False, color=False) if bm.get('vol') else '—'}</td>"
        f"<td class='num'>{ui.pct(bm.get('maxdd'))}</td><td class='num'>—</td></tr>")

    st.markdown(
        "<div class='wrap'><table class='term'><thead><tr><th>Sector</th><th>Peso</th><th>Precio</th>"
        "<th>Día</th><th>Año</th><th>1 año</th><th>3 años/año</th><th>5 años/año</th>"
        "<th>Volatilidad</th><th>Caída máx.</th><th>TER</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>", unsafe_allow_html=True)
    asof = next((m["asof"] for m in stats.values() if m.get("asof") is not None), None)
    st.caption(f"Peso: {content.get('pesos_fuente', 'MSCI World')}. Precios en euros (Xetra), con dividendos "
               f"reinvertidos{', cierre del ' + asof.strftime('%d/%m/%Y') if asof is not None else ''}. "
               "3 y 5 años: rentabilidad media anual. Caída máxima: 5 años.")

    # ---------------- gráfico comparativo
    st.subheader("Evolución comparada")
    if closes is not None:
        names = {e["ticker"]: e["sector"] for e in etfs}
        names[bench["ticker"]] = "MSCI World"
        g1, g2 = st.columns([3, 1])
        default = [e["sector"] for e in sorted(etfs, key=lambda x: -(x.get("peso") or 0))[:3]]
        chosen = g1.multiselect("Sectores", [e["sector"] for e in etfs], default=default,
                                label_visibility="collapsed")
        period = g2.segmented_control("Periodo", list(PERIODS), default="3 años",
                                      label_visibility="collapsed") or "3 años"
        cols = [t for t, n in names.items() if n in chosen and t in closes.columns]
        if bench["ticker"] in closes.columns:
            cols.append(bench["ticker"])
        since = closes.index[-1] - timedelta(days=PERIODS[period])
        df = etf_data.normalized(closes[cols], since).rename(columns=names)
        if not df.empty:
            st.line_chart(df, y_label="Base 100", height=380)
            st.caption("Base 100: cuánto valdrían 100 € invertidos al inicio del periodo.")
    else:
        st.info("El gráfico aparecerá cuando vuelvan las cotizaciones.")

    # ---------------- fichas
    st.subheader("Ficha de cada sector")
    sel = st.selectbox("Sector", [e["sector"] for e in etfs], label_visibility="collapsed")
    e = next(x for x in etfs if x["sector"] == sel)
    m = stats.get(e["ticker"], {})
    a, b = st.columns([1.4, 1])
    with a:
        st.markdown(f"#### {ui.esc(e['sector'])}")
        st.markdown(e.get("descripcion", ""))
        st.markdown(f"<span class='small'>ETF de referencia</span><br><b>{ui.esc(e['nombre'])}</b><br>"
                    f"<span class='mono small'>{ui.esc(e['ticker'])} · TER {ui.es(e.get('ter') or 0, 2)} % · "
                    f"{ui.es(e.get('peso') or 0, 1)} % del MSCI World</span>", unsafe_allow_html=True)
    with b:
        k = st.columns(2)
        k[0].metric("Precio", f"{ui.es(m['price'])} €" if m.get("price") else "—",
                    f"{ui.es(m['day'] * 100)} %" if m.get("day") is not None else None)
        k[1].metric("1 año", f"{ui.es(m['r1y'] * 100, 1)} %" if m.get("r1y") is not None else "—")
        k = st.columns(2)
        k[0].metric("Volatilidad", f"{ui.es(m['vol'] * 100, 1)} %" if m.get("vol") else "—")
        k[1].metric("Caída máx. 5 años", f"{ui.es(m['maxdd'] * 100, 1)} %" if m.get("maxdd") is not None else "—")

    st.caption(content["textos"].get("aviso_legal", ""))
