"""
Extracción de datos fundamentales con yfinance.

Se usan cifras TTM (últimos 12 meses = suma de los 4 últimos trimestres) cuando
existen; si no, el último ejercicio anual. Los nombres de las filas de yfinance
cambian entre versiones, por eso cada partida busca varios alias.
"""
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

_CACHE: dict[str, tuple[float, "CompanyData"]] = {}


@dataclass
class CompanyData:
    ticker: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    currency: str = ""
    price: float | None = None
    shares: float | None = None
    market_cap: float | None = None
    net_income: float | None = None        # TTM
    ebitda: float | None = None            # TTM
    free_cash_flow: float | None = None    # TTM
    total_debt: float | None = None        # último balance
    cash: float | None = None              # caja + inversiones a corto
    dividends_per_share: float | None = None  # pagados en los últimos 12 meses
    basis: dict = field(default_factory=dict)  # "TTM" o "Anual" por partida
    warnings: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


# ------------------------------------------------------------------ helpers
def _num(x):
    try:
        x = float(x)
        return None if math.isnan(x) or math.isinf(x) else x
    except (TypeError, ValueError):
        return None


def _row(df: pd.DataFrame | None, aliases: list[str]) -> pd.Series | None:
    if df is None or df.empty:
        return None
    for name in aliases:
        if name in df.index:
            return df.loc[name].dropna()
    return None


def _flow(quarterly, annual, aliases):
    """Partida de flujo (cuenta de resultados / cash flow): TTM o anual."""
    q = _row(quarterly, aliases)
    if q is not None and len(q) >= 4:
        return _num(q.sort_index(ascending=False).iloc[:4].sum()), "TTM"
    a = _row(annual, aliases)
    if a is not None and len(a):
        return _num(a.sort_index(ascending=False).iloc[0]), "Anual"
    return None, None


def _stock(quarterly, annual, aliases):
    """Partida de balance: el dato más reciente."""
    for df, label in ((quarterly, "Último trimestre"), (annual, "Anual")):
        r = _row(df, aliases)
        if r is not None and len(r):
            return _num(r.sort_index(ascending=False).iloc[0]), label
    return None, None


# ------------------------------------------------------------------ API
def fetch_company(ticker: str, cache_seconds: int = 900) -> CompanyData:
    ticker = ticker.strip().upper()
    hit = _CACHE.get(ticker)
    if hit and time.time() - hit[0] < cache_seconds:
        return hit[1]

    t = yf.Ticker(ticker)
    try:
        info = t.info or {}
    except Exception:
        info = {}

    d = CompanyData(ticker=ticker)
    d.name = info.get("longName") or info.get("shortName") or ticker
    d.sector = info.get("sector") or ""
    d.industry = info.get("industry") or ""
    d.currency = info.get("financialCurrency") or info.get("currency") or ""

    try:
        fi = t.fast_info
        d.price = _num(fi.get("last_price")) or _num(info.get("currentPrice"))
        d.shares = _num(fi.get("shares")) or _num(info.get("sharesOutstanding"))
        d.market_cap = _num(fi.get("market_cap")) or _num(info.get("marketCap"))
    except Exception:
        d.price = _num(info.get("currentPrice"))
        d.shares = _num(info.get("sharesOutstanding"))
        d.market_cap = _num(info.get("marketCap"))

    if d.price is None and d.market_cap is None:
        raise ValueError(f"No se encontraron datos para '{ticker}'. ¿Ticker correcto? (ej. NFLX, SAN.MC)")

    def safe(attr):
        try:
            return getattr(t, attr)
        except Exception:
            return None

    q_is, a_is = safe("quarterly_income_stmt"), safe("income_stmt")
    q_cf, a_cf = safe("quarterly_cashflow"), safe("cashflow")
    q_bs, a_bs = safe("quarterly_balance_sheet"), safe("balance_sheet")

    d.net_income, d.basis["Beneficio neto"] = _flow(
        q_is, a_is, ["Net Income Common Stockholders", "Net Income",
                     "Net Income From Continuing Operation Net Minority Interest"])
    d.ebitda, d.basis["EBITDA"] = _flow(q_is, a_is, ["EBITDA", "Normalized EBITDA"])
    d.free_cash_flow, d.basis["FCF"] = _flow(q_cf, a_cf, ["Free Cash Flow"])
    if d.free_cash_flow is None:  # FCF = CFO - CapEx
        cfo, b1 = _flow(q_cf, a_cf, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
        capex, _ = _flow(q_cf, a_cf, ["Capital Expenditure"])
        if cfo is not None and capex is not None:
            d.free_cash_flow, d.basis["FCF"] = cfo + capex, b1  # capex viene en negativo

    d.total_debt, d.basis["Deuda"] = _stock(q_bs, a_bs, ["Total Debt"])
    d.cash, d.basis["Caja"] = _stock(
        q_bs, a_bs, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"])

    # Fallbacks desde .info si los estados no vienen
    d.ebitda = d.ebitda if d.ebitda is not None else _num(info.get("ebitda"))
    d.free_cash_flow = d.free_cash_flow if d.free_cash_flow is not None else _num(info.get("freeCashflow"))
    d.total_debt = d.total_debt if d.total_debt is not None else _num(info.get("totalDebt"))
    d.cash = d.cash if d.cash is not None else _num(info.get("totalCash"))

    # Dividendos realmente pagados en los últimos 365 días
    try:
        divs = t.dividends
        if divs is not None and len(divs):
            cutoff = datetime.now(timezone.utc) - timedelta(days=365)
            idx = divs.index.tz_convert("UTC") if divs.index.tz is not None else divs.index.tz_localize("UTC")
            d.dividends_per_share = _num(divs[idx >= cutoff].sum()) or 0.0
        else:
            d.dividends_per_share = 0.0
    except Exception:
        d.dividends_per_share = _num(info.get("trailingAnnualDividendRate"))

    if d.currency and info.get("currency") and d.currency != info.get("currency"):
        d.warnings.append(
            f"Los estados financieros están en {d.currency} y la cotización en {info.get('currency')}: "
            "los ratios que mezclan ambos pueden estar distorsionados.")

    _CACHE[ticker] = (time.time(), d)
    return d
