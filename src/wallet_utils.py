import os
import json
import glob
from rgb_lib import (
    Wallet,
    restore_backup,
    WalletData,
    SinglesigKeys,
    BitcoinNetwork,
    DatabaseType,
    AssetSchema,
)

print("NETWORK raw =", os.getenv("NETWORK"))
print("INDEXER_URL raw =", os.getenv("INDEXER_URL"))
print("PROXY_ENDPOINT raw =", os.getenv("PROXY_ENDPOINT"))
env_network = int(os.getenv("NETWORK", "3"))
NETWORK = BitcoinNetwork(env_network)
BASE_PATH = "./data"
RESTORED_PATH = "./data"
BACKUP_PATH = "./backup"
vanilla_keychain = 0
wallet_instances: dict[str, dict[str, object]] = {}
INDEXER_URL = os.getenv("INDEXER_URL")

if INDEXER_URL is None:
    raise EnvironmentError("Missing required env var: INDEXER_URL")

# rgb-lib WalletData.reuse_addresses: when True, receive flows may reuse derivation slots
# (see rgb-lib docs). Set REUSE_ADDRESSES=1 at deploy time; default off.
_REUSE_ADDRESSES_RAW = os.getenv("REUSE_ADDRESSES", "").strip().lower()
REUSE_ADDRESSES = _REUSE_ADDRESSES_RAW in ("1", "true", "yes", "on")

SCHEMAS_FULL = [AssetSchema.NIA, AssetSchema.CFA, AssetSchema.UDA, AssetSchema.IFA]
SCHEMAS_OFFLINE = [AssetSchema.NIA, AssetSchema.CFA, AssetSchema.UDA]


def _wallet_data(data_dir: str, supported_schemas: list, reuse_addresses: bool) -> WalletData:
    return WalletData(
        data_dir=data_dir,
        bitcoin_network=NETWORK,
        database_type=DatabaseType.SQLITE,
        max_allocations_per_utxo=1,
        supported_schemas=supported_schemas,
        reuse_addresses=reuse_addresses,
    )


def resolved_reuse_addresses(client_id: str, override: bool | None = None) -> bool:
    """rgb-lib WalletData.reuse_addresses: optional API override, then wallet.json, then REUSE_ADDRESSES env."""
    cfg = load_wallet_config(client_id) or {}
    if override is not None:
        value = bool(override)
    elif "reuse_addresses" in cfg:
        value = bool(cfg["reuse_addresses"])
    else:
        value = REUSE_ADDRESSES
    if cfg.get("reuse_addresses") != value:
        save_wallet_config(client_id, {**cfg, "reuse_addresses": value})
    return value


def _singlesig_keys(
    xpub_van: str,
    xpub_col: str,
    master_fingerprint: str | None,
    mnemonic: str | None = None,
) -> SinglesigKeys:
    return SinglesigKeys(
        account_xpub_vanilla=xpub_van,
        account_xpub_colored=xpub_col,
        vanilla_keychain=vanilla_keychain,
        master_fingerprint=master_fingerprint or "",
        mnemonic=mnemonic,
    )


class WalletNotFoundError(Exception):
    pass


class WalletStateExistsError(Exception):
    """Raised when attempting to restore over an existing wallet state."""

    pass


def get_wallet_path(client_id: str):
    return os.path.join(BASE_PATH, client_id)


def get_restored_wallet_path(client_id: str):
    return os.path.join(RESTORED_PATH, client_id)


def remove_backup_if_exists(client_id: str):
    os.makedirs(BACKUP_PATH, exist_ok=True)
    pattern = os.path.join(BACKUP_PATH, f"{client_id}.backup*")
    removed = False
    for path in glob.glob(pattern):
        try:
            os.remove(path)
            removed = True
        except FileNotFoundError:
            continue
    if removed:
        print(f"Removed existing backups for {client_id} matching {pattern}")


def get_backup_path(client_id: str):
    os.makedirs(BACKUP_PATH, exist_ok=True)
    return os.path.join(BACKUP_PATH, f"{client_id}.backup")


def get_wallet_config_path(client_id: str):
    return os.path.join(get_wallet_path(client_id), "wallet.json")


def save_wallet_config(client_id: str, config: dict):
    os.makedirs(get_wallet_path(client_id), exist_ok=True)
    with open(get_wallet_config_path(client_id), "w") as f:
        json.dump(config, f, indent=2)


