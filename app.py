from flask import Flask, render_template, redirect, url_for, flash, request
from flask_migrate import Migrate
from flask_login import login_required, current_user
from models import db, Post
from auth import auth, login_manager
from posts import posts
import os

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # Database configuration - detect environment
    if os.environ.get('GAE_ENV', '').startswith('standard') or os.environ.get('K_SERVICE'):
        # Running on Google Cloud (App Engine or Cloud Run)
        # Use Cloud SQL with PostgreSQL
        db_user = os.environ.get('DB_USER')
        db_pass = os.environ.get('DB_PASS')
        db_name = os.environ.get('DB_NAME')
        db_socket_dir = os.environ.get('DB_SOCKET_DIR', '/cloudsql')
        cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
        
        # If using Cloud SQL with PostgreSQL
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            f'postgresql+psycopg2://{db_user}:{db_pass}@/{db_name}'
            f'?host={db_socket_dir}/{cloud_sql_connection_name}'
        )
    else:
        # Local development - use SQLite
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///literary_app.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    app.config['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(auth, url_prefix='/api/auth')
    app.register_blueprint(posts, url_prefix='/api')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Main routes
    @app.route('/')
    def index():
        post_type = request.args.get('type')
        query = Post.query
        
        if post_type:
            query = query.filter_by(post_type=post_type)
        
        posts = query.order_by(Post.created_at.desc()).all()
        return render_template('posts/index.html', posts=posts)

    @app.route('/posts/create')
    @login_required
    def create_post():
        return render_template('posts/create.html')

    @app.route('/posts/<int:post_id>')
    def view_post(post_id):
        post = Post.query.get_or_404(post_id)
        if post is None:
            return render_template('404.html'), 404
        return render_template('posts/view.html', post=post)

    @app.route('/profile')
    @login_required
    def profile():
        return render_template('profile.html')

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    @app.route('/register')
    def register_page():
        return render_template('auth/register.html')
    
    # Custom filter
    def nl2br(s):
        return s.replace('\n', '<br>')

    app.jinja_env.filters['nl2br'] = nl2br
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
