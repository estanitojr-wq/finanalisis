"""
Cálculo de ratios a partir de CompanyData (o cualquier objeto con esos atributos).
Funciones puras: sin red ni base de datos -> fáciles de testear.

Definiciones:
  Deuda neta        = Deuda total - Caja (y equivalentes + inversiones c/p)
  EV                = Capitalización + Deuda neta
  PER               = Capitalización / Beneficio neto TTM
  EV/EBITDA         = EV / EBITDA TTM
  Rentab. FCF       = FCF TTM / Capitalización
  Rentab. dividendo = Dividendos por acción últimos 12m / Precio
  Deuda neta/EBITDA = Deuda neta / EBITDA TTM
"""
from dataclasses import dataclass


@dataclass
class Ratio:
    key: str
    label: str
    value: float | None
    fmt: str            # "x" (múltiplo) o "%" (porcentaje)
    note: str = ""      # motivo si no es calculable

    def display(self) -> str:
        if self.value is None:
            return "N/D"
        return f"{self.value * 100:.2f} %" if self.fmt == "%" else f"{self.value:.2f}x"


def _div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def compute_ratios(d) -> dict[str, Ratio]:
    net_debt = None
    if d.total_debt is not None or d.cash is not None:
        net_debt = (d.total_debt or 0.0) - (d.cash or 0.0)
    ev = d.market_cap + net_debt if d.market_cap is not None and net_debt is not None else None

    r: dict[str, Ratio] = {}

    # PER: sin sentido con pérdidas
    if d.net_income is not None and d.net_income <= 0:
        r["per"] = Ratio("per", "PER", None, "x", "Beneficio negativo")
    else:
        r["per"] = Ratio("per", "PER", _div(d.market_cap, d.net_income), "x")

    if d.ebitda is not None and d.ebitda <= 0:
        r["ev_ebitda"] = Ratio("ev_ebitda", "EV/EBITDA", None, "x", "EBITDA negativo")
        r["nd_ebitda"] = Ratio("nd_ebitda", "Deuda neta/EBITDA", None, "x", "EBITDA negativo")
    else:
        r["ev_ebitda"] = Ratio("ev_ebitda", "EV/EBITDA", _div(ev, d.ebitda), "x")
        r["nd_ebitda"] = Ratio("nd_ebitda", "Deuda neta/EBITDA", _div(net_debt, d.ebitda), "x")

    r["fcf_yield"] = Ratio("fcf_yield", "Rentabilidad por FCF", _div(d.free_cash_flow, d.market_cap), "%")
    r["div_yield"] = Ratio("div_yield", "Rentabilidad por dividendo",
                           _div(d.dividends_per_share, d.price) if d.dividends_per_share is not None else None, "%")

    # Extras útiles para mostrar
    r["_ev"] = Ratio("_ev", "Enterprise Value", ev, "x")
    r["_net_debt"] = Ratio("_net_debt", "Deuda neta", net_debt, "x")
    return r
