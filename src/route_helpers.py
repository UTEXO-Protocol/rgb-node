"""Helpers for wallet HTTP routes (rgb-lib send/receive, invoice expiry). Kept out of routes.py for clarity."""

from __future__ import annotations

import time
from typing import List, Optional

from rgb_lib import Assignment, Wallet

from src.rgb_model import OperationResult, Recipient, SendResult


def invoice_expiration_timestamp(duration_seconds: int) -> Optional[int]:
    """rgb-lib 0.3.0b17+ uses absolute expiry unix time, not duration. 0 = no expiry."""
    if duration_seconds <= 0:
        return None
    return int(time.time()) + duration_seconds


def send_begin_psbt(
    wallet: Wallet,
    online,
    recipient_map,
    donation: bool,
    fee_rate: int,
    min_confirmations: int,
    expiration_timestamp: Optional[int],
    dry_run: bool,
) -> str:
    r = wallet.send_begin(
        online,
        recipient_map,
        donation,
        fee_rate,
        min_confirmations,
        expiration_timestamp,
        dry_run,
    )
    return r.psbt


def send_end_to_response(r) -> SendResult:
    """Map rgb_lib OperationResult from send_end to API SendResult."""
    return SendResult(txid=r.txid, batch_transfer_idx=r.batch_transfer_idx, entropy=r.entropy)


def inflate_end_to_response(r) -> OperationResult:
    """Map rgb_lib OperationResult from inflate_end to API OperationResult."""
    return OperationResult(txid=r.txid, batch_transfer_idx=r.batch_transfer_idx, entropy=r.entropy)


def normalize_recipient_map(recipient_map: dict[str, List[Recipient]]) -> dict:
    """Convert int assignments to Assignment.FUNGIBLE for wallet.send_begin."""
    out: dict = {}
    for asset_id, recs in recipient_map.items():
        out[asset_id] = []
        for r in recs:
            asn = r.assignment
            if isinstance(asn, int):
                asn = Assignment.FUNGIBLE(asn)
            out[asset_id].append(
                Recipient(
                    recipient_id=r.recipient_id,
                    assignment=asn,
                    witness_data=r.witness_data,
                    transport_endpoints=r.transport_endpoints,
                )
            )
    return out
