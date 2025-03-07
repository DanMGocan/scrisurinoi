from flask import Blueprint, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, Post, Comment, Like
from http import HTTPStatus
from config import Config
import logging
import os
import re
import json
from openai import OpenAI

posts = Blueprint('posts', __name__)

def validate_post_data(data):
    """Validate post creation data."""
    if not all(k in data for k in ['title', 'content', 'post_type']):
        raise ValueError('Missing required fields')
        
    if data['post_type'] not in ['poetry', 'story', 'essay', 'theater', 'letter', 'journal']:
        raise ValueError('Invalid post type')

def calculate_post_cost(post_type, content):
    """Calculate the cost of creating a post."""
    word_count = len(content.split())
    cost = Config.POST_COSTS.get(post_type, 5)  # Default to 5 if category not found
    
    if word_count > Config.POST_WORD_LIMIT:
        additional_cost = (word_count // Config.POST_WORD_LIMIT) * Config.POST_WORD_COST_MULTIPLIER
        cost += additional_cost
        
    return cost

def handle_response(message, status_code, **kwargs):
    """Handle unified JSON/form responses."""
    if request.is_json:
        response = {'message': message, **kwargs}
        if status_code >= HTTPStatus.BAD_REQUEST:
            response['error'] = message
        return jsonify(response), status_code
    else:
        flash(message, 'success' if status_code == HTTPStatus.CREATED else 'error')
        return redirect(url_for('posts.create_post'))

@posts.route('/posts', methods=['POST'])
@login_required
def create_post():
    """Create a new post with validation and cost calculation."""
    try:
        data = request.get_json() if request.is_json else request.form
        validate_post_data(data)
        
        post = Post(
            title=data['title'],
            description=data.get('description', ''),
            content=data['content'],
            post_length=len(data['content']),
            post_type=data['post_type'],
            user_id=current_user.id
        )

        cost = calculate_post_cost(data['post_type'], data['content'])
        
        if current_user.points < cost:
            error_msg = f'Puncte insuficiente. Ai nevoie de {cost} puncte pentru a crea această postare.'
            return handle_response(error_msg, HTTPStatus.BAD_REQUEST)

        current_user.points -= cost
        db.session.add(post)
        db.session.commit()

        success_msg = 'Postare creată cu succes!'
        return handle_response(success_msg, HTTPStatus.CREATED, post_id=post.id)

    except ValueError as e:
        return handle_response(str(e), HTTPStatus.BAD_REQUEST)
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating post: {str(e)}")
        return handle_response('A apărut o eroare la crearea postării', HTTPStatus.INTERNAL_SERVER_ERROR)

@posts.route('/posts', methods=['GET'])
def get_posts():
    """Get paginated list of posts with filtering."""
    post_type = request.args.get('type')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    query = Post.query
    if post_type:
        query = query.filter_by(post_type=post_type)

    posts = query.order_by(Post.created_at.desc()).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )

    return jsonify({
        'items': [serialize_post(post) for post in posts.items],
        'total': posts.total,
        'pages': posts.pages,
        'current_page': posts.page
    })

def serialize_post(post):
    """Serialize post data for JSON responses."""
    return {
        'id': post.id,
        'title': post.title,
        'description': post.description,
        'post_type': post.post_type,
        'author': post.author.name,
        'created_at': post.created_at.isoformat(),
        'comment_count': len(post.comments),
        'like_count': len(post.likes)
    }

