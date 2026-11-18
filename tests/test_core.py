"""Tests de la lógica pura. Ejecuta:  pytest -q"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import compound, etf_data  # noqa: E402
from services import content as content_svc  # noqa: E402


# ------------------------------------------------------------------ métricas ETF
def series(start_price, annual, years=5.2):
    idx = pd.bdate_range(end="2026-11-17", periods=int(252 * years))
    daily = (1 + annual) ** (1 / 252)
    return pd.Series(start_price * daily ** np.arange(len(idx)), index=idx)


def test_metrics_crecimiento_constante():
    m = etf_data.metrics(series(100, 0.10))
    assert m["r1y"] == pytest.approx(0.10, abs=0.01)
    assert m["r3y"] == pytest.approx(0.10, abs=0.01)
    assert m["r5y"] == pytest.approx(0.10, abs=0.01)
    assert m["maxdd"] == pytest.approx(0.0)
    assert m["vol"] == pytest.approx(0.0, abs=1e-9)


def test_metrics_caida_maxima():
    s = series(100, 0.0)
    s.iloc[300:] = s.iloc[300:] * 0.6     # caída del 40 %
    assert etf_data.metrics(s)["maxdd"] == pytest.approx(-0.40, abs=1e-6)


def test_metrics_historia_corta_no_inventa_5_anos():
    m = etf_data.metrics(series(100, 0.05, years=2))
    assert m["r1y"] is not None and m["r5y"] is None and m["r3y"] is None


def test_metrics_vacio():
    assert etf_data.metrics(pd.Series(dtype=float))["price"] is None


def test_normalizado_base_100():
    df = pd.DataFrame({"A": series(50, 0.1), "B": series(200, -0.05)})
    n = etf_data.normalized(df, df.index[-252])
    assert n.iloc[0].tolist() == pytest.approx([100, 100])


# ------------------------------------------------------------------ contenido
def test_content_json_valido_y_completo():
    data = content_svc.load()
    assert content_svc.validate(data) == []
    assert len([v for v in data["videos"] if v.get("dia")]) == 30
    assert len(data["etfs"]) == 10
    assert sum(e["peso"] for e in data["etfs"]) < 100


def test_validate_detecta_errores():
    data = content_svc.load()
    bad = content_svc.clone(data)
    bad["etfs"][0]["ticker"] = ""
    bad["videos"][1]["id"] = bad["videos"][0]["id"]
    errs = content_svc.validate(bad)
    assert any("ticker" in e for e in errs) and any("identificador" in e for e in errs)


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ?si=abc",
    "https://youtube.com/shorts/dQw4w9WgXcQ",
    "https://www.youtube.com/embed/dQw4w9WgXcQ",
])
def test_youtube_id(url):
    assert content_svc.youtube_id(url) == "dQw4w9WgXcQ"


def test_playable_source():
    assert content_svc.playable_source({"url": "https://youtube.com/shorts/dQw4w9WgXcQ"}) \
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert content_svc.playable_source({"url": "", "archivo": "no_existe.mp4"}) is None
    assert content_svc.find_video_file("../../etc/passwd") is None   # sin salir de la carpeta


def test_round_trip_json():
    data = content_svc.load()
    assert json.loads(content_svc.to_json(data)) == data


# ------------------------------------------------------------------ interés compuesto
def test_compound_tasa_mensual_exacta():
    assert compound.simulate(1000, 0, 0.07, 1)[-1]["balance"] == pytest.approx(1070)
