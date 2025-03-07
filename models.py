from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class UserActivity(db.Model):
    __tablename__ = 'user_activity'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    login_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    points_awarded = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<UserActivity user_id={self.user_id} date={self.login_date}>'

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    name = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(200), nullable=True, default='/static/images/default_profile.png')
    bio = db.Column(db.String(500), nullable=True)
    favorite_quote = db.Column(db.String(500), nullable=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy=True)
    activities = db.relationship('UserActivity', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'

class Post(db.Model):
    __tablename__ = 'post'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    content = db.Column(db.Text, nullable=False)
    post_length = db.Column(db.Integer, nullable=False, default=0)
    post_type = db.Column(db.String(50), nullable=False)  # 'poetry' or 'story'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='post', lazy=True)

    def __repr__(self):
        return f'<Post {self.title}>'

    @property
    def comment_count(self):
        return len(self.comments)
        
    @property
    def like_count(self):
        return len(self.likes)

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    comment_length = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ai_score = db.Column(db.Integer, nullable=True)
    ai_feedback = db.Column(db.Text, nullable=True)  # Store AI reasoning/feedback
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    likes = db.relationship('Like', backref='comment', lazy=True)

    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'

    @staticmethod
    def validate_content(content):
        """Validate comment content length"""
        min_length = 10
        max_length = 5000
        if not (min_length <= len(content) <= max_length):
            raise ValueError(
                f'Comment length must be between {min_length} and {max_length} characters'
            )

class Like(db.Model):
    __tablename__ = 'like'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Like user_id={self.user_id} post_id={self.post_id} comment_id={self.comment_id}>'
