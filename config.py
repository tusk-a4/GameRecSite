import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    # Use PostgreSQL on Vercel, SQLite locally
    if os.environ.get('VERCEL'):
        # Vercel provides DATABASE_URL for PostgreSQL
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///:memory:'
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RAWG_API_KEY = os.environ.get('RAWG_API_KEY') or ''
    RAWG_API_BASE_URL = 'https://api.rawg.io/api'


