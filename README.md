# Scrisuri Noi - Literary Community Platform

Scrisuri Noi ("New Writings") is a web platform for Romanian literature enthusiasts to share and discuss their literary works. The platform encourages quality feedback and community engagement through a points-based system.

## Project Overview

This platform serves as a community for Romanian literature writers that encourages feedback and interaction. It's a place for people to both teach and learn about their writing. The application is built with Flask and provides a space for users to:

- Share their literary works in various formats (poetry, prose, essays, etc.)
- Receive and give feedback on literary works
- Earn points through quality contributions
- Build a literary portfolio and community presence

## Features

### User Authentication
- Email/password registration and login
- User profiles with points tracking
- Google authentication integration

### Content Management
- Create and publish literary works in multiple formats:
  - Poetry
  - Prose
  - Essays
  - Theater
  - Letters
  - Journal entries
- Format-specific styling and presentation
- Rich text editing capabilities

### Community Interaction
- Comment on literary works
- AI-powered comment quality evaluation
- Like posts and comments
- Points-based reward system

### AI Integration
- Automatic evaluation of comment quality using OpenAI's GPT models
- Spam detection for comments
- Quality scoring based on emotional resonance, thoughtfulness, and authenticity

## Technologies Used

- **Backend**: Python, Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Flask-Login, Google OAuth
- **AI Integration**: OpenAI API (GPT-4o)
- **Styling**: Font Awesome, Google Fonts

## Points System Structure

The platform uses a points-based system to encourage quality contributions:

### Earning Points
- Receiving likes on posts
- Receiving likes on comments
- Writing high-quality comments (evaluated by AI)

### Spending Points
- Creating new posts (cost varies by post type)
- Additional costs for longer posts

### Quality Thresholds
Comments are evaluated by AI and scored from 0-100 based on:
- Emotional Resonance & Personal Connection (0-35 points)
- Thoughtfulness & Depth (0-35 points)
- Authenticity & Engagement (0-30 points)

## Installation and Setup

### Prerequisites
- Python 3.10+
- pip (Python package manager)
- Git

### Local Development Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd scrisurinoi
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Copy the example environment file and update it with your values:
   ```
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. Initialize the database:
   ```
   python reset_db.py
   ```

6. Run the application:
   ```
   python run_local.py
   ```

7. Access the application at `http://localhost:5000`

## Deployment to Google Cloud

This application can be deployed to Google Cloud Platform using either App Engine or Cloud Run. For detailed deployment instructions, see the [Google Cloud Deployment Guide](gcp_deployment_guide.md).

### Quick Deployment Steps

1. Install the Google Cloud SDK
2. Create a new Google Cloud project
3. Enable required APIs (Cloud Run, Cloud Build, Secret Manager, etc.)
4. Set up a Cloud SQL PostgreSQL database
5. Store secrets in Secret Manager
6. Deploy using one of the following methods:

#### App Engine Deployment
```bash
gcloud app deploy app.yaml
```

#### Cloud Run Deployment
```bash
# Build the container
gcloud builds submit --tag gcr.io/[PROJECT_ID]/literary-app

# Deploy to Cloud Run
gcloud run deploy literary-app --image gcr.io/[PROJECT_ID]/literary-app
```

For complete deployment instructions with all required parameters, refer to the [Google Cloud Deployment Guide](gcp_deployment_guide.md).

## Project Structure

- `app.py` - Main application entry point
- `models.py` - Database models
- `auth.py` - Authentication routes and logic
- `posts.py` - Post and comment handling
- `config.py` - Application configuration
- `templates/` - HTML templates
- `static/` - Static assets (CSS, JS, images)
- `instance/` - Instance-specific data (database)

## Contributing

Contributions to improve Scrisuri Noi are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for providing the AI evaluation capabilities
- Flask and its ecosystem for the web framework
- All contributors and users of the platform
