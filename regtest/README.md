# regtest — scripts de prueba

Scripts para probar la conexión de los clientes contra un entorno **regtest**
local levantado con [Polar](https://lightningpolar.com/).

## Qué hay

- `test_bitcoin_connection.py` — smoke test del `BitcoinCoreClient`
  (getblockchaininfo, balance, nueva address). No mueve fondos.
- `test_lnd_connection.py` — smoke test del `LNDCLient` por gRPC
  (GetInfo, balance de canales). No crea ni paga invoices.

## Setup con Polar

1. Abrí Polar y creá una red con al menos 1 nodo **LND** + 1 nodo **Bitcoin Core**.
2. Iniciá la red (Start).
3. Los datos de conexión de cada nodo están en la pestaña **Connect** del nodo.

## Correr los tests

Los scripts cargan solos `regtest/.env` (no se sube al repo). Copiá tus valores
de Polar ahí y después corré, desde la raíz del repo con el `.venv` activado:

```bash
python regtest/test_bitcoin_connection.py
python regtest/test_lnd_connection.py
```

Ejemplo de `regtest/.env`:

```dotenv
BITCOIN_RPC_USER=polaruser
BITCOIN_RPC_PASSWORD=polarpass
BITCOIN_RPC_HOST=127.0.0.1
BITCOIN_RPC_PORT=18443

LND_GRPC_HOST=127.0.0.1:10001
LND_TLS_CERT_PATH=/home/USUARIO/.polar/networks/2/volumes/lnd/alice/tls.cert
LND_MACAROON_PATH=/home/USUARIO/.polar/networks/2/volumes/lnd/alice/data/chain/bitcoin/regtest/admin.macaroon
```

También podés overridear puntualmente una variable sin tocar el `.env`
(tiene prioridad sobre el archivo):

```bash
LND_GRPC_HOST=127.0.0.1:10002 python regtest/test_lnd_connection.py
```

## Variables de entorno

### Bitcoin Core (`btc/client.py`)
| Var | Default | Polar |
| --- | --- | --- |
| `BITCOIN_RPC_USER` | `bitcoin` | `polaruser` |
| `BITCOIN_RPC_PASSWORD` | `bitcoin` | `polarpass` |
| `BITCOIN_RPC_HOST` | `localhost` | `127.0.0.1` |
| `BITCOIN_RPC_PORT` | `8332` | `18443` (regtest) |

> Los scripts ya setean los defaults de Polar si no hay nada en el entorno.

### LND (`ln/client.py`)
| Var | Default | Polar |
| --- | --- | --- |
| `LND_GRPC_HOST` | `localhost:10009` | `127.0.0.1:<puerto del nodo>` |
| `LND_TLS_CERT_PATH` | `~/.lnd/tls.cert` | `~/.polar/networks/<N>/volumes/lnd/<alias>/tls.cert` |
| `LND_MACAROON_PATH` | `~/.lnd/.../mainnet/admin.macaroon` | `.../data/chain/bitcoin/regtest/admin.macaroon` |
