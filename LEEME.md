# FinAnálisis v3: sectores, academia y modo edición

## Estructura

```
streamlit_app.py        Menú superior, pie y botón discreto «Acceso»
content.json            TODO el contenido editable: textos, 30 vídeos y 10 ETFs
.streamlit/config.toml  Tema oscuro
services/
  auth.py               Modo lectura / edición (clave en los secrets del servidor)
  content.py            Cargar, validar, guardar y publicar content.json en GitHub
  etf_data.py           Cotizaciones y métricas de los ETFs
  compound.py           Cálculos de interés compuesto
  news.py               Noticias económicas por RSS
vistas/
  inicio.py             Portada: pulso del mercado, últimas clases, noticias
  sectores.py           Tabla de los 10 sectores, gráfico comparativo y fichas
  academia.py           Biblioteca de vídeos en cuadrícula con reproductor emergente
  interes.py            Calculadora de interés compuesto
  sobre.py              Página informativa
  admin.py              Panel de edición (solo administrador)
  ui.py                 Estilos y utilidades
videos/                 Vídeos .mp4 opcionales
tests/test_core.py      Pruebas automáticas (pytest)
```

## Cómo funciona la seguridad

- Cualquier visitante está en **modo lectura**: no ve el panel de administración y no puede cambiar nada.
- En el pie de cada página hay un botón discreto **«Acceso»**. Pide la clave de administrador.
- La clave **no está en el código**: vive en los *Secrets* de Streamlit, en el servidor.
  Aunque alguien lea todo el repositorio, no la verá.
- Tras 5 claves incorrectas, la sesión se bloquea 5 minutos.
- Cada acción de guardado vuelve a comprobar el permiso: ocultar los botones no es la única barrera.

## Cómo se guardan los cambios

Al pulsar «Guardar y publicar», la app:
1. Comprueba que el contenido es válido (por ejemplo, que ningún ETF se quede sin ticker).
2. Lo guarda en el servidor, y se ve al instante.
3. Hace un *commit* de `content.json` en tu GitHub, para que el cambio sobreviva a los
   reinicios de Streamlit. Para eso hace falta el `GITHUB_TOKEN` (paso 3 del despliegue).

## Despliegue (sobre la app que ya tienes)

### 1. Subir los archivos
En tu repositorio de GitHub: **Agregar archivo → Subir archivos** y arrastra **el contenido**
de la carpeta: `streamlit_app.py`, `content.json`, `requirements.txt`, `LEEME.md` y las carpetas
`services`, `vistas`, `videos` y `tests`. Después pulsa **Confirmar cambios**.
Los archivos con el mismo nombre se sustituyen solos.

### 2. Tema oscuro (`.streamlit/config.toml`)
GitHub no sube bien las carpetas que empiezan por punto. Créala a mano:
**Agregar archivo → Crear nuevo archivo**, escribe como nombre `.streamlit/config.toml`
(al escribir la barra `/` se crea la carpeta), pega el contenido del archivo y confirma.
Después borra el `config.toml` suelto que había en la raíz.

### 3. Secrets (clave de administrador y guardado en GitHub)
**a) Crea un token de GitHub**: tu foto (arriba a la derecha) → *Settings* → *Developer settings*
→ *Personal access tokens* → **Fine-grained tokens** → *Generate new token*.
- *Repository access*: **Only select repositories** → `finanalisis`
- *Permissions → Repository permissions → Contents*: **Read and write**
- Caducidad: 1 año. Copia el token (empieza por `github_pat_`). Solo se muestra una vez.

**b) Pégalo en Streamlit**: en share.streamlit.io, junto a tu app, pulsa **⋮ → Settings → Secrets** y escribe:

```toml
ADMIN_PIN = "elige-una-clave-larga-que-no-uses-en-otro-sitio"
GITHUB_TOKEN = "github_pat_xxxxxxxxxxxxxxxx"
GITHUB_REPO = "estanitojr-wq/finanalisis"
GITHUB_BRANCH = "main"
```
Pulsa **Save**. La app se reinicia sola.

### 4. Vídeos
Lo más fluido es subirlos a **YouTube** (sirven también los Shorts) y pegar el enlace en
*Administración → Vídeos → URL*. La miniatura aparece sola.
Alternativa: sube el `.mp4` a la carpeta `videos/` y escribe su nombre en la columna *Archivo*.

## Datos y fuentes
- Cotizaciones: Yahoo Finance, ETFs de Xetra en euros, con dividendos reinvertidos (se refrescan cada hora).
- Peso de cada sector: ficha del índice MSCI World (editable en el panel).
- ETFs: gama Xtrackers MSCI World por sectores (TER 0,25 %).
- Si Yahoo limita las consultas, la web sigue funcionando con los datos fijos y avisa.

## Pruebas
```bash
pip install -r requirements.txt pytest numpy
pytest -q
```
