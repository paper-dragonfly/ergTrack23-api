"""added comment col to workout . table

Revision ID: 97b015525fea
Revises: 453a58e36300
Create Date: 2023-05-04 10:50:55.024682

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '97b015525fea'
down_revision = '453a58e36300'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('workout_log', sa.Column('comment', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('workout_log', 'comment')
    # ### end Alembic commands ###
