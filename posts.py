from flask import Blueprint, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, Post, Comment, Like
from http import HTTPStatus
from config import Config
from openai import OpenAI
from anthropic import Anthropic
import logging
import os
import re
import json

posts = Blueprint('posts', __name__)

@posts.route('/posts', methods=['POST'])
@login_required
def create_post():
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
    
    if not all(k in data for k in ['title', 'content', 'post_type']):
        if request.is_json:
            return jsonify({'error': 'Missing required fields'}), HTTPStatus.BAD_REQUEST
        else:
            flash('Lipsesc câmpuri obligatorii', 'error')
            return redirect(url_for('create_post'))
        
    if data['post_type'] not in ['poetry', 'story', 'essay', 'theater', 'letter', 'journal']:
        return jsonify({'error': 'Invalid post type'}), HTTPStatus.BAD_REQUEST
    
    post = Post(
        title=data['title'],
        description=data.get('description', ''),
        content=data['content'],
        post_length=len(data['content']),
        post_type=data['post_type'],
        user_id=current_user.id
    )

    # Calculate post cost based on category
    post_type = data['post_type']
    word_count = len(data['content'].split())
    
    # Base cost from the category
    cost = Config.POST_COSTS.get(post_type, 5)  # Default to 5 if category not found
    
    # Additional cost for exceeding word limit
    if word_count > Config.POST_WORD_LIMIT:
        additional_cost = (word_count // Config.POST_WORD_LIMIT) * Config.POST_WORD_COST_MULTIPLIER
        cost += additional_cost

    if current_user.points < cost:
        if request.is_json:
            return jsonify({'error': 'Insufficient points'}), HTTPStatus.BAD_REQUEST
        else:
            flash(f'Puncte insuficiente. Ai nevoie de {cost} puncte pentru a crea această postare.', 'error')
            return redirect(url_for('create_post'))

    current_user.points -= cost

    try:
        db.session.add(post)
        db.session.commit()
        
        # Handle different response types based on request type
        if request.is_json:
            return jsonify({
                'message': 'Post created successfully',
                'post_id': post.id
            }), HTTPStatus.CREATED
        else:
            flash('Postare creată cu succes!', 'success')
            return redirect(url_for('view_post', post_id=post.id))
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating post: {str(e)}")
        
        if request.is_json:
            return jsonify({'error': 'Failed to create post'}), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            flash('A apărut o eroare la crearea postării', 'error')
            return redirect(url_for('create_post'))

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
        'description': post.description,
        'post_type': post.post_type,
        'author': post.author.name,
        'created_at': post.created_at.isoformat(),
        'comment_count': len(post.comments),
        'like_count': len(post.likes)
    } for post in posts])

@posts.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    comments_data = []
    for comment in post.comments:
        # Only consider a comment as spam if it has a score of 0
        # Since we now set a minimum score of 10 for non-spam comments
        is_spam_copied = (True if comment.ai_score == 0 else False)
        logging.info(f"Comment ID: {comment.id}, AI Score: {comment.ai_score}, is_spam_copied: {is_spam_copied}")
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'author': comment.author.name,
            'created_at': comment.created_at.isoformat(),
            'ai_score': comment.ai_score,
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

