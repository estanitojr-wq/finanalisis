"""
Datos de mercado de los ETFs sectoriales (Yahoo Finance, cotización en euros en Xetra).

Métricas (funciones puras, testeables):
  - Precio, variación del día, rentabilidad en el año (YTD), 1 año,
    3 y 5 años anualizadas, volatilidad anual y caída máxima a 5 años.
"""
import math
import time
from datetime import timedelta

import pandas as pd


# ------------------------------------------------------------------ descarga
def download_closes(tickers: list[str], period: str = "5y", tries: int = 3) -> pd.DataFrame:
    """Cierres ajustados (dividendos incluidos) de todos los tickers en una sola llamada."""
    import yfinance as yf
    last_error = None
    for i in range(tries):
        try:
            df = yf.download(tickers, period=period, interval="1d", auto_adjust=True,
                             progress=False, threads=True, group_by="column")
            closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df[["Close"]]
            if isinstance(closes, pd.Series):
                closes = closes.to_frame(tickers[0])
            if closes.shape[1] == 1 and len(tickers) == 1:
                closes.columns = tickers
            closes = closes.dropna(how="all")
            if closes.empty:
                raise RuntimeError("Yahoo no devolvió datos")
            return closes
        except Exception as e:   # límite de Yahoo u otro fallo transitorio
            last_error = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"No se pudieron descargar cotizaciones: {last_error}")


# ------------------------------------------------------------------ métricas
def _price_on_or_before(s: pd.Series, when) -> float | None:
    s = s[s.index <= when]
    return float(s.iloc[-1]) if len(s) else None


def _annualized(last, past, years):
    if not last or not past or past <= 0:
        return None
    return (last / past) ** (1 / years) - 1


def metrics(series: pd.Series) -> dict:
    s = series.dropna()
    out = {k: None for k in ("price", "day", "ytd", "r1y", "r3y", "r5y", "vol", "maxdd", "asof")}
    if len(s) < 2:
        return out
    last, end = float(s.iloc[-1]), s.index[-1]
    out["price"], out["asof"] = last, end
    out["day"] = last / float(s.iloc[-2]) - 1

    prev_year_end = pd.Timestamp(year=end.year - 1, month=12, day=31, tz=end.tz)
    p = _price_on_or_before(s, prev_year_end)
    out["ytd"] = last / p - 1 if p else None

    first = s.index[0]
    for key, years in (("r1y", 1), ("r3y", 3), ("r5y", 5)):
        when = end - timedelta(days=round(365.25 * years))
        if first <= when + timedelta(days=7):           # hay historia suficiente
            past = _price_on_or_before(s, when)
            out[key] = (last / past - 1) if years == 1 and past else _annualized(last, past, years)

    one_year = s[s.index > end - timedelta(days=365)]
    rets = one_year.pct_change().dropna()
    if len(rets) > 20:
        out["vol"] = float(rets.std() * math.sqrt(252))

    drawdown = s / s.cummax() - 1
    out["maxdd"] = float(drawdown.min())
    return out


def normalized(closes: pd.DataFrame, since) -> pd.DataFrame:
    """Base 100 desde la fecha `since` (para comparar evolución)."""
    df = closes[closes.index >= since].ffill().dropna(how="all")
    if df.empty:
        return df
    return df.div(df.bfill().iloc[0]).mul(100)
