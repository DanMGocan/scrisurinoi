from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Post, Comment
from http import HTTPStatus
import openai

posts = Blueprint('posts', __name__)

@posts.route('/posts', methods=['POST'])
@login_required
def create_post():
    data = request.get_json()
    
    if not all(k in data for k in ['title', 'content', 'post_type']):
        return jsonify({'error': 'Missing required fields'}), HTTPStatus.BAD_REQUEST
        
    if data['post_type'] not in ['poetry', 'story']:
        return jsonify({'error': 'Invalid post type'}), HTTPStatus.BAD_REQUEST
    
    post = Post(
        title=data['title'],
        content=data['content'],
        post_type=data['post_type'],
        user_id=current_user.id
    )
    
    db.session.add(post)
    db.session.commit()
    
    return jsonify({
        'message': 'Post created successfully',
        'post_id': post.id
    }), HTTPStatus.CREATED

@posts.route('/posts', methods=['GET'])
def get_posts():
    post_type = request.args.get('type')
    query = Post.query
    
    if post_type:
        query = query.filter_by(post_type=post_type)
    
    posts = query.order_by(Post.created_at.desc()).all()
    
    return jsonify([{
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'post_type': post.post_type,
        'author': post.author.name,
        'created_at': post.created_at.isoformat(),
        'comment_count': len(post.comments)
    } for post in posts])

@posts.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    return jsonify({
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'post_type': post.post_type,
        'author': post.author.name,
        'created_at': post.created_at.isoformat(),
        'comments': [{
            'id': comment.id,
            'content': comment.content,
            'author': comment.author.name,
            'created_at': comment.created_at.isoformat(),
            'ai_score': comment.ai_score,
            'ai_feedback': comment.ai_feedback
        } for comment in post.comments]
    })

async def evaluate_comment(content, post_type):
    """Evaluate comment using OpenAI API"""
    try:
        prompt = f"""
        Evaluate this comment on a {post_type}. Consider:
        1. Thoughtfulness
        2. Constructive feedback
        3. Relevance
        4. Writing quality
        
        Comment: {content}
        
        Provide:
        1. Score (0-100)
        2. Brief feedback
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a literary critic evaluating comments."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse response to extract score and feedback
        evaluation = response.choices[0].message.content
        # Simple parsing - in production you'd want more robust parsing
        score_line = [line for line in evaluation.split('\n') if 'Score' in line][0]
        score = float(score_line.split(':')[1].strip())
        feedback = evaluation.split('Feedback:')[1].strip()
        
        return score, feedback
        
    except Exception as e:
        return 0, f"Error in AI evaluation: {str(e)}"

@posts.route('/posts/<int:post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    
    if 'content' not in data:
        return jsonify({'error': 'Missing comment content'}), HTTPStatus.BAD_REQUEST
    
    # Evaluate comment using AI
    score, feedback = evaluate_comment(data['content'], post.post_type)
    
    comment = Comment(
        content=data['content'],
        user_id=current_user.id,
        post_id=post_id,
        ai_score=score,
        ai_feedback=feedback
    )
    
    # Award points based on AI score
    points_awarded = int(score / 10)  # 1 point for every 10 points in AI score
    current_user.points += points_awarded
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'message': 'Comment added successfully',
        'comment_id': comment.id,
        'ai_score': score,
        'ai_feedback': feedback,
        'points_awarded': points_awarded
    }), HTTPStatus.CREATED
