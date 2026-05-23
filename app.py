import os
from flask import Flask, redirect, url_for, jsonify
from dotenv import load_dotenv
from models import db
from config import config
from utils import generate_csrf_token

load_dotenv()


def create_app():
    app = Flask(__name__)
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config.get(env, config['default']))

    db.init_app(app)

    # Make CSRF token available in all templates
    app.jinja_env.globals['csrf_token'] = generate_csrf_token

    # Register blueprints
    from routes.auth import auth_bp
    from routes.topics import topics_bp
    from routes.profile import profile_bp
    from routes.civic_units import civic_units_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(topics_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(civic_units_bp)

    # Seed route — development only
    @app.route('/admin/seed')
    def admin_seed():
        if os.environ.get('FLASK_ENV') != 'development':
            return 'Not available in production.', 403
        from services.topic_service import seed_interests, seed_topics
        seed_interests()
        seed_topics()
        return jsonify({'status': 'ok', 'message': 'Interests and sample topics seeded.'})

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
