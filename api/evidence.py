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

from io import BytesIO
from flask import Blueprint, request, jsonify, send_file

from models import db, Evidence, User
from blockchain.simulator import commit_transaction
evidence_bp = Blueprint('evidence', __name__)


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def _get_current_user() -> User | None:
    username = request.headers.get('X-Username') or request.args.get('username', '')
    username = username.strip() if username else ''
    if not username:
        return None
    return User.query.filter_by(username=username).first()


def _get_last_non_empty_line(text: str) -> str:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return lines[-1] if lines else 'Empty evidence content'


# --------------------------------------------------------------------------
# POST /api/evidence  — submit a new evidence record
# --------------------------------------------------------------------------

@evidence_bp.route('', methods=['POST'])
def submit_evidence():
    """
    Submit new evidence
    ---
    tags:
      - Evidence
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: false
        description: The evidence file to upload
      - name: evidenceId
        in: formData
        type: string
        description: Unique evidence ID (generated if missing)
      - name: honeypotId
        in: formData
        type: string
        description: ID of source honeypot
      - name: attackType
        in: formData
        type: string
        description: e.g. SQLi, Brute Force
      - name: content
        in: formData
        type: string
        description: Raw text evidence (if no file)
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

    # Auto-generate missing metadata if not provided
    honeypot_id = data.get('honeypotId') or f"HP-{uuid.uuid4().hex[:4].upper()}"
    attack_type = data.get('attackType') or "SENSORY_ALERT"
    source_ip_hash = data.get('sourceIpHash') or _sha256("0.0.0.0")
    mitre_technique = data.get('mitreTechnique') or "T1059"

    # Build the full payload string (mirrors what chaincode would store)
    payload = json.dumps({
        'evidenceId': evidence_id,
        'honeypotId': honeypot_id,
        'honeypotType': data.get('honeypotType', 'VirtualHoneypot'),
        'attackType': attack_type,
        'sourceIpHash': source_ip_hash,
        'mitreTechnique': mitre_technique,
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
        honeypot_id=honeypot_id,
        honeypot_type=data.get('honeypotType', 'VirtualHoneypot'),
        attack_type=attack_type,
        source_ip_hash=source_ip_hash,
        mitre_technique=mitre_technique,
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
def list_evidence():
    """
    List all evidence records
    ---
    tags:
      - Evidence
    responses:
      200:
        description: List of all evidence entries
    """
    all_evidence = Evidence.query.order_by(Evidence.created_at.desc()).all()
    include_content = request.args.get('include_content', 'false').lower() in ('1', 'true', 'yes')

    return jsonify({
        'status': 'success',
        'total_records': len(all_evidence),
        'data': [e.to_dict(include_content=include_content) for e in all_evidence],
    }), 200


# --------------------------------------------------------------------------
# GET /api/evidence/stats  — quick accumulation stats
# --------------------------------------------------------------------------

@evidence_bp.route('/stats', methods=['GET'])
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
def get_evidence(evidence_id):
    ev = Evidence.query.filter_by(evidence_id=evidence_id).first()
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404
    return jsonify({'status': 'success', 'data': ev.to_dict()}), 200


#---- --------------------------------------------------------------------------
# GET /api/evidence/<id>/download  — download content as a file
# --------------------------------------------------------------------------

@evidence_bp.route('/<evidence_id>/download', methods=['GET'])
def download_evidence(evidence_id):
        """
        Download evidence content as a file
        ---
        tags:
            - Evidence
        parameters:
            - name: evidence_id
                in: path
                type: string
                required: true
                description: Evidence ID to download
        responses:
            200:
                description: File download (text/plain)
                schema:
                    type: string
                    example: "last line of evidence\nsecond line"
            404:
                description: Evidence not found or no content
        """
    ev = Evidence.query.filter_by(evidence_id=evidence_id).first()
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404
    if not ev.content_text:
        return jsonify({'error': 'No content available for this evidence'}), 404

    filename = ev.filename or f"{evidence_id}.txt"
    content_bytes = ev.content_text.encode('utf-8')
    return send_file(
        BytesIO(content_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype='text/plain'
    )


# --------------------------------------------------------------------------
# GET /api/evidence/latest-lines — last line for every record
# --------------------------------------------------------------------------

@evidence_bp.route('/latest-lines', methods=['GET'])
def latest_lines():
        """
        Get the last non-empty line for each evidence record
        ---
        tags:
            - Evidence
        parameters:
            - name: limit
                in: query
                type: integer
                required: false
                default: 100
                description: Max records to return (1-500)
        responses:
            200:
                description: Latest line for each evidence record
        """
    limit = request.args.get('limit', 100, type=int)
    limit = max(1, min(limit, 500))

    records = Evidence.query.order_by(Evidence.created_at.desc()).limit(limit).all()
    data = []
    for ev in records:
        last_line = _get_last_non_empty_line(ev.content_text or '')
        data.append({
            'evidence_id': ev.evidence_id,
            'filename': ev.filename,
            'tx_id': ev.tx_id,
            'last_line': last_line,
            'timestamp': ev.created_at.isoformat(),
        })

    return jsonify({
        'status': 'success',
        'count': len(data),
        'data': data,
    }), 200


# --------------------------------------------------------------------------
# PUT /api/evidence/<id>/status  — update lifecycle status
# --------------------------------------------------------------------------

@evidence_bp.route('/<evidence_id>/status', methods=['PUT'])
def update_status(evidence_id):
    return jsonify({
        'error': 'Immutable database',
        'message': 'Evidence records cannot be updated.'
    }), 409


# --------------------------------------------------------------------------
# POST /api/evidence/<id>/transfer  — custody transfer
# --------------------------------------------------------------------------

@evidence_bp.route('/<evidence_id>/transfer', methods=['POST'])
def transfer_custody(evidence_id):
    return jsonify({
        'error': 'Immutable database',
        'message': 'Evidence custody cannot be updated.'
    }), 409


# --------------------------------------------------------------------------
# GET /api/evidence/latest-command — for timeline ledger component
# --------------------------------------------------------------------------

@evidence_bp.route('/latest-command', methods=['GET'])
def latest_command():
    """Returns the last line of the latest evidence submission."""
    """
    Get the last line of the latest evidence submission
    ---
    tags:
      - Evidence
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
