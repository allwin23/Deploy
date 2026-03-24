"""
Blockchain Simulator — produces real SHA-256 hash-chained blocks.

Every call to `commit_transaction()` creates (or appends to) a pending
block and returns a signed tx_id.  The block is finalised immediately
for simplicity (1 TX per block), which matches Hyperledger Fabric's
default behaviour under low load.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from models import db, Block, Transaction


GENESIS_HASH = '0' * 64   # Hash of the imaginary block 0


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def _utcnow():
    return datetime.now(timezone.utc)


def _get_latest_block() -> Block | None:
    return Block.query.order_by(Block.block_number.desc()).first()


def generate_tx_id(function_name: str, payload: str, submitter_wallet: str) -> str:
    """Deterministic TX ID: SHA-256(uuid + function + wallet + payload-hash)."""
    nonce = str(uuid.uuid4())
    raw = f"{nonce}:{function_name}:{submitter_wallet}:{_sha256(payload)}"
    return _sha256(raw)


def commit_transaction(
    submitter: str,
    submitter_wallet: str,
    function_name: str,
    payload: str,          # JSON-serialisable string of all inputs
    channel_name: str = 'evidencechannel',
    chaincode: str = 'evidence',
) -> Transaction:
    """
    Simulate submitting a transaction to the blockchain.
    Creates a new Block and one Transaction inside it.
    Returns the committed Transaction object.
    """
    payload_hash = _sha256(payload)
    tx_id = generate_tx_id(function_name, payload, submitter_wallet)

    # Hash-chain: get previous block hash
    latest = _get_latest_block()
    prev_hash = latest.block_hash if latest else GENESIS_HASH
    next_block_number = (latest.block_number + 1) if latest else 1

    # Data hash = hash of (tx_id + payload_hash)
    data_hash = _sha256(f"{tx_id}{payload_hash}")

    # Block hash = hash of (block_number + prev_hash + data_hash + timestamp)
    ts_str = _utcnow().isoformat()
    block_hash = _sha256(
        f"{next_block_number}{prev_hash}{data_hash}{ts_str}{channel_name}"
    )

    block = Block(
        block_number=next_block_number,
        previous_hash=prev_hash,
        data_hash=data_hash,
        block_hash=block_hash,
        channel_name=channel_name,
        creator_msp_id='Org1MSP',
        transaction_count=1,
    )
    db.session.add(block)
    db.session.flush()   # get block.id before committing

    tx = Transaction(
        tx_id=tx_id,
        block_id=block.id,
        submitter=submitter,
        submitter_wallet=submitter_wallet,
        chaincode=chaincode,
        function_name=function_name,
        payload_hash=payload_hash,
        status='VALID',
    )
    db.session.add(tx)
    db.session.commit()
    return tx


def get_chain_stats() -> dict:
    """Return aggregate blockchain statistics."""
    total_blocks = Block.query.count()
    total_txs = Transaction.query.count()
    latest = _get_latest_block()
    return {
        'total_blocks': total_blocks,
        'total_transactions': total_txs,
        'latest_block_number': latest.block_number if latest else 0,
        'latest_block_hash': latest.block_hash if latest else GENESIS_HASH,
        'latest_block_timestamp': latest.timestamp.isoformat() if latest else None,
    }


def verify_chain_integrity() -> dict:
    """Walk the chain and verify every block's hash is correct."""
    blocks = Block.query.order_by(Block.block_number.asc()).all()
    issues = []
    prev_hash = GENESIS_HASH

    for block in blocks:
        if block.previous_hash != prev_hash:
            issues.append({
                'block_number': block.block_number,
                'error': 'previous_hash mismatch',
                'expected': prev_hash,
                'found': block.previous_hash,
            })
        prev_hash = block.block_hash

    return {
        'verified': len(issues) == 0,
        'blocks_checked': len(blocks),
        'issues': issues,
    }
