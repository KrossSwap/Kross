# Loader mínimo de .env (sin dependencias). Lee regtest/.env y carga las
# variables en os.environ SIN pisar las que ya estén seteadas en el entorno
# (así podés override puntual con `VAR=... python ...`).
import os


def load_env() -> None:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            os.environ.setdefault(key, value)
