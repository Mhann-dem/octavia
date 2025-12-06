"""Add job progress tracking columns

Revision ID: add_job_progress
Revises: add_celery_tracking
Create Date: 2025-01-10 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_job_progress'
down_revision = 'add_celery_tracking'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add phase column to track current execution phase
    op.add_column('jobs', sa.Column('phase', sa.Enum('pending', 'transcribing', 'translating', 'synthesizing', 'uploading', 'completed', 'failed', name='jobphase'), nullable=False, server_default='pending'))
    
    # Add progress_percentage column (0.0 to 100.0)
    op.add_column('jobs', sa.Column('progress_percentage', sa.Float(), nullable=False, server_default='0.0'))
    
    # Add current_step column for human-readable step description
    op.add_column('jobs', sa.Column('current_step', sa.String(), nullable=True))
    
    # Add started_at column to track when processing began
    op.add_column('jobs', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove the columns in reverse order
    op.drop_column('jobs', 'started_at')
    op.drop_column('jobs', 'current_step')
    op.drop_column('jobs', 'progress_percentage')
    op.drop_column('jobs', 'phase')
