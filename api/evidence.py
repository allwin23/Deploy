"""
Evidence API — the core chaincode-equivalent endpoints.

POST   /api/evidence              Submit a new evidence record (text or form-data)
GET    /api/evidence              List all evidence with summary stats
GET    /api/evidence/stats        Accumulated file / byte counts
GET    /api/evidence/<id>         Get a single evidence record
PUT    /api/evidence/<id>/status  Update evidence status (ACTIVE → ARCHIVED etc.)
POST   /api/evidence/<id>/transfer Transfer custody to another org
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from models import db, Evidence, User
from blockchain.simulator import commit_transaction
from api.auth import login_required

evidence_bp = Blueprint('evidence', __name__)


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def _get_current_user() -> User | None:
    username = get_jwt_identity()
    return User.query.filter_by(username=username).first()


# --------------------------------------------------------------------------
# POST /api/evidence  — submit a new evidence record
# --------------------------------------------------------------------------

@evidence_bp.route('', methods=['POST'])
@login_required
def submit_evidence():
    """
    Submit new evidence
    ---
    tags:
      - Evidence
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            evidenceId:
              type: string
            honeypotId:
              type: string
            content:
              type: string
            attackType:
              type: string
    responses:
      201:
        description: Evidence committed to blockchain
      400:
        description: Bad request
    """
    user = _get_current_user()

    # Accept both JSON and multipart form-data (text file upload)
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form.to_dict()
        file = request.files.get('file')
        if file and file.filename:
            content_text = file.read().decode('utf-8', errors='replace')
            filename = file.filename
        else:
            content_text = data.get('content', '')
            filename = None
    else:
        data = request.get_json(silent=True) or {}
        content_text = data.get('content', '')
        filename = data.get('filename')

    if not content_text:
        return jsonify({'error': 'No content provided'}), 400

    evidence_id = data.get('evidenceId') or f"EVI-{uuid.uuid4().hex[:8].upper()}"
    content_hash = _sha256(content_text)

    # Build the full payload string (mirrors what chaincode would store)
    payload = json.dumps({
        'evidenceId': evidence_id,
        'honeypotId': data.get('honeypotId', ''),
        'honeypotType': data.get('honeypotType', ''),
        'attackType': data.get('attackType', ''),
        'sourceIpHash': data.get('sourceIpHash', ''),
        'mitreTechnique': data.get('mitreTechnique', ''),
        'contentHash': content_hash,
        'submitter': user.username if user else 'unknown',
    }, sort_keys=True)

    tx = commit_transaction(
        submitter=user.username if user else 'unknown',
        submitter_wallet=user.wallet_address if user else '0x0',
        function_name='SubmitEvidence',
        payload=payload,
    )

    ev = Evidence(
        evidence_id=evidence_id,
        tx_id=tx.tx_id,
        submitter=user.username if user else 'unknown',
        submitter_wallet=user.wallet_address if user else '0x0',
        filename=filename,
        content_text=content_text,
        content_hash=content_hash,
        content_size_bytes=len(content_text.encode('utf-8')),
        honeypot_id=data.get('honeypotId', ''),
        honeypot_type=data.get('honeypotType', ''),
        attack_type=data.get('attackType', ''),
        source_ip_hash=data.get('sourceIpHash', ''),
        mitre_technique=data.get('mitreTechnique', ''),
        record_status='ACTIVE',
        custody_chain=json.dumps([{
            'org': user.org if user else 'org1.example.com',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': 'CREATED',
        }]),
    )
    db.session.add(ev)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Evidence committed to blockchain',
        'tx_id': tx.tx_id,
        'block_number': tx.block.block_number,
        'evidence_id': evidence_id,
        'content_hash': content_hash,
    }), 201


# --------------------------------------------------------------------------
# GET /api/evidence  — list all records with counts
# --------------------------------------------------------------------------

@evidence_bp.route('', methods=['GET'])
@login_required
def list_evidence():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    query = Evidence.query.order_by(Evidence.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'status': 'success',
        'total_records': paginated.total,
        'page': page,
        'per_page': per_page,
        'total_pages': paginated.pages,
        'data': [e.to_dict(include_content=False) for e in paginated.items],
    }), 200


# --------------------------------------------------------------------------
# GET /api/evidence/stats  — quick accumulation stats
# --------------------------------------------------------------------------

@evidence_bp.route('/stats', methods=['GET'])
@login_required
def evidence_stats():
    from sqlalchemy import func
    total_records = Evidence.query.count()
    total_bytes = db.session.query(
        func.sum(Evidence.content_size_bytes)
    ).scalar() or 0
    active = Evidence.query.filter_by(record_status='ACTIVE').count()
    archived = Evidence.query.filter_by(record_status='ARCHIVED').count()
    return jsonify({
        'status': 'success',
        'total_files_submitted': total_records,
        'total_bytes_stored': total_bytes,
        'total_kb_stored': round(total_bytes / 1024, 2),
        'active_records': active,
        'archived_records': archived,
    }), 200


# --------------------------------------------------------------------------
# GET /api/evidence/<id>  — single record
# --------------------------------------------------------------------------

@evidence_bp.route('/<evidence_id>', methods=['GET'])
@login_required
def get_evidence(evidence_id):
    ev = Evidence.query.filter_by(evidence_id=evidence_id).first()
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404
    return jsonify({'status': 'success', 'data': ev.to_dict()}), 200


# --------------------------------------------------------------------------
# PUT /api/evidence/<id>/status  — update lifecycle status
# --------------------------------------------------------------------------

@evidence_bp.route('/<evidence_id>/status', methods=['PUT'])
@login_required
def update_status(evidence_id):
    user = _get_current_user()
    ev = Evidence.query.filter_by(evidence_id=evidence_id).first()
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404

    new_status = (request.get_json(silent=True) or {}).get('status', '')
    if new_status not in ('ACTIVE', 'ARCHIVED', 'UNDER_REVIEW', 'DELETED'):
        return jsonify({'error': 'Invalid status value'}), 400

    payload = json.dumps({'evidenceId': evidence_id, 'newStatus': new_status})
    tx = commit_transaction(
        submitter=user.username if user else 'system',
        submitter_wallet=user.wallet_address if user else '0x0',
        function_name='UpdateEvidenceStatus',
        payload=payload,
    )
    ev.record_status = new_status
    db.session.commit()

    return jsonify({'status': 'success', 'tx_id': tx.tx_id, 'new_status': new_status}), 200


# --------------------------------------------------------------------------
# POST /api/evidence/<id>/transfer  — custody transfer
# --------------------------------------------------------------------------

@evidence_bp.route('/<evidence_id>/transfer', methods=['POST'])
@login_required
def transfer_custody(evidence_id):
    user = _get_current_user()
    ev = Evidence.query.filter_by(evidence_id=evidence_id).first()
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404

    data = request.get_json(silent=True) or {}
    new_org = data.get('newOwningOrg', '')
    reason = data.get('reason', 'Administrative transfer')

    if not new_org:
        return jsonify({'error': 'newOwningOrg is required'}), 400

    payload = json.dumps({'evidenceId': evidence_id, 'to': new_org, 'reason': reason})
    tx = commit_transaction(
        submitter=user.username if user else 'system',
        submitter_wallet=user.wallet_address if user else '0x0',
        function_name='TransferCustody',
        payload=payload,
    )

    # Update custody chain
    chain = json.loads(ev.custody_chain)
    chain.append({
        'from': ev.owning_org,
        'to': new_org,
        'reason': reason,
        'tx_id': tx.tx_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })
    ev.owning_org = new_org
    ev.custody_chain = json.dumps(chain)
    db.session.commit()

    return jsonify({'status': 'success', 'tx_id': tx.tx_id, 'custody_chain': chain}), 200


# --------------------------------------------------------------------------
# GET /api/evidence/latest-command — for timeline ledger component
# --------------------------------------------------------------------------

@evidence_bp.route('/latest-command', methods=['GET'])
@login_required
def latest_command():
    """Returns the last line of the latest evidence submission."""
    """
    Get the last line of the latest evidence submission
    ---
    tags:
      - Evidence
    security:
      - Bearer: []
    responses:
      200:
        description: Command line output
    """
    latest = Evidence.query.order_by(Evidence.created_at.desc()).first()
    if not latest or not latest.content_text:
        return jsonify({
            'status': 'success',
            'command': 'Waiting for network activity...',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200

    # Get the last non-empty line
    lines = [line.strip() for line in latest.content_text.split('\n') if line.strip()]
    last_line = lines[-1] if lines else 'Empty evidence content'

    return jsonify({
        'status': 'success',
        'command': last_line,
        'evidence_id': latest.evidence_id,
        'tx_id': latest.tx_id,
        'timestamp': latest.created_at.isoformat()
    }), 200
