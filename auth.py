from flask import Blueprint, request, jsonify, current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from google.oauth2 import id_token
from google.auth.transport import requests
from models import db, User
from http import HTTPStatus

auth = Blueprint('auth', __name__)
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), HTTPStatus.BAD_REQUEST
    
    user = User(
        email=data['email'],
        name=data['name'],
        password_hash=generate_password_hash(data['password'])
    )

    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), HTTPStatus.CREATED

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        login_user(user)
        return jsonify({'message': 'Logged in successfully'})
    
    return jsonify({'error': 'Invalid credentials'}), HTTPStatus.UNAUTHORIZED

@auth.route('/google/login', methods=['POST'])
def google_login():
    try:
        token = request.json.get('token')
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            current_app.config['GOOGLE_CLIENT_ID']
        )
        
        email = idinfo['email']
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(
                email=email,
                name=idinfo.get('name'),
                google_id=idinfo['sub']
            )
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        return jsonify({'message': 'Logged in successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), HTTPStatus.UNAUTHORIZED

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'})

@auth.route('/profile')
@login_required
def profile():
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'name': current_user.name,
        'favorite_quote': current_user.favorite_quote,
        'points': current_user.points
    })

@auth.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json()

    current_user.name = data.get('name', current_user.name)
    current_user.favorite_quote = data.get('favorite_quote', current_user.favorite_quote)

    db.session.commit()

    return jsonify({'message': 'Profile updated successfully'})
