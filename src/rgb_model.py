# pylint: disable=too-few-public-methods
"""Module containing models related to RGB."""
from __future__ import annotations

from datetime import datetime
import enum
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel
from pydantic import model_validator

from src.constant import FEE_RATE_FOR_CREATE_UTXOS
from src.constant import NO_OF_UTXO
from src.constant import RGB_INVOICE_DURATION_SECONDS
from src.constant import UTXO_SIZE_SAT
from rgb_lib import (
    AssetSchema,
    BitcoinNetwork,
    Wallet,
    TransferStatus,
    TransportType,
    TransferKind,
    TransactionType,
)
# -------------------- Helper models -----------------------

class CommonException(Exception):
    pass


class StatusModel(BaseModel):
    """Response status model."""

    status: bool


class TransactionTxModel(BaseModel):
    """Mode for get single transaction method of asset detail page service"""
    tx_id: str | None = None
    idx: int | None = None

    # 'mode='before'' ensures the validator runs before others
    @model_validator(mode='before')
    def check_at_least_one(cls, values):  # pylint: disable=no-self-argument
        """
        Ensures that at least one of tx_id or idx is provided.
        """
        tx_id, idx = values.get('tx_id'), values.get('idx')
        if tx_id is None and idx is None:
            raise CommonException("Either 'tx_id' or 'idx' must be provided")

        if tx_id is not None and idx is not None:
            raise CommonException(
                "Both 'tx_id' and 'idx' cannot be accepted at the same time.",
            )

        return values
class SendBtcBeginRequestModel(BaseModel):
    address: str
    amount: int
    fee_rate: int = 3
    skip_sync:bool = False
class SendBtcEndRequestModel(BaseModel):
    signed_psbt: str
    skip_sync: bool = False
class GetFeeEstimateRequestModel(BaseModel):
    blocks: int


class RegisterWalletRequest(BaseModel):
    """Optional JSON body for POST /wallet/register."""

    reuse_addresses: Optional[bool] = Field(
        default=None,
        description=(
            "If true or false, saved to wallet.json and used for rgb-lib WalletData.reuse_addresses. "
            "If omitted or null, use existing wallet.json or REUSE_ADDRESSES env (default false when unset)."
        ),
    )


class RegisterModel(BaseModel):
    address: str
    btc_balance: BtcBalance
    # Effective rgb-lib WalletData.reuse_addresses (body / wallet.json / REUSE_ADDRESSES env).
    reuse_addresses: bool


class GenerateKeysResponse(BaseModel):
    """Serialized output of rgb_lib.generate_keys (uniffi Keys is not JSON-serializable as-is)."""

    mnemonic: str
    xpub: str
    master_fingerprint: str
    account_xpub_vanilla: str
    account_xpub_colored: str


class WitnessData(BaseModel):
    amount_sat: int
    blinding: Optional[int] = None

class Recipient(BaseModel):
    """Recipient model for asset transfer."""
    recipient_id: str
    witness_data: Any = None
    assignment: Any
    transport_endpoints: List[str]
    
class SendAssetBeginRequestModel(BaseModel):
    invoice: str | None = None
    asset_id: str| None = None
    recipient_id: str= None
    amount: int= None
    witness_data: Optional[WitnessData] = None
    fee_rate: Optional[int] = None
    min_confirmations: Optional[int] = None
    donation: bool = False
    # Absolute unix expiry for the transfer batch; None = no expiry (rgb-lib send_begin).
    expiration_timestamp: Optional[int] = None
    dry_run: bool = False

class SendAssetBeginModel(BaseModel):
    recipient_map: dict[str, List[Recipient]]
    donation: bool = False
    fee_rate: int = 5
    min_confirmations: int = 1

class OperationResult(BaseModel):
    txid: str
    batch_transfer_idx: int
    entropy: int

class SendAssetEndRequestModel(BaseModel):
    signed_psbt: str


class SendBatchBeginRequestModel(BaseModel):
    """Params for send batch begin – passed directly to wallet.send_begin."""
    recipient_map: dict[str, List[Recipient]]
    donation: bool = False
    fee_rate: int = 5
    min_confirmations: int = 1
    expiration_timestamp: Optional[int] = None
    dry_run: bool = False


