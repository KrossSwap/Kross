#!/usr/bin/env python3
# Smoke test de conexión a LND (regtest / Polar) por gRPC.
#
# Verifica que el LNDCLient levante el canal gRPC con cert + macaroon y pueda
# hablar con el nodo:
#   - GetInfo        -> confirma identidad / red / sincronía
#   - ChannelBalance -> get_ln_balance()
#
# NO crea ni paga invoices: solo lecturas.
#
# Config por variables de entorno. En Polar, cada nodo LND expone su host gRPC
# y las rutas de cert/macaroon en la pestaña "Connect".
#   LND_GRPC_HOST=127.0.0.1:10001            (el puerto lo asigna Polar por nodo)
#   LND_TLS_CERT_PATH=~/.polar/networks/<N>/volumes/lnd/<alias>/tls.cert
#   LND_MACAROON_PATH=~/.polar/networks/<N>/volumes/lnd/<alias>/data/chain/bitcoin/regtest/admin.macaroon
#
# Uso:
#   LND_GRPC_HOST=127.0.0.1:10001 \
#   LND_TLS_CERT_PATH=/ruta/tls.cert \
#   LND_MACAROON_PATH=/ruta/admin.macaroon \
#   python regtest/test_lnd_connection.py
import os
import sys

# Permite ejecutar el script desde la raíz del repo (para importar `ln`).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carga regtest/.env (no pisa variables ya seteadas en el entorno).
from _env import load_env
load_env()

from ln.client import LNDCLient
from ln import lightning_pb2


def main() -> int:
    print("== LND connection test (regtest/Polar) ==")
    print(f"host={os.getenv('LND_GRPC_HOST', 'localhost:10009')}")
    print(f"cert={os.getenv('LND_TLS_CERT_PATH', '~/.lnd/tls.cert')}")
    print(f"macaroon={os.getenv('LND_MACAROON_PATH', '~/.lnd/.../admin.macaroon')}")

    try:
        client = LNDCLient.instance()
    except FileNotFoundError as e:
        print(f"[FAIL] No encuentro cert o macaroon: {e}")
        print("       Seteá LND_TLS_CERT_PATH y LND_MACAROON_PATH (ver Polar -> Connect).")
        return 1
    except Exception as e:
        print(f"[FAIL] No pude inicializar el cliente: {e}")
        return 1

    # 1) GetInfo: confirma que el macaroon autoriza y que el nodo responde.
    try:
        info = client.lightning.GetInfo(lightning_pb2.GetInfoRequest())
    except Exception as e:
        print(f"[FAIL] GetInfo: {e}")
        return 1
    print(f"[OK]   Conectado a LND. alias={info.alias} pubkey={info.identity_pubkey}")
    print(f"       version={info.version} synced_to_chain={info.synced_to_chain} "
          f"active_channels={info.num_active_channels}")
    chains = [c.chain + "/" + c.network for c in info.chains]
    print(f"       chains={chains}")
    if not any(c.network == "regtest" for c in info.chains):
        print("[WARN] El nodo no reporta la red 'regtest'.")

    # 2) Balance de canales (en sats).
    try:
        balance = client.get_ln_balance()
    except Exception as e:
        print(f"[FAIL] get_ln_balance: {e}")
        return 1
    print(f"[OK]   Balance local de canales: {balance} sats")

    print("== LND: OK ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
