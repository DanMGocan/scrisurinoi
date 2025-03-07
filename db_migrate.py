from flask import Flask
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from models import db, User, Post, Comment, Like, UserActivity

app = Flask(__name__)
app.config.from_object('config.Config')

db.init_app(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