class SendBatchWithSignRequestModel(SendBatchBeginRequestModel):
    """Send batch in one call: begin → sign → end (like createutxos)."""
    mnemonic: str


class WatchOnly(BaseModel):
    xpub: str


class CreateUtxosBegin(BaseModel):
    mnemonic: str | None = None
    up_to: bool = False
    num: int = 5
    size: int = 1000
    fee_rate: int = 5


class CreateUtxosWithSign(BaseModel):
    """Create UTXOs in one call: begin (load_wallet) → sign (offline_wallet + mnemonic) → end."""
    mnemonic: str
    up_to: bool = False
    num: int = 5
    size: int = 1000
    fee_rate: int = 5


class CreateUtxosEnd(BaseModel):
    signed_psbt: str


class AssetBalanceRequest(BaseModel):
    asset_id: str


class SignPSBT(BaseModel):
    mnemonic: str
    psbt: str
    xpub_van: str
    xpub_col: str
    master_fingerprint: str


class Media(BaseModel):
    """Model for list asset"""
    file_path: str
    digest: str
    hex: str | None = None
    mime: str


class Balance(BaseModel):
    """Model for list asset"""
    settled: int
    future: int
    spendable: int


class Token(BaseModel):
    """Model for list asset"""
    index: int
    ticker: str | None = None
    name: str | None = None
    details: str | None = None
    embedded_media: bool
    media: Media
    attachments: dict[str, Media]
    reserves: bool

class Outpoint(BaseModel):
    txid: str
    vout: int
class Backup(BaseModel):
    password: str

class RgbAllocation(BaseModel):
    asset_id: Optional[str]
    amount: int
    settled: bool

class Utxo(BaseModel):
    outpoint: Outpoint
    btc_amount: int
    colorable: bool
    exists: bool

class Unspent(BaseModel):
    utxo: Utxo
    rgb_allocations: List[RgbAllocation]

class Balance(BaseModel):
    settled: int
    future: int
    spendable: int

class ReceiveData(BaseModel):
    invoice: str
    recipient_id: str
    expiration_timestamp: Optional[int]
    batch_transfer_idx: int

class SendResult(BaseModel):
    txid: str
    batch_transfer_idx: int
    entropy: int

class BtcBalance(BaseModel):
    vanilla: Balance
    colored: Balance

class AssetIface(enum.IntEnum):
    RGB20 = 0
    
    RGB21 = 1
    
    RGB25 = 2

class AssetNia(BaseModel):
    asset_id: str
    # asset_iface: AssetIface
    ticker: str
    name: str
    details: Optional[str]
    precision: int
    issued_supply: int
    timestamp: int
    added_at: int
    balance: Balance
    media: Optional[Media]

class AssetIfa(BaseModel):
    asset_id: str
    ticker: str
    name: str
    details: Optional[str]
    precision: int
    initial_supply: int
    max_supply: int
    known_circulating_supply: int
    timestamp: int
    added_at: int
    balance: Balance
    media: Optional[Media]
    reject_list_url: Optional[str]

class InflateAssetIfaRequestModel(BaseModel):
    asset_id: str
    inflation_amounts: list[int]
    fee_rate: int = 5
    min_confirmations: int = 1
    dry_run: bool = False
class InflateEndRequestModel(BaseModel):
    signed_psbt: str

class AssetModel(BaseModel):
    """Model for asset """
    asset_id: str
    # asset_iface: str
    ticker: str | None = None
    name: str
    details: str | None
    precision: int
    issued_supply: int
    timestamp: int
    added_at: int
    balance: AssetBalanceResponseModel
    media: Media | None = None
    token: Token | None = None


class TransportEndpoint(BaseModel):
    """Model representing transport endpoints."""

    endpoint: str
    transport_type: str
    used: bool

# -------------------- Request models -----------------------


class AssetIdModel(BaseModel):
    """Request model for asset balance."""

    asset_id: str | None = None


class CreateUtxosRequestModel(BaseModel):
    """Request model for creating UTXOs."""

    up_to: bool | None = False
    num: int = NO_OF_UTXO
    size: int = UTXO_SIZE_SAT
    fee_rate: int = FEE_RATE_FOR_CREATE_UTXOS
    skip_sync: bool = False


class DecodeRgbInvoiceRequestModel(BaseModel):
    """Request model for decoding RGB invoices."""

    invoice: str


