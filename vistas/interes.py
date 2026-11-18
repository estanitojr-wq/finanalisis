"""Página Interés compuesto: teoría, calculadora, ejemplos y vídeo."""
import streamlit as st

from services import compound
from services import content as content_svc

from .ui import es


def render():
    st.markdown('<div class="kicker">Herramientas</div>', unsafe_allow_html=True)
    st.title("El interés compuesto")
    st.markdown("""
El interés compuesto consiste en **ganar intereses sobre los intereses**. El primer año ganas
sobre lo que pusiste; el segundo, sobre lo que pusiste **más** lo que ya ganaste; y así cada año.
Al principio apenas se nota, pero con el tiempo la curva se dispara: es una **bola de nieve**.

La fórmula, para un capital inicial **C**, una rentabilidad anual **r** y **n** años:
""")
    st.latex(r"V_{final} = C \cdot (1 + r)^{n}")

    # ---- de dónde sale el dinero
    st.subheader("¿De dónde sale realmente ese dinero?")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**Intereses**  \nSi prestas dinero (un depósito, un bono), el banco o el Estado "
                "te paga por usarlo. Si no lo gastas y lo vuelves a prestar, el año siguiente cobras "
                "intereses también sobre esos intereses.")
    c2.markdown("**Dividendos reinvertidos**  \nLas empresas reparten parte de sus beneficios. "
                "Si con ese dividendo compras más acciones, el próximo dividendo será mayor porque "
                "tienes más acciones.")
    c3.markdown("**Beneficios que se reinvierten**  \nLa mayoría de lo que gana una empresa se queda "
                "dentro: abre fábricas, contrata y crece. Una empresa que gana más vale más, y eso "
                "se ve en el precio de la acción.")
    st.info("Un **fondo indexado de acumulación** (por ejemplo, un MSCI World) hace todo esto solo: "
            "reinvierte automáticamente los dividendos de miles de empresas. Tú solo tienes que "
            "aportar y esperar.")

    # ---- vídeo
    video = content_svc.find_video_file("interes_compuesto.mp4")
    if video:
        st.subheader("Explicado en vídeo")
        st.video(str(video))

    # ---- calculadora
    st.subheader("Calculadora")
    i1, i2, i3 = st.columns(3)
    initial = i1.number_input("Capital inicial (€)", 0, 10_000_000, 1_000, step=500)
    monthly = i2.number_input("Aportación mensual (€)", 0, 100_000, 200, step=50)
    years = i3.slider("Años", 1, 50, 30)
    i4, i5, i6 = st.columns(3)
    rate = i4.slider("Rentabilidad anual (%)", 0.0, 15.0, 7.0, 0.5,
                     help="La bolsa mundial ha dado históricamente alrededor de un 7 % anual "
                          "a largo plazo, con años muy buenos y años muy malos.") / 100
    fee = i5.slider("Comisiones anuales (%)", 0.0, 2.5, 0.2, 0.05,
                    help="Un fondo indexado suele cobrar menos del 0,3 %; uno de gestión activa, 1-2 %.") / 100
    infl = i6.slider("Inflación anual (%)", 0.0, 6.0, 2.5, 0.5) / 100

    rows = compound.simulate(initial, monthly, rate, years, fee)
    last = rows[-1]
    gains = last["balance"] - last["contributed"]
    real = compound.real_value(last["balance"], infl, years)
    m = st.columns(4)
    m[0].metric("Tendrás", f"{es(last['balance'], 0)} €")
    m[1].metric("Has aportado tú", f"{es(last['contributed'], 0)} €")
    m[2].metric("Intereses generados", f"{es(gains, 0)} €",
                f"{es(gains / last['contributed'] * 100, 0)} % sobre lo aportado" if last["contributed"] else None)
    m[3].metric("En euros de hoy", f"{es(real, 0)} €", help="Descontando la inflación: lo que podrías "
                "comprar con ese dinero a precios de hoy.")

    chart = {
        "Año": [r["year"] for r in rows],
        "Lo que aportas": [round(r["contributed"]) for r in rows],
        "Intereses": [round(r["balance"] - r["contributed"]) for r in rows],
    }
    st.bar_chart(chart, x="Año", y=["Lo que aportas", "Intereses"],
                 color=["#4a7bd0", "#2fbf71"], y_label="€")

    if fee > 0:
        no_fee = compound.simulate(initial, monthly, rate, years, 0)[-1]["balance"]
        st.caption(f"Las comisiones del {es(fee * 100)} % te cuestan **{es(no_fee - last['balance'], 0)} €** "
                   f"en {years} años.")

    # ---- simple vs compuesto
    st.subheader("Simple contra compuesto")
    st.markdown("Con **interés simple** solo cobras sobre lo que pusiste al principio. "
                "Con **compuesto**, también sobre lo ganado. Mismo dinero y misma rentabilidad:")
    cap, yrs = 10_000, 30
    simple = compound.simple_interest(cap, rate, yrs)
    comp = [r["balance"] for r in compound.simulate(cap, 0, rate, yrs)]
    st.line_chart({"Año": list(range(yrs + 1)), "Simple": [round(v) for v in simple],
                   "Compuesto": [round(v) for v in comp]},
                  x="Año", y=["Simple", "Compuesto"], color=["#d69e2e", "#2fbf71"], y_label="€")
    st.caption(f"{es(cap, 0)} € al {es(rate * 100, 1)} % durante {yrs} años: "
               f"{es(simple[-1], 0)} € con simple frente a {es(comp[-1], 0)} € con compuesto.")

    # ---- el tiempo vale más que el dinero
    st.subheader("El tiempo vale más que el dinero")
    ana, luis = compound.start_early_vs_late(rate=0.07)
    a, b = st.columns(2)
    a.markdown(f"**Ana** invierte 300 €/mes **solo de los 23 a los 33 años** y luego no aporta más.  \n"
               f"Pone {es(ana['contributed'], 0)} € → a los 58 tiene **{es(ana['balance'], 0)} €**")
    b.markdown(f"**Luis** invierte 300 €/mes **de los 33 a los 58 años**, sin parar.  \n"
               f"Pone {es(luis['contributed'], 0)} € → a los 58 tiene **{es(luis['balance'], 0)} €**")
    st.caption("Ejemplo hipotético al 7 % anual. Luis aporta 2,5 veces más dinero y aun así acaba con menos: "
               "a Ana le dio tiempo a crecer.")

    # ---- regla del 72
    st.subheader("La regla del 72")
    st.markdown("Divide **72 entre la rentabilidad anual** y sabrás cuántos años tarda tu dinero en duplicarse.")
    st.table([{"Rentabilidad": f"{p} %", "Regla del 72": f"{es(72 / p, 1)} años",
               "Exacto": f"{es(compound.years_to_double(p / 100)[1], 1)} años"} for p in (2, 4, 6, 7, 8, 10, 12)])

    # ---- advertencias
    st.subheader("Pero ojo")
    st.markdown("""
- **Nada está garantizado.** La bolsa ha tenido caídas del 30-50 % (2008, 2020, 2022). Para que el
  interés compuesto funcione hay que **no vender en las caídas**.
- **La inflación** se come parte de la ganancia: mira la cifra "en euros de hoy".
- **Las comisiones** también se componen, pero en tu contra. Un 1 % más al año puede costar decenas de miles de euros.
- **Impuestos:** en España las ganancias tributan al venderlas. Los fondos se pueden traspasar
  de uno a otro sin pagar impuestos hasta el reembolso final.

**Las 4 reglas:** empezar pronto · ser constante · comisiones bajas · paciencia.
""")
    st.caption("Contenido educativo, no es recomendación de inversión. Rentabilidades pasadas no garantizan las futuras.")
