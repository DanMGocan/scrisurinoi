# Deploying Your Literary Community Flask App to Google Cloud

This guide will walk you through the process of deploying your Flask application to Google Cloud Platform (GCP). There are multiple ways to deploy a Flask application on GCP, but we'll focus on two popular options: Google App Engine and Google Cloud Run.

## Prerequisites

1. A Google Cloud account (create one at [cloud.google.com](https://cloud.google.com) if you don't have one)
2. Google Cloud SDK installed on your local machine ([Installation Guide](https://cloud.google.com/sdk/docs/install))
3. Git (for version control)

## Step 1: Prepare Your Application for Deployment

### 1.1 Create an app.yaml file for App Engine

Create a file named `app.yaml` in the root directory of your project:

```yaml
runtime: python310  # Use Python 3.10 runtime

instance_class: F2  # Choose an instance class based on your needs

env_variables:
  SECRET_KEY: "your-secret-key-here"  # Replace with a secure key
  # Don't include API keys here, use Secret Manager instead

entrypoint: gunicorn -b :$PORT app:app  # Use the app factory pattern

handlers:
- url: /static
  static_dir: static
  secure: always

- url: /.*
  script: auto
  secure: always
```

### 1.2 Create a Dockerfile for Cloud Run

Create a file named `Dockerfile` in the root directory of your project:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 app:app
```

### 1.3 Update Your Database Configuration

Since SQLite is not suitable for production in cloud environments, you should modify your app.py to use Cloud SQL (PostgreSQL or MySQL) in production:

```python
# In app.py, modify the database configuration
if os.environ.get('GAE_ENV', '').startswith('standard'):
    # Running on App Engine, use Cloud SQL
    db_user = os.environ.get('DB_USER')
    db_pass = os.environ.get('DB_PASS')
    db_name = os.environ.get('DB_NAME')
    db_socket_dir = os.environ.get('DB_SOCKET_DIR', '/cloudsql')
    cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f'postgresql+psycopg2://{db_user}:{db_pass}@/{db_name}'
        f'?host={db_socket_dir}/{cloud_sql_connection_name}'
    )
else:
    # Local development, use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///literary_app.db'
```

### 1.4 Create a .gcloudignore file

Create a `.gcloudignore` file to specify files that should not be uploaded to Google Cloud:

```
.git
.gitignore
.gcloudignore
__pycache__/
*.py[cod]
*$py.class
venv/
env/
ENV/
instance/
*.db
*.sqlite
*.log
```

## Step 2: Set Up Google Cloud Project

### 2.1 Create a New Project

```bash
gcloud projects create [PROJECT_ID] --name="Literary Community App"
```

### 2.2 Set the Active Project

```bash
gcloud config set project [PROJECT_ID]
```

### 2.3 Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable appengine.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

## Step 3: Set Up Cloud SQL (Optional but Recommended)

### 3.1 Create a PostgreSQL Instance

```bash
gcloud sql instances create literary-db \
  --database-version=POSTGRES_13 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=[YOUR_PASSWORD]
```

### 3.2 Create a Database

```bash
gcloud sql databases create literary_app --instance=literary-db
```

### 3.3 Create a User

```bash
gcloud sql users create literary-user \
  --instance=literary-db \
  --password=[USER_PASSWORD]
```

## Step 4: Store Secrets in Secret Manager

### 4.1 Create Secrets

```bash
echo -n "your-secret-key-here" | gcloud secrets create flask-secret-key --data-file=-
echo -n "[YOUR_ANTHROPIC_API_KEY]" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "[YOUR_OPENAI_API_KEY]" | gcloud secrets create openai-api-key --data-file=-
echo -n "[YOUR_DB_PASSWORD]" | gcloud secrets create db-password --data-file=-
```

### 4.2 Grant Access to the App

```bash
# For App Engine
gcloud secrets add-iam-policy-binding flask-secret-key \
  --member="serviceAccount:[PROJECT_ID]@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# For Cloud Run
gcloud secrets add-iam-policy-binding flask-secret-key \
  --member="serviceAccount:[PROJECT_ID]-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Step 5: Deploy Your Application

### Option A: Deploy to App Engine

```bash
gcloud app deploy app.yaml
```

### Option B: Deploy to Cloud Run

```bash
# Build the container
gcloud builds submit --tag gcr.io/[PROJECT_ID]/literary-app

# Deploy to Cloud Run
gcloud run deploy literary-app \
  --image gcr.io/[PROJECT_ID]/literary-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="CLOUD_SQL_CONNECTION_NAME=[PROJECT_ID]:[REGION]:literary-db" \
  --set-env-vars="DB_USER=literary-user" \
  --set-env-vars="DB_NAME=literary_app" \
  --set-secrets="SECRET_KEY=flask-secret-key:latest" \
  --set-secrets="DB_PASS=db-password:latest" \
  --set-secrets="ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest"
```

## Step 6: Set Up Database Migrations

After deploying, you'll need to run migrations to set up your database schema:

### For App Engine

```bash
# Open a Cloud Shell session
gcloud app instances ssh --service=default --version=[VERSION]

# Run migrations
cd /app
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

### For Cloud Run

```bash
# Create a one-time job to run migrations
gcloud run jobs create db-migrate \
  --image gcr.io/[PROJECT_ID]/literary-app \
  --set-env-vars="CLOUD_SQL_CONNECTION_NAME=[PROJECT_ID]:[REGION]:literary-db" \
  --set-env-vars="DB_USER=literary-user" \
  --set-env-vars="DB_NAME=literary_app" \
  --set-secrets="DB_PASS=db-password:latest" \
  --command="python" \
  --args="-c","from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"

# Execute the job
gcloud run jobs execute db-migrate
```

## Step 7: Set Up Continuous Deployment (Optional)

### 7.1 Connect Your GitHub Repository

1. Go to the Cloud Build section in the Google Cloud Console
2. Click on "Triggers"
3. Click "Connect Repository"
4. Follow the steps to connect your GitHub repository

### 7.2 Create a Build Trigger

1. Click "Create Trigger"
2. Configure the trigger to build and deploy on pushes to your main branch
3. Use the following build configuration (cloudbuild.yaml):

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/literary-app', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/literary-app']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
    - 'run'
    - 'deploy'
    - 'literary-app'
    - '--image'
    - 'gcr.io/$PROJECT_ID/literary-app'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'
    - '--set-env-vars'
    - 'CLOUD_SQL_CONNECTION_NAME=$PROJECT_ID:us-central1:literary-db'
    - '--set-env-vars'
    - 'DB_USER=literary-user'
    - '--set-env-vars'
    - 'DB_NAME=literary_app'
    - '--set-secrets'
    - 'SECRET_KEY=flask-secret-key:latest'
    - '--set-secrets'
    - 'DB_PASS=db-password:latest'
    - '--set-secrets'
    - 'ANTHROPIC_API_KEY=anthropic-api-key:latest'
    - '--set-secrets'
    - 'OPENAI_API_KEY=openai-api-key:latest'

images:
  - 'gcr.io/$PROJECT_ID/literary-app'
```

## Step 8: Set Up a Custom Domain (Optional)

### 8.1 Verify Domain Ownership

1. Go to the Google Cloud Console
2. Navigate to App Engine or Cloud Run settings
3. Click on "Custom Domains"
4. Follow the steps to verify your domain ownership

### 8.2 Map Your Domain

1. After verification, map your domain to your App Engine or Cloud Run service
2. Configure SSL certificates (Google can provision these automatically)

## Troubleshooting

### Viewing Logs

```bash
# App Engine logs
gcloud app logs tail

# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=literary-app" --limit=50
```

### Checking Application Status

```bash
# App Engine status
gcloud app describe

# Cloud Run status
gcloud run services describe literary-app --region=us-central1
```

## Cost Management

- App Engine and Cloud Run both offer free tiers
- Set up budget alerts to avoid unexpected charges
- Consider using Cloud SQL's smallest instance (db-f1-micro) to minimize costs
- Use Cloud Run's scale-to-zero feature to avoid paying for idle instances

## Security Considerations

- Never store API keys or secrets directly in your code or in app.yaml
- Always use Secret Manager for sensitive information
- Set up Identity and Access Management (IAM) properly
- Consider implementing Cloud Armor for additional security

## Next Steps

- Set up monitoring and alerting with Cloud Monitoring
- Implement Cloud CDN for static assets
- Configure Cloud Storage for user uploads
- Set up regular database backups
