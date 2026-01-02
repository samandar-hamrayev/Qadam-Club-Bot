from flask import Flask
from flask_cors import CORS
from .database import init_db
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    
    # Initialize database
    with app.app_context():
        init_db()
    
    # Register Blueprints
    from .routes.auth import auth_bp
    from .routes.challenges import challenges_bp
    from .routes.leaderboard import leaderboard_bp
    from .routes.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(challenges_bp, url_prefix='/api/challenges')
    app.register_blueprint(leaderboard_bp, url_prefix='/api/leaderboard')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    @app.route('/')
    def index():
        return {"status": "ok", "message": "Qadam Club API is running"}
    
    # Serve Frontend for TMA and Admin
    from flask import send_from_directory
    import os

    @app.route('/tma')
    def serve_tma():
        frontend_dir = os.path.join(app.root_path, '../frontend/tma')
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/admin-panel')
    def serve_admin():
        frontend_dir = os.path.join(app.root_path, '../frontend/admin')
        return send_from_directory(frontend_dir, 'index.html')
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
