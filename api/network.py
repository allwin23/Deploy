"""
Network API — simulated Hyperledger Fabric network status.
This provides the "gimmick" info the user requested to show "connected systems".
"""

from flask import Blueprint, jsonify, current_app
from api.auth import login_required

network_bp = Blueprint('network', __name__)


@network_bp.route('/status', methods=['GET'])
@login_required
def network_status():
    """
    Returns a convincing set of metadata about the 'connected' blockchain network.
    ---
    tags:
      - Network
    security:
      - Bearer: []
    responses:
      200:
        description: Network status summary
    """
    return jsonify({
        'status': 'success',
        'data': {
            'network_name': current_app.config.get('NETWORK_NAME', 'HoneypotChain'),
            'channel': current_app.config.get('CHANNEL_NAME', 'evidencechannel'),
            'chaincode': {
                'name': current_app.config.get('CHAINCODE_NAME', 'evidence'),
                'version': '2.4.1',
                'sequence': 12,
                'status': 'READY'
            },
            'organizations': [
                {
                    'name': 'Org1',
                    'msp_id': 'Org1MSP',
                    'peers': [
                        {'id': 'peer0.org1.example.com', 'status': 'ONLINE', 'endpoint': 'grpcs://peer0.org1:7051'},
                        {'id': 'peer1.org1.example.com', 'status': 'ONLINE', 'endpoint': 'grpcs://peer1.org1:8051'}
                    ]
                },
                {
                    'name': 'OrdererOrg',
                    'msp_id': 'OrdererMSP',
                    'orderers': [
                        {'id': 'orderer.example.com', 'status': 'ONLINE', 'endpoint': 'grpcs://orderer:7050'}
                    ]
                }
            ],
            'consensus': 'Raft',
            'state_database': 'CouchDB',
            'block_height': 42  # Simplified, could be linked to actual block count
        }
    }), 200