class IssueAssetNiaRequestModel(BaseModel):
    """Request model for issuing assets nia."""
    amounts: list[int]
    ticker: str
    name: str
    precision: int = 0

class IssueAssetIfaRequestModel(IssueAssetNiaRequestModel):
    """Request model for issuing assets ifa."""
    inflation_amounts: list[int]
    replace_rights_num: int = 0
    reject_list_url: Optional[str] = None

class IssueAssetCfaRequestModelWithDigest(IssueAssetNiaRequestModel):
    """Request model for issuing assets."""
    file_digest: str


class IssueAssetCfaRequestModel(IssueAssetNiaRequestModel):
    """Request model for issuing assets."""
    file_path: str


class IssueAssetUdaRequestModel(IssueAssetCfaRequestModel):
    """Request model for issuing assets."""
    attachments_file_paths: list[list[str]]


class RefreshRequestModel(BaseModel):
    """Request model for refresh wallet"""
    skip_sync: bool = False


class RgbInvoiceRequestModel(BaseModel):
    """Request model for RGB invoices."""

    min_confirmations: int = 1
    asset_id: str | None = None
    amount: int | None = None
    duration_seconds: int = RGB_INVOICE_DURATION_SECONDS


class SendAssetRequestModel(BaseModel):
    """Request model for sending assets."""

    asset_id: str
    amount: int
    recipient_id: str
    donation: bool | None = False
    fee_rate: int
    min_confirmations: int
    transport_endpoints: list[str]
    skip_sync: bool = False


class ListTransfersRequestModel(AssetIdModel):
    """Request model for listing asset transfers."""

class GetAssetMediaModelRequestModel(BaseModel):
    """Response model for get asset medial api"""
    digest: str

class FailTransferRequestModel(BaseModel):
    """Response model for fail transfer"""
    batch_transfer_idx: int
    no_asset_only: bool = False
    skip_sync: bool = False

# -------------------- Response models -----------------------


class AssetBalanceResponseModel(Balance):
    """Response model for asset balance."""
    offchain_outbound: int = 0
    offchain_inbound: int = 0


class CreateUtxosResponseModel(StatusModel):
    """Response model for creating UTXOs."""


class DecodeRgbInvoiceResponseModel(BaseModel):
    """Decoded invoice (`rgb_lib.InvoiceData`) for POST /wallet/decodergbinvoice."""

    model_config = ConfigDict(from_attributes=True)

    recipient_id: str
    asset_schema: Optional[AssetSchema] = None
    asset_id: Optional[str] = None
    assignment: Any
    assignment_name: Optional[str] = None
    network: BitcoinNetwork
    expiration_timestamp: Optional[int] = None
    transport_endpoints: list[str] = Field(default_factory=list)


class GetAssetResponseModel(BaseModel):
    """Response model for list assets."""
    nia: list[AssetModel | None] | None = []
    uda: list[AssetModel | None] | None = []
    cfa: list[AssetModel | None] | None = []
    ifa: list[AssetIfa | None] | None = []


class IssueAssetResponseModel(AssetModel):
    """Response model for issuing assets."""


class RefreshTransferResponseModel(StatusModel):
    """Response model for refreshing asset transfers."""


class RgbInvoiceDataResponseModel(BaseModel):
    """Response model for invoice data."""

    recipient_id: str
    invoice: str
    expiration_timestamp: datetime
    batch_transfer_idx: int


class SendAssetResponseModel(BaseModel):
    """Response model for sending assets."""

    txid: str


class GetAssetMediaModelResponseModel(BaseModel):
    """Response model for get asset media api"""
    bytes_hex: str


class PostAssetMediaModelResponseModel(BaseModel):
    """Response model for get asset media api"""
    digest: str


class RgbAssetPageLoadModel(BaseModel):
    """RGB asset detail page load model"""
    asset_id: str | None = None
    asset_name: str | None = None
    image_path: str | None = None
    asset_type: str


class FailTransferResponseModel(BaseModel):
    """Response model for fail transfer"""
    transfers_changed: bool


class WalletFailTransfersResponse(BaseModel):
    """POST /wallet/failtransfers — whether any transfers were failed."""

    failed: bool


