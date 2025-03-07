from flask import Flask, render_template, redirect, url_for, flash, request
from flask_migrate import Migrate
from flask_login import login_required, current_user
from models import db, Post, User, Comment, Like
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
        sort = request.args.get('sort', 'recent')
        
        query = Post.query
        
        if post_type:
            query = query.filter_by(post_type=post_type)
        
        # Apply sorting
        if sort == 'recent':
            query = query.order_by(Post.created_at.desc())
        elif sort == 'likes':
            # Order by number of likes (most liked first)
            query = query.outerjoin(Post.likes).group_by(Post.id).order_by(db.func.count(Like.id).desc())
        elif sort == 'comments':
            # Order by number of comments (most commented first)
            query = query.outerjoin(Post.comments).group_by(Post.id).order_by(db.func.count(Comment.id).desc())
        elif sort == 'random':
            # Random order
            query = query.order_by(db.func.random())
        
        posts = query.all()
        return render_template('posts/index.html', posts=posts, Post=Post)

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
        
    @app.route('/authors')
    def authors_list():
        sort = request.args.get('sort', 'date')
        
        query = User.query
        
        # Apply sorting
        if sort == 'date':
            # Sort by registration date (newest first)
            query = query.order_by(User.created_at.desc())
        elif sort == 'posts':
            # Sort by number of posts (most posts first)
            query = query.outerjoin(User.posts).group_by(User.id).order_by(db.func.count(Post.id).desc())
        elif sort == 'likes':
            # Sort by number of likes received (most likes first)
            query = query.outerjoin(User.posts).outerjoin(Post.likes).group_by(User.id).order_by(db.func.count(Like.id).desc())
        
        authors = query.all()
        
        # Calculate likes received for each author
        for author in authors:
            likes_received = 0
            for post in author.posts:
                likes_received += len(post.likes)
            author.likes_received = likes_received
            
        return render_template('authors_list.html', authors=authors)

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
