#TODO maxi: implementar el client de ln, para poder crear hold invoices y suscribirse a ellas.
#TODO: usar blinker para señales; from blinker import Signal
# Usar grpc para comunicacion
from collections.abc import Callable
from typing import Any


class LNDCLient:
    # Secret is a 32-byte value used for creating hold invoices
    def create_hold_invoice(self, amount: int, secret: bytes, memo: str) -> str:
        """
        Create a hold invoice for the given amount and memo.
        Returns the payment request string.
        """
        # Implementation to create a hold invoice using the Lightning Network client
        pass

    def settle_hold_invoice(self, secret: bytes) -> None:
        """
        Settle the hold invoice associated with the given secret.
        """
        # Implementation to settle the hold invoice using the Lightning Network client
        pass

    def subscribe_to_invoice(self, payment_request: str, callback: Callable[[Any], None]) -> None:
        """
        Subscribe to updates for the given payment request.
        Calls the callback with the status of the invoice when it changes.
        """
        # Implementation to subscribe to invoice updates using the Lightning Network client
        # Onchain payment to user is originated after the invoice is stettled, handled by the callback
        pass

    def pay_invoice(self, payment_request: str, amount: int, max_fee: int, callback: Callable[[Any], None]) -> None:
        """
        Pay the given Lightning Network invoice.
        """
        # Implementation to pay a Lightning Network invoice using the client
        # Callback receives updates of the payment status, including success or failure 
        pass

    @staticmethod
    def instance() -> "LNDCLient":
        """
        Returns a singleton instance of the Client.
        """
        # Implementation to return a singleton instance of the Client
        pass

    @staticmethod
    def generate_secret() -> bytes:
        """
        Generate a random 32-byte secret for creating hold invoices.
        """
        # Implementation to generate a random 32-byte secret
        pass
    
    def get_ln_balance(self) -> int:
        """
        Get the current Lightning Network balance.
        """
        # Implementation to get the current Lightning Network balance using the client
        pass