from flask import Blueprint, request, jsonify, current_app, url_for, render_template, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from google.oauth2 import id_token
from google.auth.transport import requests
from models import db, User, UserActivity
from http import HTTPStatus
from config import Config
from datetime import datetime, timedelta
import logging

auth = Blueprint('auth', __name__)
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ['email', 'password', 'name']):
        return jsonify({'error': 'Missing required fields'}), HTTPStatus.BAD_REQUEST
    
    # Validate password complexity
    if len(data['password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long'}), HTTPStatus.BAD_REQUEST
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), HTTPStatus.BAD_REQUEST
    
    user = User(
        email=data['email'],
        name=data['name'],
        password_hash=generate_password_hash(data['password'])
    )

    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), HTTPStatus.CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), HTTPStatus.INTERNAL_SERVER_ERROR

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        login_user(user)
        
        # Award daily login points if not already awarded today
        today = datetime.utcnow().date()
        activity = UserActivity.query.filter_by(user_id=user.id, login_date=today).first()
        
        if not activity:
            # First login of the day
            activity = UserActivity(user_id=user.id, login_date=today, points_awarded=True)
            user.points += Config.DAILY_LOGIN_REWARD
            db.session.add(activity)
            
            # Calculate days since last login to award membership points
            yesterday = today - timedelta(days=1)
            last_activity = UserActivity.query.filter_by(user_id=user.id).filter(
                UserActivity.login_date < today
            ).order_by(UserActivity.login_date.desc()).first()
            
            if last_activity and last_activity.login_date == yesterday:
                # Consecutive login - award membership points for the day
                user.points += Config.DAILY_MEMBERSHIP_REWARD
            
            db.session.commit()
            
            return jsonify({
                'message': 'Logged in successfully',
                'points_awarded': Config.DAILY_LOGIN_REWARD
            })
        
        return jsonify({'message': 'Logged in successfully'})
    
    return jsonify({'error': 'Invalid credentials'}), HTTPStatus.UNAUTHORIZED

@auth.route('/login', methods=['GET'])
def login_page():
    return render_template('auth/login.html')

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
        
        # Award daily login points if not already awarded today
        today = datetime.utcnow().date()
        activity = UserActivity.query.filter_by(user_id=user.id, login_date=today).first()
        
        if not activity:
            # First login of the day
            activity = UserActivity(user_id=user.id, login_date=today, points_awarded=True)
            user.points += Config.DAILY_LOGIN_REWARD
            db.session.add(activity)
            
            # Calculate days since last login to award membership points
            yesterday = today - timedelta(days=1)
            last_activity = UserActivity.query.filter_by(user_id=user.id).filter(
                UserActivity.login_date < today
            ).order_by(UserActivity.login_date.desc()).first()
            
            if last_activity and last_activity.login_date == yesterday:
                # Consecutive login - award membership points for the day
                user.points += Config.DAILY_MEMBERSHIP_REWARD
            
            db.session.commit()
            
            return jsonify({
                'message': 'Logged in successfully',
                'points_awarded': Config.DAILY_LOGIN_REWARD
            })
        
        return jsonify({'message': 'Logged in successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), HTTPStatus.UNAUTHORIZED

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ai fost deconectat cu succes!', 'success')
    return redirect(url_for('index'))

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
