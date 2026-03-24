"""
Auth API — JWT-based login/logout with wallet identity.

POST /api/auth/login   → { access_token, user }
POST /api/auth/logout  → { message }
GET  /api/auth/me      → { username, wallet_address, msp_id, ... }
"""

import json
import hashlib
from functools import wraps

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)

from models import db, User

auth_bp = Blueprint('auth', __name__)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_users() -> dict:
    """Load username→password map from config / env."""
    try:
        return json.loads(current_app.config.get('AUTH_USERS_JSON', '{}'))
    except (json.JSONDecodeError, TypeError):
        return {}


def _get_or_create_user(username: str) -> User:
    """Return existing User row or create one on first login."""
    user = User.query.filter_by(username=username).first()
    if not user:
        users_map = _get_users()
        pw = users_map.get(username, '')
        role = 'admin' if username == 'admin' else 'analyst'
        user = User(
            username=username,
            password_hash=_hash_password(pw),
            wallet_address=User.derive_wallet(username),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
    return user


# --------------------------------------------------------------------------
# Decorator re-exported for other blueprints
# --------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login to the system
    ---
    tags:
      - Auth
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              example: alice
            password:
              type: string
              example: password123
    responses:
      200:
        description: Login successful
      401:
        description: Invalid credentials
    """
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    users_map = _get_users()
    if username not in users_map or users_map[username] != password:
        return jsonify({'error': 'Invalid username or password'}), 401

    user = _get_or_create_user(username)
    token = create_access_token(identity=username)
    return jsonify({
        'message': 'Login successful',
        'access_token': token,
        'token_type': 'Bearer',
        'user': user.to_dict(),
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    """
    Get current user profile
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: User profile data
    """
    username = get_jwt_identity()
    user = _get_or_create_user(username)
    return jsonify(user.to_dict()), 200


@auth_bp.route('/wallet/<username>', methods=['GET'])
@login_required
def wallet_info(username):
    """Return the wallet address for any registered user (public info)."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'username': user.username,
        'wallet_address': user.wallet_address,
        'msp_id': user.msp_id,
        'org': user.org,
    }), 200
