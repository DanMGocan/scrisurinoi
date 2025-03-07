"""Add bio column to user table

Revision ID: add_bio_column
Revises: add_ai_feedback_column
Create Date: 2025-03-07 17:12:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_bio_column'
down_revision = 'add_ai_feedback_column'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('bio', sa.String(length=500), nullable=True))


def downgrade():
    op.drop_column('user', 'bio')
