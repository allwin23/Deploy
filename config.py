import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret')
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 8  # 8 hours (seconds)

    # Database
    # Render provides DATABASE_URL starting with "postgres://", SQLAlchemy needs "postgresql://"
    _raw_db_url = os.environ.get('DATABASE_URL', 'sqlite:///blockchain_demo.db')
    SQLALCHEMY_DATABASE_URI = _raw_db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Auth users — stored as JSON string in env var
    AUTH_USERS_JSON = os.environ.get('AUTH_USERS', '{"alice":"password123","admin":"admin123"}')

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')

    # Blockchain network identity (purely cosmetic for simulation)
    NETWORK_NAME = os.environ.get('NETWORK_NAME', 'HoneypotChain')
    CHANNEL_NAME = os.environ.get('CHANNEL_NAME', 'evidencechannel')
    CHAINCODE_NAME = os.environ.get('CHAINCODE_NAME', 'evidence')
    ORG_MSP_ID = os.environ.get('ORG_MSP_ID', 'Org1MSP')
