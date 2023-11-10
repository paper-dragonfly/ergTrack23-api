"""Add last_post column to AthleteTable

Revision ID: 5d227bf5e46f
Revises: ad4db57caf59
Create Date: 2023-11-09 20:04:12.610871

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d227bf5e46f'
down_revision = 'ad4db57caf59'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('athlete', sa.Column('last_post', sa.Date, nullable=True))


def downgrade() -> None:
    op.drop_column('athlete', 'last_post')
