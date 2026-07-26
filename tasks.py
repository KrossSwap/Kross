import os
import asyncio

from btc.client import BitcoinCoreClient, TransactionOutput
from db import SwapOutStatus, get_swap_outs_by_status, mark_swap_outs_paid, mark_swap_outs_about_to_be_paid

FEE_PRIORITY = os.getenv('BATCH_FEE_PRIORITY', 'medium')

lock = asyncio.Lock()

#TODO: No usar asyncio, usar hilos, mejor practica
# This should be a job that executes periodically (~once per 2 hours)
async def send_batched_payouts():
    #si se ejecuta 2 veces al mismo tiempo en paralelo?
    async with lock:
        # 1. Traemos todas las swap-out orders en estado BATCHED
        batched_orders = await get_swap_outs_by_status(SwapOutStatus.BATCHED)

        if not batched_orders:
            return

        order_ids = [order.id for order in batched_orders]

        # 2. Armamos los outputs: una entrada por orden (dirección + monto a pagar)
        outputs = [
            TransactionOutput(address=order.address, amount_in_sats=order.amount_out_sats)
            for order in batched_orders
        ]

        await mark_swap_outs_about_to_be_paid(order_ids)
        # 3. Enviamos una única tx on-chain con todos los pagos batcheados
        btc_client = BitcoinCoreClient.instance()
        fee_per_vbyte = btc_client.get_fee_rate_per_byte(FEE_PRIORITY)
        txid = btc_client.send_batched_payments(outputs, fee_per_vbyte)

        # 4. Guardamos el txid y marcamos las órdenes como pagadas
        await mark_swap_outs_paid(order_ids, txid)