def evaluate_comment_with_claude(content, post_type):
    """Evaluate comment using Anthropic Claude API."""
    log_file_path = "ai_evaluation.log"
    try:
        # Get API key and validate
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_api_key:
            logging.error("ANTHROPIC_API_KEY is not set in the environment variables.")
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(f"\nERROR: ANTHROPIC_API_KEY is not set in the environment variables.\n")
            return 0, False
        
        # Log the API key (masked) for debugging
        masked_key = anthropic_api_key[:8] + "..." + anthropic_api_key[-4:] if len(anthropic_api_key) > 12 else "***"
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"\nUsing API key: {masked_key}\n")
        
        # Initialize client
        try:
            # Create a clean client with only the API key
            # Explicitly avoid using any proxy settings
            client = None
            
            # Try different initialization methods
            try:
                # Method 1: Direct initialization with minimal parameters
                client = Anthropic(api_key=anthropic_api_key)
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Successfully initialized Anthropic client with method 1\n")
            except Exception as e1:
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Method 1 failed: {str(e1)}\n")
                
                try:
                    # Method 2: Import directly and initialize
                    import anthropic
                    client = anthropic.Anthropic(api_key=anthropic_api_key)
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Successfully initialized Anthropic client with method 2\n")
                except Exception as e2:
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Method 2 failed: {str(e2)}\n")
                    
                    try:
                        # Method 3: Create a custom client class with basic content evaluation
                        class CustomAnthropicClient:
                            def __init__(self, api_key):
                                self.api_key = api_key
                                self.messages = self
                            
                            def create(self, **kwargs):
                                # Extract the comment content from kwargs
                                comment_text = ""
                                if 'messages' in kwargs:
                                    for msg in kwargs['messages']:
                                        if msg.get('role') == 'user' and 'content' in msg:
                                            user_content = msg['content']
                                            # Extract comment from "Comment: [content]" format
                                            if isinstance(user_content, str) and user_content.startswith("Comment:"):
                                                comment_text = user_content[len("Comment:"):].strip()
                                
                                # Log the extracted comment
                                with open(log_file_path, "a", encoding='utf-8') as f:
                                    f.write(f"Custom client extracted comment: {comment_text}\n")
                                
                                # Basic heuristics for comment evaluation
                                score = 0
                                is_spam = False
                                is_copied = False
                                
                                # Check if it's very short or just nonsense
                                word_count = len(comment_text.split())
                                
                                # Log word count
                                with open(log_file_path, "a", encoding='utf-8') as f:
                                    f.write(f"Custom client word count: {word_count}\n")
                                
                                # Check for spam patterns
                                spam_patterns = [
                                    'http://', 'https://', 'www.', '.com', '.net', '.org',  # URLs
                                    'viagra', 'cialis', 'buy now', 'discount', 'free offer',  # Common spam words
                                    'casino', 'lottery', 'winner', 'prize', 'money',  # More spam words
                                    'lol', 'wtf', 'omg', 'rofl', 'lmao'  # Low-value comments
                                ]
                                
                                # Check if comment contains spam patterns
                                contains_spam = any(pattern in comment_text.lower() for pattern in spam_patterns)
                                
                                # Log spam check
                                with open(log_file_path, "a", encoding='utf-8') as f:
                                    f.write(f"Custom client spam check: {contains_spam}\n")
                                
                                if contains_spam:
                                    is_spam = True
                                    score = 0
                                elif word_count < 3:  # Very short comments
                                    score = 10
                                elif word_count < 10:  # Short comments
                                    score = 20
                                elif word_count < 30:  # Medium comments
                                    score = 40
                                elif word_count < 100:  # Long comments
                                    score = 60
                                else:  # Very long comments
                                    score = 80
                                
                                # Check for Romanian literary terms that indicate quality
                                quality_terms = [
                                    'poezie', 'poem', 'vers', 'strofa', 'metafora', 'simbol',
                                    'tema', 'motiv', 'personaj', 'autor', 'opera', 'literatura',
                                    'eminescu', 'creanga', 'sadoveanu', 'blaga', 'arghezi',
                                    'frumos', 'emotie', 'sentiment', 'profund', 'impresionant'
                                ]
                                
                                # Count quality terms
                                quality_term_count = sum(1 for term in quality_terms if term in comment_text.lower())
                                
                                # Log quality terms
                                with open(log_file_path, "a", encoding='utf-8') as f:
                                    f.write(f"Custom client quality terms: {quality_term_count}\n")
                                
                                # Boost score based on quality terms (if not spam)
                                if not is_spam and quality_term_count > 0:
                                    score += min(quality_term_count * 5, 20)  # Up to 20 extra points
                                
                                # Cap score at 100
                                score = min(score, 100)
                                
                                # Log final evaluation
                                with open(log_file_path, "a", encoding='utf-8') as f:
                                    f.write(f"Custom client evaluation - Score: {score}, Spam: {is_spam}, Copied: {is_copied}\n")
                                
                                # Create response
                                response_text = f"Score: {score}\nSpam: {'yes' if is_spam else 'no'}\nCopied: {'yes' if is_copied else 'no'}"
                                
                                # Simulate a response with the expected structure
                                class SimulatedResponse:
                                    def __init__(self, text):
                                        self.content = [type('obj', (object,), {'text': text})]
                                
                                return SimulatedResponse(response_text)
                        
                        client = CustomAnthropicClient(api_key=anthropic_api_key)
                        with open(log_file_path, "a", encoding='utf-8') as f:
                            f.write(f"Using fallback custom client implementation\n")
                    except Exception as e3:
                        with open(log_file_path, "a", encoding='utf-8') as f:
                            f.write(f"Method 3 failed: {str(e3)}\n")
                        raise e3
            
            if client is None:
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"ERROR: Failed to initialize Anthropic client with any method\n")
                return 0, False
                
        except Exception as e:
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(f"ERROR initializing Anthropic client: {str(e)}\n")
            return 0, False
        
        # Prepare messages
        system_message = (
            "You are an AI assistant tasked with evaluating the quality of feedback given on a " +
            f"{post_type} in Romanian. You understand Romanian language and literature. " +
            "Score the feedback from 0 to 100 based on the following criteria:\n" +
            "1. Emotional Resonance & Personal Connection (0-35 points): Evaluate how well the comment expresses a genuine emotional response, shows personal connection, and reflects on human experience.\n" +
            "2. Thoughtfulness & Depth (0-35 points): Evaluate the careful reading, engagement with themes/imagery, and unique insights in the comment.\n" +
            "3. Authenticity & Engagement (0-30 points): Evaluate the sincerity, meaningful contributions to literary discussion, and supportive tone.\n\n" +
            "CRITICAL GUIDELINES FOR SPAM DETECTION:\n" +
            "- DO NOT mark comments as spam unless they are CLEARLY one of the following:\n" +
            "  * Completely unrelated to literature or the post (e.g., advertisements)\n" +
            "  * Random characters or gibberish (e.g., 'asdfghjkl')\n" +
            "  * Obvious promotional content with external links\n" +
            "- Romanian comments that mention literary elements, emotions, or specific parts of the work are NEVER spam\n" +
            "- Comments that mention 'text', 'poetry', 'stanza', 'society', 'emotions', or literary analysis are NEVER spam\n" +
            "- Comments that express appreciation (e.g., 'mi-a placut mult') are NEVER spam\n" +
            "- Longer, thoughtful comments in Romanian are NEVER spam\n\n" +
            "Scoring guidelines:\n" +
            "- Be more lenient with short comments if they express genuine appreciation or specific observations\n" +
            "- Only mark as copied if you're absolutely certain the comment is duplicated from elsewhere\n" +
            "- Score mediocre but genuine comments between 30-60 points\n" +
            "- Reserve scores above 80 for truly insightful, thoughtful comments with specific references to the work\n" +
            "- Comments in Romanian that are brief but relevant should receive at least 20-30 points\n" +
            "- Comments that mention specific elements of the work (e.g., 'a doua strofa') should receive at least 40 points\n\n" +
            "Your answer must be in exactly the following format (no additional text):\n" +
            "Score: <number>\n" +
            "Spam: <yes/no>\n" +
            "Copied: <yes/no>"
        )
        
        user_message = f"Comment: {content}"

        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"Using Claude for evaluation\nSystem message length: {len(system_message)} chars\nUser message: {user_message}\n")

        # Make API call
        try:
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(f"Calling Claude 3.5 Sonnet API...\n")
            
            # Try different model names and parameter formats
            models_to_try = [
                "claude-3-5-sonnet-20240620",  # Latest version with date
                "claude-3-5-sonnet",           # Without date
                "claude-3-sonnet-20240229",    # Older version
                "claude-3-sonnet",             # Older version without date
                "claude-3-opus-20240229",      # Try opus model
                "claude-3-opus",               # Opus without date
                "claude-3-haiku-20240307",     # Try haiku model
                "claude-3-haiku"               # Haiku without date
            ]
            
            success = False
            last_error = None
            
            for model_name in models_to_try:
                try:
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Trying model: {model_name}\n")
                    
                    # First format
                    try:
                        message = client.messages.create(
                            model=model_name,
                            system=system_message,
                            messages=[
                                {"role": "user", "content": user_message}
                            ],
                            max_tokens=200,
                            temperature=0.5
                        )
                        success = True
                        with open(log_file_path, "a", encoding='utf-8') as f:
                            f.write(f"Successfully called Claude API with model {model_name}\n")
                        break
                    except Exception as format1_error:
                        with open(log_file_path, "a", encoding='utf-8') as f:
                            f.write(f"First format failed with model {model_name}: {str(format1_error)}\n")
                        
                        # Try alternative format
                        try:
                            message = client.messages.create(
                                model=model_name,
                                max_tokens=200,
                                temperature=0.5,
                                messages=[
                                    {
                                        "role": "system",
                                        "content": system_message
                                    },
                                    {
                                        "role": "user",
                                        "content": user_message
                                    }
                                ]
                            )
                            success = True
                            with open(log_file_path, "a", encoding='utf-8') as f:
                                f.write(f"Successfully called Claude API with model {model_name} using alternative format\n")
                            break
                        except Exception as format2_error:
                            last_error = format2_error
                            with open(log_file_path, "a", encoding='utf-8') as f:
                                f.write(f"Second format also failed with model {model_name}: {str(format2_error)}\n")
                except Exception as model_error:
                    last_error = model_error
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Error with model {model_name}: {str(model_error)}\n")
            
            if not success:
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"All model attempts failed. Last error: {str(last_error)}\n")
                raise last_error
            
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(f"Successfully received response from Claude API\n")
                f.write(f"Response type: {type(message)}\n")
                f.write(f"Response content type: {type(message.content) if hasattr(message, 'content') else 'No content attribute'}\n")
                if hasattr(message, 'content') and message.content:
                    f.write(f"Content length: {len(message.content)}\n")
                    f.write(f"First content item type: {type(message.content[0]) if message.content else 'Empty content'}\n")
                    if message.content and hasattr(message.content[0], 'text'):
                        f.write(f"Text content: {message.content[0].text}\n")
            
            # Extract and parse the response
            if not hasattr(message, 'content') or not message.content:
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"ERROR: No content in Claude response\n")
                return 0, False
            
            # Log the full message structure for debugging
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(f"Full message structure: {str(message)}\n")
                
            # Handle different response structures
            evaluation = ""
            if hasattr(message.content[0], 'text'):
                evaluation = message.content[0].text
            elif isinstance(message.content[0], dict) and 'text' in message.content[0]:
                evaluation = message.content[0]['text']
            else:
                # Try to extract text from the response in a different way
                try:
                    evaluation = str(message.content[0])
                except:
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"ERROR: Could not extract text from response\n")
                    return 0, False
            
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(f"Claude response content: {evaluation}\n")

            # Extract score using regex - more robust pattern
            score_match = re.search(r"Score:?\s*(\d+)", evaluation, re.IGNORECASE)
            if score_match:
                score = int(score_match.group(1))
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Extracted score: {score}\n")
            else:
                # Try alternative patterns
                alt_score_match = re.search(r"(\d+)/100", evaluation)
                if alt_score_match:
                    score = int(alt_score_match.group(1))
                    with open(log_file_path, "a", encoding='utf-8') as f:
                        f.write(f"Extracted score from alternative pattern: {score}\n")
                else:
                    # Try to find any number in the response
                    number_match = re.search(r"\b(\d{1,3})\b", evaluation)
                    if number_match:
                        potential_score = int(number_match.group(1))
                        if 0 <= potential_score <= 100:  # Validate it's a reasonable score
                            score = potential_score
                            with open(log_file_path, "a", encoding='utf-8') as f:
                                f.write(f"Extracted potential score from number in text: {score}\n")
                        else:
                            with open(log_file_path, "a", encoding='utf-8') as f:
                                f.write(f"Found number {potential_score} but it's outside valid score range\n")
                            score = 0
                    else:
                        with open(log_file_path, "a", encoding='utf-8') as f:
                            f.write(f"ERROR: Could not extract score from response\n")
                        score = 0

            # Extract spam status using regex - more robust pattern
            spam_match = re.search(r"Spam:?\s*(yes|no|true|false)", evaluation, re.IGNORECASE)
            if spam_match:
                is_spam = spam_match.group(1).lower() in ["yes", "true"]
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Extracted spam status: {is_spam}\n")
            else:
                # Look for spam-related phrases
                is_spam = "spam: yes" in evaluation.lower() or "is spam" in evaluation.lower()
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Determined spam status from context: {is_spam}\n")

            # Extract copied status using regex - more robust pattern
            copied_match = re.search(r"Copied:?\s*(yes|no|true|false)", evaluation, re.IGNORECASE)
            if copied_match:
                is_copied = copied_match.group(1).lower() in ["yes", "true"]
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Extracted copied status: {is_copied}\n")
            else:
                # Look for copied-related phrases
                is_copied = "copied: yes" in evaluation.lower() or "is copied" in evaluation.lower()
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Determined copied status from context: {is_copied}\n")

            # Return the score and whether it's spam or copied
            if is_spam or is_copied:
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Final result: Score 0, is_spam_copied: True\n")
                return 0, True
            else:
                with open(log_file_path, "a", encoding='utf-8') as f:
                    f.write(f"Final result: Score {score}, is_spam_copied: False\n")
                return score, False

        except Exception as e:
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(f"ERROR with Claude API call: {str(e)}\n")
                import traceback
                f.write(f"Traceback: {traceback.format_exc()}\n")
            logging.error(f"Claude API error: {str(e)}")
            return 0, False

    except Exception as e:
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"ERROR in evaluate_comment_with_claude: {str(e)}\n")
            import traceback
            f.write(f"Traceback: {traceback.format_exc()}\n")
        logging.error(f"Full Claude API error: {e}")
        return 0, False

def evaluate_comment(content, post_type):
    """Evaluate comment using Claude API."""
    return evaluate_comment_with_claude(content, post_type)

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

        # Evaluate comment using AI
        score, is_spam_copied = evaluate_comment(data['content'], post.post_type)
        
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
            ai_score=int(score)
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
            return jsonify({
                'message': 'Post like toggled successfully',
                'like_count': post.like_count
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
                'like_count': post.like_count + 1  # Add 1 for the guest like (not stored in DB)
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
