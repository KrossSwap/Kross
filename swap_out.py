import os

from ln.client import LNDCLient
from db import SwapOut, SwapOutStatus
from balance_calculator import get_onchain_balance

MIN_BATCH_SIZE = int(os.getenv('MIN_BATCH_SIZE', 3))
MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', 100))

#Todo: .env
SWAP_OUT_MIN_VOLUME_SATS = 10000
SWAP_OUT_MAX_VOLUME_SATS = 500000

def swap_out_calculate_amount_out(amount_in_sats: int) -> int:
    #TODO: Use a dynamic rate based on available onchain balance and lightning balance 
    # Placeholder for the actual calculation logic
    # This function should calculate the amount out based on the current rate and fees
    return int(amount_in_sats * 0.995)  # Example: deducting a 0.5% fee

def swap_out(amount: int, address: str):
    if amount < SWAP_OUT_MIN_VOLUME_SATS or amount > SWAP_OUT_MAX_VOLUME_SATS:
        raise Exception('Amount not in a valid range')
    
    # Create a hold invoice for the given amount and address
    lnd_client= LNDCLient.instance()
    secret = lnd_client.generate_secret()
    payment_request = lnd_client.create_hold_invoice(amount, secret, f"Swap {amount} sats out to {address}")
    # First we create an order
    swap_out_order = SwapOut(
        ln_invoice=payment_request,
        ln_hold_invoice_secret=secret,
        address=address,
        amount_in_sats=amount,
        amount_out_sats=swap_out_calculate_amount_out(amount),
    )

    # Subscribe to updates for the hold invoice
    def invoice_callback(invoice):
        if invoice.status == 'ACCEPTED':
            # Invoice is being held (this is a hold invoice)
            # We validate order status is WAITING_PAYMENT
            if swap_out_order.status != SwapOutStatus.WAITING_PAYMENT:
                raise Exception(f"Swap out order status is not waiting_payment: order id: {swap_out_order.id}")
            
            lnd_client.settle_hold_invoice(swap_out_order.secret)

        if invoice.status == 'SETTLED':
            if swap_out_order.status != SwapOutStatus.WAITING_PAYMENT:
                raise Exception(f"Swap out order status is not waiting_payment: order id: {swap_out_order.id}")
        
            # Now we can batch the payment to the user
            swap_out_order.status = SwapOutStatus.BATCHED
            swap_out_order.save()
            return
        
        elif invoice.status == 'CANCELED':
            # Delete the order from databse for cleanup
            ...
        
        else:
            # Something waird is happening, log an error
            ...


    # Nos suscribimos por 'secret': el cliente calcula el payment_hash localmente
    # (sha256(secret)), evitando una llamada de red para decodificar el invoice.
    lnd_client.subscribe_to_invoice(secret, invoice_callback)
    return payment_request