@posts.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get detailed post data with comments."""
    post = Post.query.get_or_404(post_id)
    
    comments_data = []
    for comment in post.comments:
        # Only consider a comment as spam if it has a score of 0
        is_spam_copied = (True if comment.ai_score == 0 else False)
        logging.info(f"Comment ID: {comment.id}, AI Score: {comment.ai_score}, is_spam_copied: {is_spam_copied}")
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'author': comment.author.name,
            'created_at': comment.created_at.isoformat(),
            'ai_score': comment.ai_score,
            'ai_feedback': comment.ai_feedback,
            'like_count': len(comment.likes),
            'is_spam_copied': is_spam_copied
        })
    
    return jsonify({
        'id': post.id,
        'title': post.title,
        'description': post.description,
        'content': post.content,
        'post_type': post.post_type,
        'author': post.author.name,
        'created_at': post.created_at.isoformat(),
        'like_count': len(post.likes),
        'comments': comments_data
    })

def evaluate_comment_with_openai(content, post_type, post_content=None, post_title=None):
    """Evaluate comment using OpenAI model."""
    log_file_path = "ai_evaluation.log"
    
    try:
        # Log the API key (masked) for debugging
        openai_api_key = os.getenv('OPENAI_API_KEY')
        masked_key = openai_api_key[:8] + "..." + openai_api_key[-4:] if openai_api_key and len(openai_api_key) > 12 else "***"
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"\nUsing OpenAI API key: {masked_key}\n")
            f.write(f"Using OpenAI o3-mini model for evaluation\n")
        
        # Log the comment
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"Evaluating comment: {content}\n")
            if post_content:
                f.write(f"Post content: {post_content[:100]}...\n")
            if post_title:
                f.write(f"Post title: {post_title}\n")
        
        # Check for spam patterns first (quick check before API call)
        spam_patterns = [
            'http://', 'https://', 'www.', '.com', '.net', '.org',  # URLs
            'viagra', 'cialis', 'buy now', 'discount', 'free offer',  # Common spam words
            'casino', 'lottery', 'winner', 'prize', 'money',  # More spam words
        ]
        
        # Check if comment contains spam patterns
        contains_spam = any(pattern in content.lower() for pattern in spam_patterns)
        
        # Log spam check
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"Initial spam check: {contains_spam}\n")
        
        if contains_spam:
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(f"Comment flagged as spam, skipping API call\n")
            return 0, True, "Comment contains spam patterns"
        
        # Prepare the prompt for OpenAI
        system_prompt = """You are an expert literary critic and community moderator for a Romanian literary platform. 
Your task is to evaluate comments on literary works based on:
1. Relevance to the original post
2. Literary insight and value
3. Constructive feedback
4. Thoughtfulness and depth
5. Appropriate tone and language

Rate the comment on a scale of 0-100, where:
0-20: Spam, irrelevant, or inappropriate
21-40: Minimal effort, generic, or superficial
41-60: Adequate but lacks depth or insight
61-80: Good quality with relevant insights
81-100: Exceptional literary analysis with depth and originality

Also determine if the comment is spam or copied content (yes/no).

