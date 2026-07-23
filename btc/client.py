#TODO: Implement the connection to the bitcoin core client using RPC, use the bitcoinrpc library
#TODO: usar blinker para señales; from blinker import Signal
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


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
    def __init__(self):
        # Initialize the client with env configuration variables, use grpc
        pass

    #TODO: Create signal for a transaction being received

    def get_onchain_balance(self) -> int:
        """
        Get the current on-chain balance.
        """
        # Implementation to get the on-chain balance using the Bitcoin Core client
        pass

    def send_batched_payments(self, outputs: list[TransactionOutput], fee_per_vbyte: int, subtract_fees: bool = True, return_address: str | None = None):
        # The returnaddress is used to mark where the "change" of the transaction should go
        # If None is passed defaults to get_newaddress
        # if substract_fees is set to True, each transaction output will get deducted the required fee_per_vbyte
        #     !PREVENT BUG: amout of an output should ALWAYS be positive even after subtracting miner fees
        if return_address is None:
            return_address = self.get_newaddress()
        ...

    def get_fee_rate_per_byte(self, priority: Literal['high', 'medium', 'low'] = 'medium'):
        ...

    def get_newaddress(self) -> str:
        ...

    def get_transaction(self, txid: str):
        # This is menat to be used to keep track of confirmed patched payouts
        ...