class RefreshedTransferItem(BaseModel):
    """Single entry in `wallet.refresh` result (`rgb_lib.RefreshedTransfer`)."""

    model_config = ConfigDict(from_attributes=True)

    updated_status: Optional[TransferStatus] = None
    failure: Optional[Any] = None


class RefreshWalletResponse(RootModel[dict[str, RefreshedTransferItem]]):
    """`wallet.refresh` returns a map of transfer index (JSON object keys) to refresh outcomes."""


class RefreshJobStatusResponse(BaseModel):
    """Row from `refresh_jobs` (GET /wallet/refresh/status/{job_id})."""

    id: int
    job_id: str
    xpub_van: str
    xpub_col: str
    master_fingerprint: str
    trigger: str
    recipient_id: Optional[str] = None
    asset_id: Optional[str] = None
    status: str
    attempts: int = 0
    max_retries: int = 10
    created_at: Optional[int] = None
    processed_at: Optional[int] = None
    error_message: Optional[str] = None


class RefreshWatcherStatusResponse(BaseModel):
    """Row from `refresh_watchers` (GET /wallet/refresh/watcher/...)."""

    id: int
    xpub_van: str
    xpub_col: str
    master_fingerprint: str
    recipient_id: str
    asset_id: Optional[str] = None
    status: str
    refresh_count: int = 0
    last_refresh: Optional[int] = None
    created_at: Optional[int] = None
    expires_at: Optional[int] = None


class WalletSyncResponse(BaseModel):
    """POST /wallet/sync"""

    message: str


class WalletRestoreResponse(BaseModel):
    """POST /wallet/restore"""

    message: str


class SyncJobEnqueuedResponse(BaseModel):
    """POST /wallet/sync-job"""

    message: str
    job_id: str


class BackupCreatedResponse(BaseModel):
    """POST /wallet/backup"""

    message: str
    download_url: str


class TransferTransportEndpoint(BaseModel):
    endpoint: str
    transport_type: TransportType
    used: bool
    
# class AssignmentFungible(BaseModel):
#     type: Literal["FUNGIBLE"]
#     amount: int

# class AssignmentNonFungible(BaseModel):
#     type: Literal["NON_FUNGIBLE"]

# class AssignmentInflationRight(BaseModel):
#     type: Literal["INFLATION_RIGHT"]
#     amount: int

# class AssignmentReplaceRight(BaseModel):
#     type: Literal["REPLACE_RIGHT"]

# class AssignmentAny(BaseModel):
#     type: Literal["ANY"]

# Assignment = Union[
#     AssignmentFungible,
#     AssignmentNonFungible,
#     AssignmentInflationRight,
#     AssignmentReplaceRight,
#     AssignmentAny
# ]


class RgbBlockTime(BaseModel):
    """Bitcoin confirmation metadata from rgb-lib (`BlockTime`)."""

    model_config = ConfigDict(from_attributes=True)

    height: int
    timestamp: int


class RgbWalletTransaction(BaseModel):
    """BTC / RGB-related transaction row from `wallet.list_transactions` (rgb-lib `Transaction`)."""

    model_config = ConfigDict(from_attributes=True)

    transaction_type: TransactionType
    txid: str
    received: int
    sent: int
    fee: int
    confirmation_time: Optional[RgbBlockTime] = None


class Transfer(BaseModel):
    """Model representing an RGB transfer (`wallet.list_transfers`)."""

    model_config = ConfigDict(from_attributes=True)

    idx: int
    batch_transfer_idx: int
    created_at: int
    updated_at: int
    status: TransferStatus
    requested_assignment: Optional[Any] = None
    assignments: List[Any] = Field(default_factory=list)
    kind: TransferKind
    txid: Optional[str] = None
    recipient_id: Optional[str] = None
    receive_utxo: Optional[Outpoint] = None
    change_utxo: Optional[Outpoint] = None
    expiration_timestamp: Optional[int] = None
    transport_endpoints: List[TransferTransportEndpoint] = Field(default_factory=list)
    invoice_string: Optional[str] = None
    consignment_path: Optional[str] = None


class ListTransferAssetResponseModel(BaseModel):
    """Response model for listing asset transfers."""

    transfers: list[Transfer | None] | None = []


class ListTransferAssetWithBalanceResponseModel(ListTransferAssetResponseModel):
    """Response model for listing asset transfers with asset balance"""

    asset_balance: AssetBalanceResponseModel