"""
Control de acceso de edición.

- Por defecto todo visitante está en MODO LECTURA.
- La clave de administrador vive en los *secrets* del servidor (ADMIN_PIN),
  nunca en el código ni en el navegador. La comprobación se hace en el servidor.
- Tras 5 intentos fallidos la sesión se bloquea 5 minutos.
- Cualquier función que escribe datos vuelve a llamar a require_admin():
  ocultar los botones no basta como seguridad.
"""
import hashlib
import hmac
import time

import streamlit as st

MAX_ATTEMPTS = 5
LOCK_SECONDS = 300


def _configured_pin() -> str | None:
    try:
        pin = st.secrets.get("ADMIN_PIN")
    except Exception:   # no hay secrets.toml
        return None
    return str(pin) if pin else None


def is_configured() -> bool:
    return _configured_pin() is not None


def is_admin() -> bool:
    return bool(st.session_state.get("_admin")) and is_configured()


def locked_for() -> int:
    until = st.session_state.get("_lock_until", 0)
    return max(0, int(until - time.time()))


def login(pin: str) -> tuple[bool, str]:
    real = _configured_pin()
    if real is None:
        return False, "El acceso de edición no está configurado en el servidor."
    if locked_for():
        return False, f"Demasiados intentos. Espera {locked_for()} s."
    ok = hmac.compare_digest(hashlib.sha256(pin.encode()).digest(),
                             hashlib.sha256(real.encode()).digest())
    if ok:
        st.session_state["_admin"] = True
        st.session_state["_attempts"] = 0
        return True, "Modo edición activado."
    n = st.session_state.get("_attempts", 0) + 1
    st.session_state["_attempts"] = n
    if n >= MAX_ATTEMPTS:
        st.session_state["_lock_until"] = time.time() + LOCK_SECONDS
        st.session_state["_attempts"] = 0
        return False, "Demasiados intentos. Acceso bloqueado 5 minutos."
    return False, f"Clave incorrecta ({MAX_ATTEMPTS - n} intentos restantes)."


def logout() -> None:
    st.session_state["_admin"] = False


def require_admin() -> None:
    """Barrera de seguridad para cualquier operación de escritura."""
    if not is_admin():
        st.error("Operación no permitida: la plataforma está en modo lectura.")
        st.stop()
