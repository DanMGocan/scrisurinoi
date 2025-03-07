"""Add ai_feedback column to Comment model

Revision ID: add_ai_feedback_column
Revises: 
Create Date: 2025-03-07 13:24:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_ai_feedback_column'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('comment', sa.Column('ai_feedback', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('comment', 'ai_feedback')
