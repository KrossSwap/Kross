import sys
import os
import secrets
from sqlalchemy import select

# Fix path to import kross modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db import Base, engine, db_session, SwapOut, SwapOutStatus

def test_db_model():
    print("== Testing DB Model and Table Creation ==")
    
    # 1. Ensure tables are created
    Base.metadata.create_all(bind=engine)
    print("[OK] Tables created.")
    
    # 2. Test insertion
    swap_out = SwapOut(
        token=secrets.token_hex(32),
        ln_invoice="lnbc_test_invoice",
        ln_hold_invoice_secret=secrets.token_bytes(32),
        address="bcrt1qtestaddress",
        amount_in_sats=1000,
        amount_out_sats=995,
        status=SwapOutStatus.WAITING_PAYMENT
    )
    
    db_session.add(swap_out)
    db_session.commit()
    print(f"[OK] SwapOut inserted with id={swap_out.id}.")
    
    # 3. Test query
    retrieved = db_session.query(SwapOut).filter(SwapOut.id == swap_out.id).first()
    assert retrieved is not None
    assert retrieved.amount_in_sats == 1000
    print(f"[OK] SwapOut retrieved: id={retrieved.id}, amount={retrieved.amount_in_sats}")
    
    db_session.remove()
    print("== DB Test: OK ==")

if __name__ == "__main__":
    test_db_model()
