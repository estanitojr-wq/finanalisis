"""
Cálculos de interés compuesto (funciones puras, sin Streamlit).

La rentabilidad anual se convierte a su equivalente mensual EXACTO:
    r_mes = (1 + r_año) ** (1/12) - 1
así un 7 % anual da exactamente un 7 % al año (repartirlo 7/12 daría un 7,23 %).
Las aportaciones se hacen al principio de cada mes.
"""


def monthly_rate(annual: float) -> float:
    return (1 + annual) ** (1 / 12) - 1


def simulate(initial: float, monthly: float, annual_return: float, years: int,
             fee: float = 0.0, contribute_years: int | None = None) -> list[dict]:
    """
    Evolución año a año.
    annual_return y fee en tanto por uno (0.07 = 7 %). La comisión se resta de la rentabilidad.
    contribute_years: años durante los que se aporta (None = todos).
    """
    r = monthly_rate(annual_return - fee)
    balance, contributed = initial, initial
    rows = [{"year": 0, "contributed": contributed, "balance": balance}]
    for y in range(1, years + 1):
        for _ in range(12):
            if contribute_years is None or y <= contribute_years:
                balance += monthly
                contributed += monthly
            balance *= 1 + r
        rows.append({"year": y, "contributed": contributed, "balance": balance})
    return rows


def simple_interest(initial: float, annual_return: float, years: int) -> list[float]:
    return [initial * (1 + annual_return * y) for y in range(years + 1)]


def real_value(amount: float, inflation: float, years: int) -> float:
    """Poder de compra en euros de hoy."""
    return amount / (1 + inflation) ** years


def years_to_double(annual_return: float) -> tuple[float, float]:
    """(regla del 72, valor exacto)."""
    import math
    return 72 / (annual_return * 100), math.log(2) / math.log(1 + annual_return)


def start_early_vs_late(monthly=300, rate=0.07, age_a=(23, 33), age_b=(33, 58), end_age=58):
    """Ana aporta solo de age_a; Luis de age_b. Ambos se miran a end_age."""
    a_years = age_a[1] - age_a[0]
    b_years = age_b[1] - age_b[0]
    ana = simulate(0, monthly, rate, end_age - age_a[0], contribute_years=a_years)[-1]
    luis = simulate(0, monthly, rate, end_age - age_b[0], contribute_years=b_years)[-1]
    return ana, luis
