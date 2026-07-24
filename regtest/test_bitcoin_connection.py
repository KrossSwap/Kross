#!/usr/bin/env python3
# Smoke test de conexión a Bitcoin Core (regtest / Polar).
#
# Verifica que el BitcoinCoreClient se conecte al nodo y que las operaciones
# básicas del cliente funcionen contra un nodo real:
#   - getbalance   -> get_onchain_balance()
#   - getnewaddress-> get_newaddress()
#   - getblockchaininfo (chequeo de que estamos en regtest)
#
# NO envía dinero: solo lecturas + generar una address (gratis).
#
# Config por variables de entorno (defaults = valores típicos de Polar):
#   BITCOIN_RPC_USER=polaruser
#   BITCOIN_RPC_PASSWORD=polarpass
#   BITCOIN_RPC_HOST=127.0.0.1
#   BITCOIN_RPC_PORT=18443        (regtest; ver el nodo en Polar -> Connect -> RPC)
#
# Uso:
#   BITCOIN_RPC_PORT=18443 python regtest/test_bitcoin_connection.py
import os
import sys

# Permite ejecutar el script desde la raíz del repo (para importar `btc`).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carga regtest/.env (no pisa variables ya seteadas en el entorno).
from _env import load_env
load_env()

from btc.client import BitcoinCoreClient, sats_to_btc


def main() -> int:
    print("== Bitcoin Core connection test (regtest/Polar) ==")
    print(f"host={os.environ['BITCOIN_RPC_HOST']}:{os.environ['BITCOIN_RPC_PORT']} "
          f"user={os.environ['BITCOIN_RPC_USER']}")

    client = BitcoinCoreClient.instance()

    # 1) Ping básico + confirmar red.
    try:
        info = client.rpc.getblockchaininfo()
    except Exception as e:
        print(f"[FAIL] No pude conectar / getblockchaininfo: {e}")
        return 1
    chain = info.get("chain")
    print(f"[OK]   Conectado. chain={chain} blocks={info.get('blocks')}")
    if chain != "regtest":
        print(f"[WARN] Se esperaba chain=regtest, pero el nodo dice '{chain}'.")

    # 2) Balance on-chain (en sats, como trabaja toda la app).
    try:
        balance = client.get_onchain_balance()
    except Exception as e:
        print(f"[FAIL] get_onchain_balance: {e}")
        return 1
    print(f"[OK]   Balance on-chain: {balance} sats ({sats_to_btc(balance)} BTC)")

    # 3) Generar una address nueva de recepción.
    try:
        addr = client.get_newaddress()
    except Exception as e:
        print(f"[FAIL] get_newaddress: {e}")
        return 1
    print(f"[OK]   Nueva address: {addr}")

    print("== Bitcoin Core: OK ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
