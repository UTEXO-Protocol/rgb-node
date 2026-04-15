from fastapi import Body, Header, HTTPException, Depends
from typing import Tuple
from rgb_lib import Wallet
from src.rgb_model import RegisterWalletRequest
from src.wallet_utils import load_wallet_instance, create_wallet_instance


def get_wallet(
    xpub_van: str = Header(...),
    xpub_col: str = Header(...),
    master_fingerprint: str = Header(...),
) -> Tuple[Wallet, object, str, str]:
    wallet, online = load_wallet_instance(xpub_van, xpub_col, master_fingerprint)
    if not wallet or not online:
        raise HTTPException(status_code=400, detail="Wallet not initialized")
    return wallet, online, xpub_van, xpub_col


def create_wallet(
    xpub_van: str = Header(...),
    xpub_col: str = Header(...),
    master_fingerprint: str = Header(...),
    body: RegisterWalletRequest = Body(default_factory=RegisterWalletRequest),
) -> Tuple[Wallet, object, str, str]:
    wallet, online = create_wallet_instance(
        xpub_van,
        xpub_col,
        master_fingerprint,
        reuse_addresses=body.reuse_addresses,
    )
    if not wallet or not online:
        raise HTTPException(status_code=400, detail="Wallet not initialized")
    return wallet, online, xpub_van, xpub_col
