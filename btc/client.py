# Cliente de Bitcoin Core por JSON-RPC (NO gRPC).
# Wrapper fino sobre el RPC del nodo: balances, direcciones, fees, pagos
# batcheados y consulta de transacciones. Toda la app trabaja en SATS, así que
# convertimos en la frontera (Bitcoin Core habla en BTC).
#
# Nota de diseño: los pagos batcheados usan `sendmany` (Bitcoin Core maneja la
# selección de UTXOs y la dirección de change de forma automática y con una
# dirección nueva cada vez, que es lo más privado). El `return_address` queda
# reservado para un futuro camino con raw-tx si hiciera falta controlar el change.
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from bitcoinrpc.authproxy import AuthServiceProxy

# 1 BTC = 100.000.000 sats
SATS_PER_BTC = Decimal(100_000_000)


def btc_to_sats(amount_btc) -> int:
    return int((Decimal(amount_btc) * SATS_PER_BTC).to_integral_value())


def sats_to_btc(amount_sats: int) -> Decimal:
    # 8 decimales, que es la precisión de Bitcoin.
    return (Decimal(amount_sats) / SATS_PER_BTC).quantize(Decimal("0.00000001"))


@dataclass
class TransactionOutput:
    address: str
    amount_in_sats: int

@dataclass
class TransactionInput:
    address: str
    amount_in_sats: int

@dataclass
class Transaction:
    confirmations: int
    txid: str
    inputs: list[TransactionInput]
    outputs: list[TransactionOutput]


