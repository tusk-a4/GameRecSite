import sys
import os

# Add parent directory to path so imports work
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Change to parent directory so relative paths work
os.chdir(parent_dir)

# Set VERCEL environment variable
os.environ['VERCEL'] = '1'

# Import app after path setup
try:
    from app import app
except Exception as e:
    # If import fails, create a minimal error handler
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error():
        return f'Error importing app: {str(e)}', 500

# Vercel Python runtime: export the WSGI application
# The @vercel/python builder will handle WSGI apps
handler = app

