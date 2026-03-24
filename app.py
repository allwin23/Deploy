import sys
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flasgger import Swagger

# Ensure the demo directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config.get('CORS_ORIGINS', '*')}})
    jwt = JWTManager(app)
    
    # Initialize Swagger
    app.config['SWAGGER'] = {
        'title': 'Blockchain Demo API',
        'uiversion': 3,
        'specs_route': '/apidocs/',
        'description': 'A production-grade mock blockchain backend for demo purposes.'
    }
    swagger = Swagger(app)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not Found', 'message': str(error)}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred'}), 500

    # Health check
    @app.route('/api/health')
    def health():
        return jsonify({
            'status': 'ok',
            'message': 'Blockchain Demo API is healthy',
            'database': 'connected' if db.engine else 'error'
        }), 200

    # Register blueprints
    from api.auth import auth_bp
    from api.evidence import evidence_bp
    from api.chain import chain_bp
    from api.network import network_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(evidence_bp, url_prefix='/api/evidence')
    app.register_blueprint(chain_bp, url_prefix='/api/chain')
    app.register_blueprint(network_bp, url_prefix='/api/network')

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    return app


# Application object for WSGI
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=(Config.FLASK_ENV == 'development'))