class BitcoinCoreClient:
    # Instancia singleton (ver .instance()).
    _instance: "BitcoinCoreClient | None" = None

    def __init__(self):
        # Config por variables de entorno.
        user = os.getenv("BITCOIN_RPC_USER", "bitcoin")
        password = os.getenv("BITCOIN_RPC_PASSWORD", "bitcoin")
        host = os.getenv("BITCOIN_RPC_HOST", "localhost")
        port = os.getenv("BITCOIN_RPC_PORT", "8332")
        # Bitcoin Core expone JSON-RPC sobre HTTP con auth básica.
        self._url = f"http://{user}:{password}@{host}:{port}"

    @property
    def rpc(self) -> AuthServiceProxy:
        # AuthServiceProxy no es reutilizable de forma segura entre threads ni
        # sobrevive bien a conexiones ociosas, así que creamos un proxy fresco
        # por acceso. Es barato (solo arma la URL; la conexión HTTP se abre al
        # llamar un método).
        return AuthServiceProxy(self._url)

    @staticmethod
    def instance() -> "BitcoinCoreClient":
        """
        Devuelve la instancia singleton del cliente.
        """
        if BitcoinCoreClient._instance is None:
            BitcoinCoreClient._instance = BitcoinCoreClient()
        return BitcoinCoreClient._instance

    #TODO: Create signal for a transaction being received
    # (se implementará en un watcher dedicado para el flujo swap-in)

    def get_onchain_balance(self) -> int:
        """
        Balance on-chain de la billetera, en sats.
        """
        balance_btc = self.rpc.getbalance()
        return btc_to_sats(balance_btc)

    def get_newaddress(self) -> str:
        """
        Genera una nueva dirección de recepción.
        """
        return self.rpc.getnewaddress()

    def get_fee_rate_per_byte(self, priority: Literal['high', 'medium', 'low'] = 'medium') -> int:
        """
        Fee estimada en sat/vByte según la prioridad (cuántos bloques esperar).
        Usa estimatesmartfee, que devuelve BTC/kvB; lo pasamos a sat/vByte.
        """
        # Menos bloques de target = más urgente = fee más alta.
        conf_target = {'high': 1, 'medium': 6, 'low': 25}[priority]
        result = self.rpc.estimatesmartfee(conf_target)
        feerate_btc_per_kvb = result.get('feerate') if isinstance(result, dict) else None
        if not feerate_btc_per_kvb:
            # El nodo no pudo estimar (típico en regtest o pocos datos de mempool).
            raise RuntimeError(f"No fee estimate available for priority '{priority}': {result}")
        # BTC/kvB -> sat/vByte: (BTC/1000 vB) * 1e8 sat/BTC
        sat_per_vbyte = (Decimal(feerate_btc_per_kvb) * SATS_PER_BTC) / Decimal(1000)
        return int(sat_per_vbyte.to_integral_value())

    def send_batched_payments(
        self,
        outputs: list[TransactionOutput],
        fee_per_vbyte: int,
        subtract_fees: bool = True,
        return_address: str | None = None,
    ) -> str:
        """
        Envía varios pagos en una sola transacción (batch) usando `sendmany`.
        Devuelve el txid.

        - fee_per_vbyte: fee objetivo en sat/vByte.
        - subtract_fees: si True, la fee se descuenta de los propios outputs
          (los recipientes reciben un poco menos); si False, la fee sale del
          balance de la billetera y los recipientes reciben el monto exacto.
        - return_address: reservado. `sendmany` maneja el change automáticamente
          (dirección nueva, más privado), así que por ahora no se usa.

        !PREVENT BUG: el monto de cada output debe ser SIEMPRE positivo, incluso
        tras descontarle la fee. Validamos que sean positivos acá; si al repartir
        la fee alguno quedara negativo, Bitcoin Core rechaza la tx.
        """
        if not outputs:
            raise ValueError("send_batched_payments: no outputs to send")

        # Bitcoin Core no permite dos outputs a la misma dirección en sendmany;
        # además necesitamos montos positivos.
        amounts: dict[str, Decimal] = {}
        for out in outputs:
            if out.amount_in_sats <= 0:
                raise ValueError(f"Output amount must be positive: {out}")
            if out.address in amounts:
                raise ValueError(f"Duplicate output address in batch: {out.address}")
            amounts[out.address] = sats_to_btc(out.amount_in_sats)

        # A qué direcciones se les descuenta la fee (todas, si subtract_fees).
        subtractfeefrom = list(amounts.keys()) if subtract_fees else []

        # sendmany(dummy, amounts, minconf, comment, subtractfeefrom,
        #          replaceable, conf_target, estimate_mode, fee_rate)
        # fee_rate va en sat/vByte (Bitcoin Core 0.21+).
        txid = self.rpc.sendmany(
            "",                 # dummy: debe ser "" (wallet por defecto)
            amounts,            # {address: amount_btc}
            1,                  # minconf
            "kross batched payout",  # comment
            subtractfeefrom,    # de qué outputs se resta la fee
            False,              # replaceable (RBF)
            1,                  # conf_target (lo domina fee_rate igualmente)
            "unset",            # estimate_mode
            int(fee_per_vbyte), # fee_rate en sat/vByte
        )
        return txid

    def get_transaction(self, txid: str) -> Transaction:
        """
        Devuelve una Transaction para seguir el estado de un payout batcheado
        (principalmente sus confirmaciones).

        Los outputs se reconstruyen decodificando la tx cruda. Los inputs se
        resuelven best-effort mirando las tx previas (pueden quedar incompletos
        si el nodo no las tiene, p.ej. sin -txindex): en ese caso se omiten.
        """
        tx = self.rpc.gettransaction(txid)
        confirmations = int(tx.get('confirmations', 0))
        decoded = self.rpc.decoderawtransaction(tx['hex'])

        outputs: list[TransactionOutput] = []
        for vout in decoded.get('vout', []):
            address = vout.get('scriptPubKey', {}).get('address')
            if address is None:
                continue
            outputs.append(TransactionOutput(
                address=address,
                amount_in_sats=btc_to_sats(vout['value']),
            ))

        inputs: list[TransactionInput] = []
        for vin in decoded.get('vin', []):
            prev_txid = vin.get('txid')
            prev_n = vin.get('vout')
            if prev_txid is None or prev_n is None:
                continue
            try:
                prev = self.rpc.gettransaction(prev_txid)
                prev_decoded = self.rpc.decoderawtransaction(prev['hex'])
                prev_out = prev_decoded['vout'][prev_n]
                address = prev_out.get('scriptPubKey', {}).get('address')
                if address is None:
                    continue
                inputs.append(TransactionInput(
                    address=address,
                    amount_in_sats=btc_to_sats(prev_out['value']),
                ))
            except Exception:
                # No pudimos resolver este input (tx previa no disponible).
                continue

        return Transaction(
            confirmations=confirmations,
            txid=txid,
            inputs=inputs,
            outputs=outputs,
        )
