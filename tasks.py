import os

from btc.client import BitcoinCoreClient, TransactionOutput
from db import SwapOutStatus, get_swap_outs_by_status, mark_swap_outs_paid

FEE_PRIORITY = os.getenv('BATCH_FEE_PRIORITY', 'medium')


# This should be a job that executes periodically (~once per 2 hours)
async def send_batched_payouts():
    # 1. Traemos todas las swap-out orders en estado BATCHED
    batched_orders = await get_swap_outs_by_status(SwapOutStatus.BATCHED)

    if not batched_orders:
        return

    # 2. Armamos los outputs: una entrada por orden (dirección + monto a pagar)
    outputs = [
        TransactionOutput(address=order.address, amount_in_sats=order.amount_out_sats)
        for order in batched_orders
    ]

    # 3. Enviamos una única tx on-chain con todos los pagos batcheados
    btc_client = BitcoinCoreClient.instance()
    fee_per_vbyte = btc_client.get_fee_rate_per_byte(FEE_PRIORITY)
    txid = btc_client.send_batched_payments(outputs, fee_per_vbyte)

    # 4. Guardamos el txid y marcamos las órdenes como pagadas
    order_ids = [order.id for order in batched_orders]
    await mark_swap_outs_paid(order_ids, txid)
