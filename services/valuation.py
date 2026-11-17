"""
Valoración dinámica por sector.

Cada sector tiene un valor de referencia ("justo") por ratio. La clasificación
usa una distancia logarítmica normalizada por una tolerancia:

        s = ln(valor / referencia) / ln(1 + tolerancia)

  - s =  0  -> exactamente en la referencia del sector
  - s =  1  -> un "paso de tolerancia" por encima (p. ej. +20 %)
  - s = -1  -> un paso por debajo (≈ -17 %)

Para múltiplos (PER, EV/EBITDA) un valor alto = caro.
Para rentabilidades (FCF, dividendo) se invierte el signo: alta = barato.

  s < -1  -> Barato     |  -1 ≤ s ≤ 1 -> Razonable  |  s > 1 -> Caro

Usar logaritmos hace la escala simétrica (PER 2x la referencia está tan
"lejos" como 0,5x) y evita que un ratio extremo domine la nota global.

Las referencias son medianas aproximadas de largo plazo (estilo Damodaran,
mercado EE. UU./Europa). Están en un diccionario para que las ajustes.
"""
import math
from dataclasses import dataclass

# per, ev_ebitda: múltiplos   |  fcf_yield, div_yield: tantos por uno
# nd_ebitda: nivel de deuda "normal" del sector (veces EBITDA)
SECTOR_BENCHMARKS: dict[str, dict[str, float | None]] = {
    "Technology":             {"per": 25, "ev_ebitda": 18, "fcf_yield": 0.035, "div_yield": 0.008, "nd_ebitda": 1.0},
    "Communication Services": {"per": 20, "ev_ebitda": 12, "fcf_yield": 0.045, "div_yield": 0.015, "nd_ebitda": 2.0},
    "Consumer Cyclical":      {"per": 20, "ev_ebitda": 12, "fcf_yield": 0.045, "div_yield": 0.015, "nd_ebitda": 2.0},
    "Consumer Defensive":     {"per": 21, "ev_ebitda": 14, "fcf_yield": 0.045, "div_yield": 0.027, "nd_ebitda": 2.5},
    "Healthcare":             {"per": 22, "ev_ebitda": 15, "fcf_yield": 0.040, "div_yield": 0.015, "nd_ebitda": 2.0},
    # Bancos/aseguradoras: EV, EBITDA y deuda neta no tienen sentido económico
    "Financial Services":     {"per": 13, "ev_ebitda": None, "fcf_yield": None, "div_yield": 0.035, "nd_ebitda": None},
    "Industrials":            {"per": 20, "ev_ebitda": 13, "fcf_yield": 0.045, "div_yield": 0.017, "nd_ebitda": 2.0},
    "Energy":                 {"per": 12, "ev_ebitda": 6,  "fcf_yield": 0.080, "div_yield": 0.040, "nd_ebitda": 1.5},
    "Utilities":              {"per": 17, "ev_ebitda": 11, "fcf_yield": 0.030, "div_yield": 0.035, "nd_ebitda": 4.5},
    "Real Estate":            {"per": 30, "ev_ebitda": 18, "fcf_yield": 0.040, "div_yield": 0.040, "nd_ebitda": 6.0},
    "Basic Materials":        {"per": 15, "ev_ebitda": 8,  "fcf_yield": 0.060, "div_yield": 0.025, "nd_ebitda": 1.5},
}
DEFAULT_BENCHMARK = {"per": 18, "ev_ebitda": 12, "fcf_yield": 0.05, "div_yield": 0.02, "nd_ebitda": 2.0}

TOLERANCE = {"per": 0.20, "ev_ebitda": 0.20, "fcf_yield": 0.25, "div_yield": 0.25}
HIGHER_IS_CHEAPER = {"fcf_yield", "div_yield"}
SCORE_CAP = 3.0
VALUATION_KEYS = ("per", "ev_ebitda", "fcf_yield", "div_yield")


@dataclass
class Verdict:
    label: str          # Barato | Razonable | Caro | Saneada | Aceptable | Apalancada | N/D ...
    css: str            # cheap | fair | expensive | neutral
    score: float | None
    benchmark: float | None
    detail: str = ""


def benchmark_for(sector: str) -> dict:
    return SECTOR_BENCHMARKS.get(sector, DEFAULT_BENCHMARK)


def _label(score: float) -> tuple[str, str]:
    if score < -1:
        return "Barato", "cheap"
    if score > 1:
        return "Caro", "expensive"
    return "Razonable", "fair"


def classify(key: str, value: float | None, sector: str) -> Verdict:
    ref = benchmark_for(sector).get(key)

    if key == "nd_ebitda":
        return _classify_leverage(value, ref)
    if ref is None:
        return Verdict("No aplica", "neutral", None, None, "Ratio poco significativo en este sector")
    if value is None:
        return Verdict("N/D", "neutral", None, ref)

    if key == "div_yield" and value == 0:
        return Verdict("Sin dividendo", "neutral", None, ref, "No computa en la nota")
    if key in HIGHER_IS_CHEAPER and value < 0:
        # FCF negativo: la empresa quema caja -> penalización máxima
        return Verdict("Caro", "expensive", SCORE_CAP, ref, "FCF negativo")

    s = math.log(value / ref) / math.log(1 + TOLERANCE[key])
    if key in HIGHER_IS_CHEAPER:
        s = -s
    s = max(-SCORE_CAP, min(SCORE_CAP, s))
    label, css = _label(s)
    return Verdict(label, css, round(s, 2), ref)


def _classify_leverage(value, ref) -> Verdict:
    """Deuda neta/EBITDA mide riesgo, no precio: se etiqueta como salud financiera."""
    if ref is None:
        return Verdict("No aplica", "neutral", None, None, "Ratio poco significativo en este sector")
    if value is None:
        return Verdict("N/D", "neutral", None, ref)
    if value <= 0:
        return Verdict("Caja neta", "cheap", None, ref, "Más caja que deuda")
    if value <= ref:
        return Verdict("Saneada", "cheap", None, ref)
    if value <= ref * 1.5:
        return Verdict("Aceptable", "fair", None, ref)
    return Verdict("Apalancada", "expensive", None, ref)


def overall(verdicts: dict[str, Verdict]) -> Verdict:
    """Nota global = media de las puntuaciones de los ratios de valoración."""
    scores = [verdicts[k].score for k in VALUATION_KEYS if k in verdicts and verdicts[k].score is not None]
    if not scores:
        return Verdict("Datos insuficientes", "neutral", None, None)
    avg = sum(scores) / len(scores)
    # Umbral global más estrecho (0,5): la media ya suaviza los extremos
    if avg < -0.5:
        label, css = "Barato", "cheap"
    elif avg > 0.5:
        label, css = "Caro", "expensive"
    else:
        label, css = "Razonable", "fair"
    return Verdict(label, css, round(avg, 2), None, f"{len(scores)} ratios evaluados")


def evaluate(ratios: dict, sector: str) -> tuple[dict[str, Verdict], Verdict]:
    verdicts = {k: classify(k, r.value, sector) for k, r in ratios.items() if not k.startswith("_")}
    return verdicts, overall(verdicts)
