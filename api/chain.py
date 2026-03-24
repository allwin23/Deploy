"""
Chain API — explore the simulated blockchain.

GET /api/chain          → Paginated list of all blocks
GET /api/chain/stats    → Total blocks, transactions, and latest block info
GET /api/chain/blocks/<n> → Get details of a specific block by number
GET /api/chain/verify   → Cryptographic integrity check of the entire chain
"""

from flask import Blueprint, jsonify, request
from models import Block, Transaction
from blockchain.simulator import get_chain_stats, verify_chain_integrity
from api.auth import login_required

chain_bp = Blueprint('chain', __name__)


@chain_bp.route('', methods=['GET'])
@login_required
def get_chain():
    """
    Get paginated blockchain blocks
    ---
    tags:
      - Chain
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 10
    responses:
      200:
        description: List of blocks
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    
    blocks = Block.query.order_by(Block.block_number.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'status': 'success',
        'data': {
            'blocks': [b.to_dict(include_txs=True) for b in blocks.items],
            'total_blocks': blocks.total,
            'pages': blocks.pages,
            'current_page': page
        }
    }), 200


@chain_bp.route('/stats', methods=['GET'])
@login_required
def chain_stats():
    """
    Get blockchain summary statistics
    ---
    tags:
      - Chain
    security:
      - Bearer: []
    responses:
      200:
        description: Chain stats
    """
    stats = get_chain_stats()
    return jsonify({
        'status': 'success',
        'data': stats
    }), 200


@chain_bp.route('/blocks/<int:block_number>', methods=['GET'])
@login_required
def get_block(block_number):
    block = Block.query.filter_by(block_number=block_number).first()
    if not block:
        return jsonify({'error': f'Block {block_number} not found'}), 404
        
    return jsonify({
        'status': 'success',
        'data': block.to_dict(include_txs=True)
    }), 200


@chain_bp.route('/verify', methods=['GET'])
@login_required
def verify_chain():
    """
    Verify blockchain integrity
    ---
    tags:
      - Chain
    security:
      - Bearer: []
    responses:
      200:
        description: Integrity check result
    """
    result = verify_chain_integrity()
    return jsonify({
        'status': 'success',
        'data': result
    }), 200
