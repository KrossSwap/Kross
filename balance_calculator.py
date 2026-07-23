# It gets the balance in sats for both on-chain and lightning network
# This file is necessarby because we need to subtract batched transactions (not yet paid) from the balance in both lightning and on-chain.
import os

LN_ONCHAIN_EQUILIBRIUM_POINT = float(os.getenv("LN_ONCHAIN_EQUILIBRIUM_POINT", 1.00))
SPREAD = os.getenv("SPREAD", 0.01)  # 1% spread

def get_ln_balance() -> int:
    # Placeholder for actual implementation
    # This should return lightning balance subtracting failed payments.
    return 1000000  # Example: returning a dummy balance of 1,000,000 sats

def get_onchain_balance() -> int:
    # Placeholder for actual implementation
    # Should return on-chain balance subtracting the batched payments. 
    return 1000000  # Example: returning a dummy balance of 1,000,000 sats


def get_ln_to_onchain_rate():
    ...