Provide your evaluation in JSON format:
{
  "score": [0-100],
  "is_spam_or_copied": [true/false],
  "reasoning": "[brief explanation of your evaluation]"
}"""

        user_prompt = f"Original Post Type: {post_type}\n"
        if post_title:
            user_prompt += f"Original Post Title: {post_title}\n"
        if post_content:
            user_prompt += f"Original Post Content: {post_content}\n"
        user_prompt += f"Comment to Evaluate: {content}"
        
        # Log the prompts
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"System prompt: {system_prompt}\n")
            f.write(f"User prompt: {user_prompt}\n")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=openai_api_key)
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Extract the response
        response_content = response.choices[0].message.content
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"OpenAI response: {response_content}\n")
        
        # Parse the JSON response
        evaluation = json.loads(response_content)
        
        score = int(evaluation.get("score", 0))
        is_spam_copied = evaluation.get("is_spam_or_copied", False)
        reasoning = evaluation.get("reasoning", "No reasoning provided")
        
        # Log the evaluation
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"Parsed evaluation - Score: {score}, Is spam/copied: {is_spam_copied}\n")
            f.write(f"Reasoning: {reasoning}\n")
        
        # Return the score, whether it's spam or copied, and the reasoning
        return score, is_spam_copied, reasoning

    except Exception as e:
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"ERROR in evaluate_comment_with_openai: {str(e)}\n")
            import traceback
            f.write(f"Traceback: {traceback.format_exc()}\n")
        logging.error(f"OpenAI evaluation error: {e}")
        return 0, False, "Error evaluating comment"

def evaluate_comment(content, post_type):
    """Evaluate comment using OpenAI API."""
    # This is a legacy function that doesn't include post context
    # It should return three values to match the new signature
    score, is_spam_copied, reasoning = evaluate_comment_with_openai(content, post_type)
    return score, is_spam_copied, reasoning

@posts.route('/posts/<int:post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    
    if 'content' not in data:
        return jsonify({'error': 'Missing comment content'}), HTTPStatus.BAD_REQUEST
    
    try:
        # Validate comment length
        Comment.validate_content(data['content'])
        
        # Log the comment attempt
        log_file_path = "ai_evaluation.log"
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"\nNew comment attempt on post {post_id}: {data['content']}\n")

        # Evaluate comment using AI with post context
        score, is_spam_copied, reasoning = evaluate_comment_with_openai(
            content=data['content'], 
            post_type=post.post_type,
            post_content=post.content,
            post_title=post.title
        )
        
        # Log the score
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"AI score: {score}, is_spam_copied: {is_spam_copied}\n")
        
        # Set minimum scores based on comment length and content
        if not is_spam_copied:
            # Calculate comment length in words
            word_count = len(data['content'].split())
            
            # Log the word count
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(f"Comment word count: {word_count}\n")
            
            # If the AI evaluation failed or returned 0, set a minimum score based on length
            if score == 0:
                if word_count > 200:  # Very long, detailed comment
                    score = 80
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Setting score to 80 for very long comment ({word_count} words)\n")
                elif word_count > 100:  # Long comment
                    score = 60
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Setting score to 60 for long comment ({word_count} words)\n")
                elif word_count > 50:  # Medium comment
                    score = 40
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Setting score to 40 for medium comment ({word_count} words)\n")
                elif word_count > 20:  # Short but substantial comment
                    score = 20
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Setting score to 20 for short comment ({word_count} words)\n")
                else:  # Very short comment
                    score = 10
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Setting score to 10 for very short comment ({word_count} words)\n")
            
            # Ensure minimum scores based on length even if AI gave a lower score
            if word_count > 200 and score < 60:
                score = 60
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Increasing score to minimum 60 for very long comment\n")
            elif word_count > 100 and score < 40:
                score = 40
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Increasing score to minimum 40 for long comment\n")
            elif word_count > 50 and score < 20:
                score = 20
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Increasing score to minimum 20 for medium comment\n")
        
        comment = Comment(
            content=data['content'],
            comment_length=len(data['content']),
            user_id=current_user.id,
            post_id=post_id,
            ai_score=int(score),
            ai_feedback=reasoning
        )
        
        # Award points based on AI score and quality thresholds
        if score == 0 or is_spam_copied:
            points_awarded = 0
        elif score <= Config.COMMENT_QUALITY_THRESHOLDS['low']:
            points_awarded = Config.COMMENT_QUALITY_REWARDS['low']
        elif score <= Config.COMMENT_QUALITY_THRESHOLDS['medium']:
            points_awarded = Config.COMMENT_QUALITY_REWARDS['medium']
        else:
            points_awarded = Config.COMMENT_QUALITY_REWARDS['high']
        
        current_user.points += points_awarded
        
        db.session.add(comment)
        db.session.commit()
        
        if is_spam_copied:
            return jsonify({
                'message': 'Comment added successfully',
                'comment_id': comment.id,
                'warning': "Acest comentariu a fost marcat ca spam sau a fost copiat un comentariu anterior",
                'points_awarded': points_awarded
            }), HTTPStatus.CREATED
        else:
            return jsonify({
                'message': 'Comment added successfully',
                'comment_id': comment.id,
                'ai_score': int(score),
                'points_awarded': points_awarded
            }), HTTPStatus.CREATED

    except ValueError as e:
        return jsonify({'error': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding comment: {str(e)}")
        return jsonify({'error': 'Failed to add comment'}), HTTPStatus.INTERNAL_SERVER_ERROR

@posts.route('/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        return jsonify({'error': 'You are not authorized to delete this post'}), HTTPStatus.FORBIDDEN
    
    try:
        db.session.delete(post)
        db.session.commit()
        return jsonify({'message': 'Post deleted successfully'}), HTTPStatus.NO_CONTENT
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting post: {str(e)}")
        return jsonify({'error': 'Failed to delete post'}), HTTPStatus.INTERNAL_SERVER_ERROR

@posts.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Check if user is authenticated
    if current_user.is_authenticated:
        like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        
        try:
            if like:
                # User is unliking the post
                db.session.delete(like)
                
                # Remove points from both the liker and post author
                current_user.points -= Config.LIKE_GIVEN_REWARD  # Remove points for giving a like
                post.author.points -= Config.POST_LIKE_REWARD    # Remove points from post author
            else:
                # User is liking the post
                like = Like(user_id=current_user.id, post_id=post_id)
                db.session.add(like)
                
                # Award points to both the liker and post author
                current_user.points += Config.LIKE_GIVEN_REWARD  # Award points for giving a like
                post.author.points += Config.POST_LIKE_REWARD    # Award points to post author
                
            db.session.commit()
            # Refresh the post object to get the updated likes
            db.session.refresh(post)
            return jsonify({
                'message': 'Post like toggled successfully',
                'like_count': len(post.likes)
            }), HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error toggling post like: {str(e)}")
            return jsonify({'error': 'Failed to toggle post like'}), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        # Guest like
        try:
            # For guest likes, we just increment the author's points
            post.author.points += Config.POST_LIKE_REWARD
            db.session.commit()
            return jsonify({
                'message': 'Guest like added successfully',
                'like_count': len(post.likes) + 1  # Add 1 for the guest like (not stored in DB)
            }), HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding guest like: {str(e)}")
            return jsonify({'error': 'Failed to add guest like'}), HTTPStatus.INTERNAL_SERVER_ERROR

@posts.route('/comments/<int:comment_id>/like', methods=['POST'])
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user is authenticated
    if current_user.is_authenticated:
        like = Like.query.filter_by(user_id=current_user.id, comment_id=comment_id).first()
        
        try:
            if like:
                # User is unliking the comment
                db.session.delete(like)
                
                # Remove points from both the liker and comment author
                current_user.points -= Config.LIKE_GIVEN_REWARD     # Remove points for giving a like
                comment.author.points -= Config.COMMENT_LIKE_REWARD  # Remove points from comment author
            else:
                # User is liking the comment
                like = Like(user_id=current_user.id, comment_id=comment_id)
                db.session.add(like)
                
                # Award points to both the liker and comment author
                current_user.points += Config.LIKE_GIVEN_REWARD     # Award points for giving a like
                comment.author.points += Config.COMMENT_LIKE_REWARD  # Award points to comment author
                
            db.session.commit()
            # Refresh the comment object to get the updated likes
            db.session.refresh(comment)
            return jsonify({
                'message': 'Comment like toggled successfully',
                'like_count': len(comment.likes)
            }), HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error toggling comment like: {str(e)}")
            return jsonify({'error': 'Failed to toggle comment like'}), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        # Guest like
        try:
            # For guest likes, we just increment the author's points
            comment.author.points += Config.COMMENT_LIKE_REWARD
            db.session.commit()
            return jsonify({
                'message': 'Guest like added successfully',
                'like_count': len(comment.likes) + 1  # Add 1 for the guest like (not stored in DB)
            }), HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding guest like: {str(e)}")
            return jsonify({'error': 'Failed to add guest like'}), HTTPStatus.INTERNAL_SERVER_ERROR

@posts.route('/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        return jsonify({'error': 'You are not authorized to delete this comment'}), HTTPStatus.FORBIDDEN
    
    try:
        # Calculate points to remove based on AI score and quality thresholds
        points_to_remove = 0
        if comment.ai_score > 0:  # Only remove points if the comment wasn't marked as spam
            if comment.ai_score <= Config.COMMENT_QUALITY_THRESHOLDS['low']:
                points_to_remove = Config.COMMENT_QUALITY_REWARDS['low']
            elif comment.ai_score <= Config.COMMENT_QUALITY_THRESHOLDS['medium']:
                points_to_remove = Config.COMMENT_QUALITY_REWARDS['medium']
            else:
                points_to_remove = Config.COMMENT_QUALITY_REWARDS['high']
        
        # Remove points from user
        if points_to_remove > 0:
            current_user.points = max(0, current_user.points - points_to_remove)
            logging.info(f"Removed {points_to_remove} points from user {current_user.id} for deleting comment {comment_id}")
        
        # Delete the comment
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({
            'message': 'Comment deleted successfully',
            'points_removed': points_to_remove
        }), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting comment: {str(e)}")
        return jsonify({'error': 'Failed to delete comment'}), HTTPStatus.INTERNAL_SERVER_ERROR
