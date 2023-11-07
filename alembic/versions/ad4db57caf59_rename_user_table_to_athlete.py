"""rename user table to athlete

Revision ID: ad4db57caf59
Revises: 63701dba84d9
Create Date: 2023-11-06 17:32:02.390791

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ad4db57caf59'
down_revision = '63701dba84d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('workout_log_user_id_fkey', 'workout_log', type_='foreignkey')
    op.drop_constraint('feedback_user_id_fkey', 'feedback', type_='foreignkey')

    # rename table
    op.rename_table('user', 'athlete')

    # recreate foreing key pointing to new table name
    op.create_foreign_key(
        'workout_log_user_id_fkey', 
        'workout_log', 
        'athlete', 
        ['user_id'], 
        ['user_id']
    )

    op.create_foreign_key(
        'feedback_user_id_fkey', 
        'feedback', 
        'athlete', 
        ['user_id'], 
        ['user_id']
    )


def downgrade():
    # Drop the recreated foreign key constraints
    op.drop_constraint('workout_log_user_id_fkey', 'workout_log', type_='foreignkey')
    op.drop_constraint('feedback_user_id_fkey', 'feedback', type_='foreignkey')
    
    # Rename 'athlete' table back to 'user'
    op.rename_table('athlete', 'user')

    # Recreate the original foreign key constraint on 'workout_log'
    op.create_foreign_key(
        'workout_log_user_id_fkey', 
        'workout_log', 
        'user', 
        ['user_id'], 
        ['user_id']
    )

    op.create_foreign_key(
        'feedback_user_id_fkey', 
        'feedback', 
        'user', 
        ['user_id'], 
        ['user_id']
    )
