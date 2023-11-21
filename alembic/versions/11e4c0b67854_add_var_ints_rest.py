"""add var_ints_rest

Revision ID: 11e4c0b67854
Revises: 5d227bf5e46f
Create Date: 2023-11-20 15:39:06.328457

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



# revision identifiers, used by Alembic.
revision = '11e4c0b67854'
down_revision = '5d227bf5e46f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('workout_log', sa.Column('var_ints_rest', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('workout_log', 'var_ints_rest')
