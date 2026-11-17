# FinAnálisis: versión web gratuita

Web pública y gratuita de análisis fundamental en tiempo real. Todo se hace desde
el navegador: no hace falta instalar Python.

## Qué hay en la carpeta

| Elemento | Para qué sirve |
|---|---|
| `streamlit_app.py` | La web: pantallas Analizar, Comparar y Metodología |
| `services/` | El motor de cálculo: datos (yfinance), ratios, valoración por sector y noticias. Es el mismo que usará la versión de pago |
| `requirements.txt` | Lista de librerías que el servidor instala solo |
| `.streamlit/config.toml` | Colores de la web (tema oscuro, acento rojo) |

## Publicarla gratis (unos 10 minutos)

1. **Crea una cuenta en GitHub** en https://github.com/signup (gratis).
2. Pulsa **"+" → New repository**.
   - Nombre: `finanalisis`
   - Marca **Public** y pulsa **Create repository**.
3. En la página del repositorio vacío, pulsa el enlace **"uploading an existing file"**.
   Arrastra **el contenido** de esta carpeta, no la carpeta en sí: `streamlit_app.py`,
   `requirements.txt`, `LEEME.md` y las carpetas `services` y `.streamlit`.
   Abajo, pulsa **Commit changes**.
4. Entra en https://share.streamlit.io y elige **Continue with GitHub** (autoriza el acceso).
5. Pulsa **Create app → Deploy a public app from GitHub** y rellena:
   - Repository: `tu-usuario/finanalisis`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: elige un nombre, p. ej. `finanalisis-estani`
6. Pulsa **Deploy**. En 2-3 minutos tendrás tu web en
   `https://finanalisis-estani.streamlit.app`, abierta a cualquiera.

**Para cambiar algo:** edita el archivo en GitHub (icono del lápiz → Commit) y la web se
actualiza sola en un minuto.

## Qué es "tiempo real" aquí

- **Precio:** se refresca solo cada 60 s. Yahoo puede ir unos 15 min retrasado en algunos mercados.
- **Estados financieros:** se descargan en vivo y se guardan 15 min. Cambian solo cuando la empresa publica resultados.
- **Noticias:** de Yahoo Finance y Google News, renovadas cada 10 min.

## Límites de la versión gratuita

- Si nadie entra en varios días, la web "se duerme". El primer visitante pulsa un botón
  para despertarla y tarda unos 30 s.
- Yahoo a veces limita las peticiones desde servidores compartidos. Si aparece el aviso
  "Yahoo Finance no responde", basta con esperar un par de minutos. Es la principal razón
  para pasar a un proveedor de datos de pago en la versión comercial.
- Tickers fuera de EE. UU. con sufijo de Yahoo: `.MC` (Madrid), `.PA` (París),
  `.DE` (Xetra), `.L` (Londres), `.MI` (Milán).
