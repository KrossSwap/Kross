#TODO: pip install sqlalchemy psycopg[binary]; Reimplement this using SQLAlchemy, giving the chance of using sqlite3 (default) and postgres (ideally in production)
from dataclasses import dataclass
from enum import Enum
from datetime import date

@dataclass
class Order:
    id: int
    # With the order token, the user can claim ownership of the order, useful if an error occurs and manual resolution is required.
    # The token has 256 bits of entropy
    token: str
    created_at: date


class SwapInStatus(Enum):
    WAITING_CONFIRMATIONS = "waiting_confirmations"
    # Once on-chain transaction is confirmed, we can prompt the user to send us a LN invoice
    WAITING_INVOICE = "waiting_invoice"
    # User has sent us a LN invoice, it will be procesed by a background task
    BATCHED = "batched"
    SUCCESS = "success"
    EXPIRED = "expired"
    ERROR = "error"

@dataclass
class SwapIn(Order):
    # Inherits id from order
    # From on-chain to lightning
    status: SwapInStatus
    # On chain address the user should send the funds to
    address: str
    amount_in_sats: int
    # This field is dynamically calculated based on the current rate when the on-chain transaction gets the required number of confirmations.
    amount_out_sats: int = 0
    # The user can accelerate the process by providing a lightning address, if so, there will be no need for prompting the user to send us a LN invoice
    lightning_address: str | None = None


class SwapInLightningPaymentRequestStatus(Enum):
    PENDING = "pending"
    ON_FLIGHT = "on_flight"
    PAID = "paid"
    FAILED = "failed"
    ERROR = "error"

@dataclass
class SwapInLightningPaymentRequest:
    id: int
    swap_in_id: int
    status: SwapInLightningPaymentRequestStatus
    payment_request: str
    max_routing_fee_sats: int


# Kross is optimized if the majority of orders are swap-outs
class SwapOutStatus(Enum):
    WAITING_PAYMENT = "waiting_payment"
    # User has sent us a LN payment, it will be processed by a background task
    BATCHED = "batched"
    ABOUT_TO_BE_PAID = "about_to_be_paid"
    SUCCESS = "success"
    EXPIRED = "expired"
    ERROR = "error"

@dataclass
class SwapOut(Order):
    # Inherits id from order
    # From lightning to on-chain
    status: SwapOutStatus = SwapOutStatus.WAITING_PAYMENT
    # Lightning invoice the user should pay
    ln_invoice: str
    # 32 byte secret used to settle the hold invoice
    ln_hold_invoice_secret: bytes
    # The bitcoin address the user should receive the funds to
    address: str
    amount_in_sats: int
    # This field is dynamically calculated based on the current rate when the LN payment gets confirmed.
    amount_out_sats: int = 0
    # Txid of the batched on-chain transaction that paid this order out
    txid: str | None = None

class SwapOutPaymentStatus(Enum):
    BATCHED = 'batched'
    PAID = 'paid'
    ERROR = 'error'

@dataclass
class SwapOutPayment:
    id: int
    status: SwapOutPaymentStatus
    address: str
    amount: int
    fees_paid: int | None
    txid: str | None

@dataclass
class OnChainPaymentBatch:
    id: int
    txid: str
    return_address: str
    # This should be a "virtual field", result of joining with a relation table between onchainpaymentbatch and swapoutpayment
    payments: list[SwapOutPayment]

# Implement accessors and setters using async psycopg

async def get_swap_outs_by_status(status: SwapOutStatus) -> list[SwapOut]:
    # TODO: implementar con SQLAlchemy (SELECT * FROM swap_out WHERE status = %s)
    raise NotImplementedError


async def mark_swap_outs_paid(swap_out_ids: list[int], txid: str) -> None:
    # TODO: implementar con SQLAlchemy
    # UPDATE swap_out SET status = 'success', txid = %s WHERE id = ANY(%s)
    raise NotImplementedError


async def mark_swap_outs_about_to_be_paid(swap_out_ids: list[int]) -> None:
    raise NotImplementedError