def load_wallet_config(client_id: str):
    path = get_wallet_config_path(client_id)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def create_wallet_instance(
    xpub_van: str,
    xpub_col: str,
    master_fingerprint: str,
    reuse_addresses: bool | None = None,
):
    client_id = xpub_van
    if client_id in wallet_instances:
        instance = wallet_instances[client_id]
        if instance.get("wallet") and instance.get("online"):
            return instance["wallet"], instance["online"]

    config_path = get_wallet_path(client_id)

    if not os.path.exists(config_path):
        os.makedirs(get_wallet_path(client_id), exist_ok=True)
    print("init wallet network:", NETWORK)
    ra = resolved_reuse_addresses(client_id, reuse_addresses)
    wallet_data = _wallet_data(get_wallet_path(client_id), SCHEMAS_FULL, ra)
    keys = _singlesig_keys(xpub_van, xpub_col, master_fingerprint, mnemonic=None)
    wallet = Wallet(wallet_data, keys)
    print("prepere online", INDEXER_URL)
    online = wallet.go_online(False, INDEXER_URL)
    print("wallet online")
    wallet_instances[client_id] = {
        "wallet": wallet,
        "online": online,
    }
    return wallet, online


def upload_backup(client_id: str):
    remove_backup_if_exists(client_id)
    backup_path = get_backup_path(client_id)


def restore_wallet_instance(
    xpub_van: str,
    xpub_col: str,
    master_fingerprint: str,
    password: str,
    backup_path: str,
    reuse_addresses: bool | None = None,
):
    client_id = xpub_van
    restore_path = get_restored_wallet_path(client_id)

    if client_id in wallet_instances or os.path.exists(restore_path):
        raise WalletStateExistsError(
            "Wallet state already exists. Restoring over an existing state is not allowed because it can corrupt RGB state."
        )

    os.makedirs(restore_path, exist_ok=True)

    print("restore_backup", backup_path, password, restore_path)
    restore_backup(backup_path, password, restore_path)
    ra = resolved_reuse_addresses(client_id, reuse_addresses)
    wallet_data = _wallet_data(restore_path, SCHEMAS_FULL, ra)
    keys = _singlesig_keys(xpub_van, xpub_col, master_fingerprint, mnemonic=None)
    wallet = Wallet(wallet_data, keys)
    online = wallet.go_online(False, INDEXER_URL)
    wallet_instances[client_id] = {
        "wallet": wallet,
        "online": online,
    }
    return wallet, online


def offline_wallet_instance(
    xpub_van: str,
    xpub_col: str,
    mnemonic: str | None = None,
    master_fingerprint: str | None = None,
):
    client_id = xpub_van
    ra = resolved_reuse_addresses(client_id)
    wallet_data = _wallet_data(get_wallet_path(client_id), SCHEMAS_OFFLINE, ra)
    keys = _singlesig_keys(xpub_van, xpub_col, master_fingerprint, mnemonic=mnemonic)
    wallet = Wallet(wallet_data, keys)
    return wallet


def test_wallet_instance(
    xpub_van: str,
    xpub_col: str,
    mnemonic: str | None = None,
    master_fingerprint: str | None = None,
):
    client_id = xpub_van

    ra = resolved_reuse_addresses(client_id)
    wallet_data = _wallet_data(get_wallet_path(client_id), SCHEMAS_FULL, ra)
    keys = _singlesig_keys(xpub_van, xpub_col, master_fingerprint, mnemonic=mnemonic)
    wallet = Wallet(wallet_data, keys)
    online = wallet.go_online(False, INDEXER_URL)
    wallet_instances[client_id] = {
        "wallet": wallet,
        "online": online,
    }
    return wallet, online


def load_wallet_instance(xpub_van: str, xpub_col: str, master_fingerprint: str):
    client_id = xpub_van
    if client_id in wallet_instances:
        instance = wallet_instances[client_id]
        if instance.get("wallet") and instance.get("online"):
            return instance["wallet"], instance["online"]
    config_path = get_wallet_path(client_id)
    print("load_wallet_instance", config_path)
    if not os.path.exists(config_path):
        raise WalletNotFoundError(f"Wallet for client '{client_id}' does not exist.")

    ra = resolved_reuse_addresses(client_id)
    wallet_data = _wallet_data(get_wallet_path(client_id), SCHEMAS_FULL, ra)
    keys = _singlesig_keys(xpub_van, xpub_col, master_fingerprint, mnemonic=None)
    wallet = Wallet(wallet_data, keys)
    online = wallet.go_online(False, INDEXER_URL)
    wallet_instances[client_id] = {
        "wallet": wallet,
        "online": online,
    }
    return wallet, online


def refresh_wallet_instance(xpub_van: str, xpub_col: str, master_fingerprint: str):
    if xpub_van in wallet_instances:
        del wallet_instances[xpub_van]
    return load_wallet_instance(xpub_van, xpub_col, master_fingerprint)
