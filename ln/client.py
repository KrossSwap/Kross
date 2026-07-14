#TODO maxi: implementar el client de ln, para poder crear hold invoices y suscribirse a ellas.

from collections.abc import Callable
from typing import Any


class Client:
    # Secret is a 32-byte value used for creating hold invoices
    def create_hold_invoice(self, amount: int, secret: bytes, memo: str) -> str:
        """
        Create a hold invoice for the given amount and memo.
        Returns the payment request string.
        """
        # Implementation to create a hold invoice using the Lightning Network client
        pass

    def subscribe_to_invoice(self, payment_request: str, callback: Callable[[Any], None]) -> None:
        """
        Subscribe to updates for the given payment request.
        Calls the callback with the status of the invoice when it changes.
        """
        # Implementation to subscribe to invoice updates using the Lightning Network client
        pass

    @staticmethod
    def instance() -> "Client":
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