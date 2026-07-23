# Cliente de Lightning (LND) por gRPC.
# Solo usamos lo mínimo para el flujo de swap-out con hold invoices:
# crear una hold invoice, suscribirse a sus cambios de estado, y liberarla
# (settle) o cancelarla si no hay fondos para completar la orden.
#
# Referencia de estilo: https://github.com/RoboSats/robosats/blob/main/api/lightning/lnd.py
# (nosotros no tenemos bonds ni escrow, así que es bastante más compacto).
import hashlib
import os
import secrets
import threading
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import grpc

from . import invoices_pb2, invoices_pb2_grpc
from . import lightning_pb2, lightning_pb2_grpc
from . import router_pb2, router_pb2_grpc


class LNDCLient:
    # Instancia singleton (ver .instance()). Guardamos una sola conexión gRPC
    # y la reutilizamos en toda la app.
    _instance: "LNDCLient | None" = None

    def __init__(self) -> None:
        # Config por variables de entorno.
        host = os.getenv("LND_GRPC_HOST", "localhost:10009")
        cert_path = os.getenv("LND_TLS_CERT_PATH", os.path.expanduser("~/.lnd/tls.cert"))
        macaroon_path = os.getenv(
            "LND_MACAROON_PATH",
            os.path.expanduser("~/.lnd/data/chain/bitcoin/mainnet/admin.macaroon"),
        )

        # LND pide DOS credenciales:
        #  1) el cert TLS -> para cifrar el canal (como el candado de HTTPS).
        #  2) el macaroon -> token de autorización que viaja en la metadata de
        #     cada llamada gRPC (va como hex).
        with open(cert_path, "rb") as f:
            cert = f.read()
        with open(macaroon_path, "rb") as f:
            macaroon = f.read()

        def metadata_callback(context, callback):
            # gRPC llama a esto en cada request para inyectar el macaroon.
            callback([("macaroon", macaroon.hex())], None)

        ssl_creds = grpc.ssl_channel_credentials(cert)
        auth_creds = grpc.metadata_call_credentials(metadata_callback)
        combined_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)
        self.channel = grpc.secure_channel(host, combined_creds)

        # Cada "servicio" del proto es un stub distinto:
        #  - lightning: operaciones generales (balance, etc.)
        #  - invoices: hold invoices (crear / settle / cancel / suscribir)
        #  - router:   pagar invoices (SendPaymentV2)
        self.lightning = lightning_pb2_grpc.LightningStub(self.channel)
        self.invoices = invoices_pb2_grpc.InvoicesStub(self.channel)
        self.router = router_pb2_grpc.RouterStub(self.channel)

    @staticmethod
    def instance() -> "LNDCLient":
        """
        Devuelve la instancia singleton del cliente (una sola conexión gRPC
        reutilizada en toda la app).
        """
        if LNDCLient._instance is None:
            LNDCLient._instance = LNDCLient()
        return LNDCLient._instance

    @staticmethod
    def generate_secret() -> bytes:
        """
        Genera un secreto random de 32 bytes (el preimage de la hold invoice).
        Quien conozca este secreto puede liberar (settle) la invoice, por eso
        lo guardamos en la DB.
        """
        return secrets.token_bytes(32)

    # El secret es el valor de 32 bytes con el que se arma la hold invoice.
    def create_hold_invoice(self, amount: int, secret: bytes, memo: str) -> str:
        """
        Crea una hold invoice por 'amount' sats. Devuelve el payment_request.

        Una hold invoice queda "congelada": cuando el usuario la paga, la plata
        queda RETENIDA (estado ACCEPTED) hasta que nosotros hagamos settle. El
        payment_hash de la invoice es sha256(secret); revelar el secret (settle)
        es lo que libera los fondos.
        """
        payment_hash = hashlib.sha256(secret).digest()
        request = invoices_pb2.AddHoldInvoiceRequest(
            memo=memo,
            hash=payment_hash,
            value=amount,
        )
        response = self.invoices.AddHoldInvoice(request)
        return response.payment_request

    def settle_hold_invoice(self, secret: bytes) -> None:
        """
        Libera (settle) la hold invoice revelando su preimage (secret).
        A partir de acá los fondos entrantes quedan efectivamente nuestros.
        """
        request = invoices_pb2.SettleInvoiceMsg(preimage=secret)
        self.invoices.SettleInvoice(request)

    def cancel_hold_invoice(self, secret: bytes) -> None:
        """
        Cancela la hold invoice (devuelve los fondos al pagador). Se usa cuando
        no hay fondos on-chain para completar el swap-out.
        """
        payment_hash = hashlib.sha256(secret).digest()
        request = invoices_pb2.CancelInvoiceMsg(payment_hash=payment_hash)
        self.invoices.CancelInvoice(request)

    def subscribe_to_invoice(self, secret: bytes, callback: Callable[[Any], None]) -> None:
        """
        Se suscribe a los cambios de estado de una hold invoice y llama a
        'callback' en cada update. La suscripción es un stream de gRPC que corre
        en un thread aparte para no frenar el resto de la app.

        DECISION DE DISEÑO (firma): originalmente esta función recibía el
        payment_request (string). Lo cambiamos por 'secret' porque LND se
        suscribe por payment_hash (= sha256(secret)), y nosotros YA generamos el
        secret al crear la invoice. Si recibiéramos el payment_request habría que
        pedirle a LND que lo decodifique (DecodePayReq) solo para recuperar el
        hash: una llamada de red extra e inútil, porque el hash lo podemos
        calcular localmente. Menos red, menos latencia, menos puntos de falla.

        El callback recibe un objeto con .status (string: 'OPEN' | 'ACCEPTED' |
        'SETTLED' | 'CANCELED') y .raw (la invoice cruda de LND). Normalizamos el
        estado a string para que el resto del código no dependa del enum de LND.
        El pago on-chain al usuario se dispara desde el callback una vez que la
        invoice queda liquidada.
        """
        payment_hash = hashlib.sha256(secret).digest()
        request = invoices_pb2.SubscribeSingleInvoiceRequest(r_hash=payment_hash)

        def run():
            for invoice in self.invoices.SubscribeSingleInvoice(request):
                status = lightning_pb2.Invoice.InvoiceState.Name(invoice.state)
                callback(SimpleNamespace(status=status, raw=invoice))

        threading.Thread(target=run, daemon=True).start()

    def pay_invoice(
        self,
        payment_request: str,
        amount: int,
        max_fee: int,
        callback: Callable[[Any], None],
    ) -> None:
        """
        Paga una invoice de Lightning. El stream de SendPaymentV2 emite updates
        del estado del pago; se los pasamos al callback (.status es string:
        'IN_FLIGHT' | 'SUCCEEDED' | 'FAILED', y .raw es el payment crudo).
        Corre en un thread aparte por la misma razón que subscribe_to_invoice.

        Nota: el monto normalmente ya viene dentro del payment_request; 'amount'
        queda disponible por si en el futuro pagamos invoices de monto abierto.
        """
        request = router_pb2.SendPaymentRequest(
            payment_request=payment_request,
            fee_limit_sat=max_fee,
            timeout_seconds=60,
        )

        def run():
            for payment in self.router.SendPaymentV2(request):
                status = lightning_pb2.Payment.PaymentStatus.Name(payment.status)
                callback(SimpleNamespace(status=status, raw=payment))

        threading.Thread(target=run, daemon=True).start()

    def get_ln_balance(self) -> int:
        """
        Balance local de los canales de Lightning, en sats (lo que podemos
        enviar). Es el líquido disponible del lado LN.
        """
        response = self.lightning.ChannelBalance(lightning_pb2.ChannelBalanceRequest())
        return response.local_balance.sat
