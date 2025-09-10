import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'webm'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # App Information
    APP_NAME = os.environ.get('APP_NAME', 'TournamentPro')
    APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
