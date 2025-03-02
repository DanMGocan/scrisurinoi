import os
from app import create_app, db
from models import User, UserActivity
from werkzeug.security import generate_password_hash

def reset_database():
    try:
        with open('reset_db_output.txt', 'w') as f:
            f.write("Running reset_database.py...\n")
        app = create_app()
        with app.app_context():
            with open('reset_db_output.txt', 'a') as f:
                f.write(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}\n")

            with open('reset_db_output.txt', 'a') as f:
                f.write("Dropping and creating all tables...\n")
            db.drop_all()
            db.create_all()
            with open('reset_db_output.txt', 'a') as f:
                f.write("Tables dropped and created.\n")

            # Add a test user
            with open('reset_db_output.txt', 'a') as f:
                f.write("Adding test user...\n")
            hashed_password = generate_password_hash('123')
            test_user = User(email='sad@sad.com', name='sad@sad.com', password_hash=hashed_password, points=1000)
            db.session.add(test_user)
            db.session.commit()
            with open('reset_db_output.txt', 'a') as f:
                f.write("Test user added.\n")

            # Query the database for the test user
            test_user = User.query.filter_by(email='sad@sad.com').first()
            if test_user:
                with open('reset_db_output.txt', 'a') as f:
                    f.write(f'Test user found: {test_user.email}\n')
            else:
                with open('reset_db_output.txt', 'a') as f:
                    f.write('Test user not found!\n')

        with open('reset_db_output.txt', 'a') as f:
            f.write('Database reset and test user added successfully!\n')

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        with open('reset_db_output.txt', 'w') as f:
            f.write(f"An error occurred: {str(e)}\n")

if __name__ == '__main__':
    reset_database()
