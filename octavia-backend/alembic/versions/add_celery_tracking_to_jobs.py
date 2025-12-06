"""Add Celery tracking columns to jobs table

Revision ID: add_celery_tracking
Revises: a41a96424b43
Create Date: 2025-01-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_celery_tracking'
down_revision = 'a41a96424b43'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add celery_task_id column to track async task ID
    op.add_column('jobs', sa.Column('celery_task_id', sa.String(255), nullable=True))
    
    # Add credit_cost column to store the credit cost calculated at queue time
    op.add_column('jobs', sa.Column('credit_cost', sa.String(36), nullable=True))


def downgrade() -> None:
    # Remove the columns
    op.drop_column('jobs', 'credit_cost')
    op.drop_column('jobs', 'celery_task_id')
