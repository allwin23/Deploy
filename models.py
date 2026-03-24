"""
SQLAlchemy models for the blockchain demo.

Tables:
  users       — registered users with simulated wallet addresses
  blocks      — simulated blockchain blocks (SHA-256 hash-chained)
  transactions— every write operation anchored to a block
  evidence    — the actual evidence records (text + metadata)
"""

import hashlib
import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# User / Wallet
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    # Simulated Fabric MSP identity string
    msp_id = db.Column(db.String(64), nullable=False, default='Org1MSP')
    # Deterministic wallet address derived from username
    wallet_address = db.Column(db.String(64), unique=True, nullable=False)
    org = db.Column(db.String(128), nullable=False, default='org1.example.com')
    role = db.Column(db.String(32), nullable=False, default='analyst')  # analyst | admin
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow)

    @staticmethod
    def derive_wallet(username: str) -> str:
        """Deterministically generate a hex wallet address from a username."""
        return '0x' + hashlib.sha256(f'wallet:{username}'.encode()).hexdigest()[:40]

    def to_dict(self):
        return {
            'username': self.username,
            'wallet_address': self.wallet_address,
            'msp_id': self.msp_id,
            'org': self.org,
            'role': self.role,
            'created_at': self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Blockchain Blocks
# ---------------------------------------------------------------------------

class Block(db.Model):
    __tablename__ = 'blocks'

    id = db.Column(db.Integer, primary_key=True)
    block_number = db.Column(db.Integer, unique=True, nullable=False, index=True)
    previous_hash = db.Column(db.String(64), nullable=False)
    data_hash = db.Column(db.String(64), nullable=False)   # hash of all TXs in block
    block_hash = db.Column(db.String(64), unique=True, nullable=False)
    channel_name = db.Column(db.String(64), nullable=False, default='evidencechannel')
    creator_msp_id = db.Column(db.String(64), nullable=False, default='Org1MSP')
    transaction_count = db.Column(db.Integer, nullable=False, default=0)
    timestamp = db.Column(db.DateTime(timezone=True), default=_utcnow, index=True)

    transactions = db.relationship('Transaction', back_populates='block', lazy='dynamic')

    def to_dict(self, include_txs=False):
        d = {
            'block_number': self.block_number,
            'hash': self.block_hash,
            'previous_hash': self.previous_hash,
            'data_hash': self.data_hash,
            'channel': self.channel_name,
            'creator_msp_id': self.creator_msp_id,
            'transaction_count': self.transaction_count,
            'timestamp': self.timestamp.isoformat(),
        }
        if include_txs:
            d['transactions'] = [t.to_dict() for t in self.transactions]
        return d


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    tx_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    block_id = db.Column(db.Integer, db.ForeignKey('blocks.id'), nullable=False)
    submitter = db.Column(db.String(64), nullable=False)          # username
    submitter_wallet = db.Column(db.String(64), nullable=False)
    chaincode = db.Column(db.String(64), nullable=False, default='evidence')
    function_name = db.Column(db.String(64), nullable=False)       # e.g. SubmitEvidence
    payload_hash = db.Column(db.String(64), nullable=False)        # SHA-256 of the input
    status = db.Column(db.String(16), nullable=False, default='VALID')  # VALID | INVALID
    timestamp = db.Column(db.DateTime(timezone=True), default=_utcnow, index=True)

    block = db.relationship('Block', back_populates='transactions')

    def to_dict(self):
        return {
            'tx_id': self.tx_id,
            'block_number': self.block.block_number if self.block else None,
            'submitter': self.submitter,
            'submitter_wallet': self.submitter_wallet,
            'chaincode': self.chaincode,
            'function': self.function_name,
            'payload_hash': self.payload_hash,
            'status': self.status,
            'timestamp': self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Evidence Records
# ---------------------------------------------------------------------------

class Evidence(db.Model):
    __tablename__ = 'evidence'

    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    tx_id = db.Column(db.String(64), db.ForeignKey('transactions.tx_id'), nullable=False)
    submitter = db.Column(db.String(64), nullable=False)
    submitter_wallet = db.Column(db.String(64), nullable=False)

    # Content
    filename = db.Column(db.String(256), nullable=True)       # original filename if any
    content_text = db.Column(db.Text, nullable=True)          # raw text content
    content_hash = db.Column(db.String(64), nullable=False)   # SHA-256 of content
    content_size_bytes = db.Column(db.Integer, nullable=False, default=0)

    # Metadata
    honeypot_id = db.Column(db.String(64), nullable=True)
    honeypot_type = db.Column(db.String(64), nullable=True)
    attack_type = db.Column(db.String(64), nullable=True)
    source_ip_hash = db.Column(db.String(64), nullable=True)
    mitre_technique = db.Column(db.String(256), nullable=True)

    # Lifecycle
    record_status = db.Column(db.String(32), nullable=False, default='ACTIVE')
    owning_org = db.Column(db.String(128), nullable=False, default='org1.example.com')
    custody_chain = db.Column(db.Text, nullable=False, default='[]')  # JSON list

    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def to_dict(self, include_content=True):
        import json as _json
        d = {
            'evidence_id': self.evidence_id,
            'tx_id': self.tx_id,
            'submitter': self.submitter,
            'submitter_wallet': self.submitter_wallet,
            'filename': self.filename,
            'content_hash': self.content_hash,
            'content_size_bytes': self.content_size_bytes,
            'honeypot_id': self.honeypot_id,
            'honeypot_type': self.honeypot_type,
            'attack_type': self.attack_type,
            'source_ip_hash': self.source_ip_hash,
            'mitre_technique': self.mitre_technique,
            'status': self.record_status,
            'owning_org': self.owning_org,
            'custody_chain': _json.loads(self.custody_chain),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
        if include_content:
            d['content'] = self.content_text
        return d
