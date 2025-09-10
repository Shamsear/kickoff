import os
from flask import Flask
from flask_socketio import SocketIO
from dotenv import load_dotenv
from config import Config
try:
    from database import init_supabase
except ImportError as e:
    print(f"Warning: Database import failed: {e}")
    def init_supabase():
        print("Using mock database")

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Initialize Supabase
    init_supabase()
    
    # Create upload directories
    upload_dirs = ['static/uploads/images', 'static/uploads/videos', 'static/uploads/documents']
    for directory in upload_dirs:
        os.makedirs(directory, exist_ok=True)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.tournament import tournament_bp
    from routes.match import match_bp
    from routes.media import media_bp
    from routes.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tournament_bp, url_prefix='/tournament')
    app.register_blueprint(match_bp, url_prefix='/match')
    app.register_blueprint(media_bp, url_prefix='/media')
    
    # Register SocketIO events
    from websocket_events import register_events
    register_events(socketio)
    
    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app()
    print("\n🚀 Starting TournamentPro server...")
    print("📍 Server will be available at: http://localhost:5000")
    print("📍 Network access at: http://0.0.0.0:5000")
    print("💡 Press Ctrl+C to stop the server\n")
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Thank you for using TournamentPro!")
