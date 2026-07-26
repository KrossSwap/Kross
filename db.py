import os
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Integer,
    String,
    Enum as SQLEnum,
    ForeignKey,
    LargeBinary,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
    scoped_session,
)

# 1. Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///kross.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 2. Base Model
class Base(DeclarativeBase):
    pass


# 3. Enums
class SwapInStatus(Enum):
    WAITING_CONFIRMATIONS = "waiting_confirmations"
    WAITING_INVOICE = "waiting_invoice"
    BATCHED = "batched"
    SUCCESS = "success"
    EXPIRED = "expired"
    ERROR = "error"


class SwapInLightningPaymentRequestStatus(Enum):
    PENDING = "pending"
    ON_FLIGHT = "on_flight"
    PAID = "paid"
    FAILED = "failed"
    ERROR = "error"


class SwapOutStatus(Enum):
    WAITING_PAYMENT = "waiting_payment"
    BATCHED = "batched"
    ABOUT_TO_BE_PAID = "about_to_be_paid"
    SUCCESS = "success"
    EXPIRED = "expired"
    ERROR = "error"


class SwapOutPaymentStatus(Enum):
    BATCHED = "batched"
    PAID = "paid"
    ERROR = "error"


# 4. Models (Joined Table Inheritance)
class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    token: Mapped[str] = mapped_column(String(256))

    __mapper_args__ = {
        "polymorphic_identity": "order",
        "polymorphic_on": type,
    }


class SwapIn(Order):
    __tablename__ = "swap_ins"
    id: Mapped[int] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    status: Mapped[SwapInStatus] = mapped_column(SQLEnum(SwapInStatus))
    address: Mapped[str] = mapped_column(String)
    amount_in_sats: Mapped[int] = mapped_column(Integer)
    amount_out_sats: Mapped[int] = mapped_column(Integer, default=0)
    lightning_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    payment_requests: Mapped[List["SwapInLightningPaymentRequest"]] = relationship(
        back_populates="swap_in"
    )

    __mapper_args__ = {
        "polymorphic_identity": "swap_in",
    }


class SwapOut(Order):
    __tablename__ = "swap_outs"
    id: Mapped[int] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    status: Mapped[SwapOutStatus] = mapped_column(
        SQLEnum(SwapOutStatus), default=SwapOutStatus.WAITING_PAYMENT
    )
    ln_invoice: Mapped[str] = mapped_column(String)
    ln_hold_invoice_secret: Mapped[bytes] = mapped_column(LargeBinary)
    address: Mapped[str] = mapped_column(String)
    amount_in_sats: Mapped[int] = mapped_column(Integer)
    amount_out_sats: Mapped[int] = mapped_column(Integer, default=0)
    txid: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "swap_out",
    }


# 5. Related Models
class SwapInLightningPaymentRequest(Base):
    __tablename__ = "swap_in_lightning_payment_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    swap_in_id: Mapped[int] = mapped_column(ForeignKey("swap_ins.id"))
    status: Mapped[SwapInLightningPaymentRequestStatus] = mapped_column(
        SQLEnum(SwapInLightningPaymentRequestStatus)
    )
    payment_request: Mapped[str] = mapped_column(String)
    max_routing_fee_sats: Mapped[int] = mapped_column(Integer)

    swap_in: Mapped["SwapIn"] = relationship(back_populates="payment_requests")


class OnChainPaymentBatch(Base):
    __tablename__ = "on_chain_payment_batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    txid: Mapped[str] = mapped_column(String)
    return_address: Mapped[str] = mapped_column(String)

    payments: Mapped[List["SwapOutPayment"]] = relationship(back_populates="batch")


class SwapOutPayment(Base):
    __tablename__ = "swap_out_payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("on_chain_payment_batches.id"), nullable=True
    )
    status: Mapped[SwapOutPaymentStatus] = mapped_column(SQLEnum(SwapOutPaymentStatus))
    address: Mapped[str] = mapped_column(String)
    amount: Mapped[int] = mapped_column(Integer)
    fees_paid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    txid: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    batch: Mapped[Optional["OnChainPaymentBatch"]] = relationship(back_populates="payments")


# 6. Database Access Helpers
async def get_swap_outs_by_status(status: SwapOutStatus) -> list[SwapOut]:
    with SessionLocal() as session:
        return session.query(SwapOut).filter(SwapOut.status == status).all()


async def mark_swap_outs_about_to_be_paid(swap_out_ids: list[int]) -> None:
    if not swap_out_ids:
        return
    with SessionLocal() as session:
        session.query(SwapOut).filter(SwapOut.id.in_(swap_out_ids)).update(
            {SwapOut.status: SwapOutStatus.ABOUT_TO_BE_PAID}, synchronize_session=False
        )
        session.commit()


async def mark_swap_outs_paid(swap_out_ids: list[int], txid: str) -> None:
    if not swap_out_ids:
        return
    with SessionLocal() as session:
        session.query(SwapOut).filter(SwapOut.id.in_(swap_out_ids)).update(
            {SwapOut.status: SwapOutStatus.SUCCESS, SwapOut.txid: txid}, synchronize_session=False
        )
        session.commit()
