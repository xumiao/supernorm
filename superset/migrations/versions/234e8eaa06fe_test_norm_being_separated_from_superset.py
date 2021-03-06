"""test_norm_being_separated_from_superset

Revision ID: 234e8eaa06fe
Revises: e81e8fca3fb1
Create Date: 2018-11-23 03:59:52.934920

"""

# revision identifiers, used by Alembic.
revision = '234e8eaa06fe'
down_revision = 'e81e8fca3fb1'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('namespace', sa.String(length=1024), nullable=True),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('max_ver', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_constraint('lambdas_created_by_fk_fkey', 'lambdas', type_='foreignkey')
    op.drop_constraint('lambdas_changed_by_fk_fkey', 'lambdas', type_='foreignkey')
    op.drop_column('lambdas', 'created_on')
    op.drop_column('lambdas', 'changed_on')
    op.drop_column('lambdas', 'created_by_fk')
    op.drop_column('lambdas', 'changed_by_fk')
    op.drop_column('variables', 'as_input')
    op.drop_column('variables', 'as_output')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('variables', sa.Column('as_output', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('variables', sa.Column('as_input', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('lambdas', sa.Column('changed_by_fk', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('lambdas', sa.Column('created_by_fk', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('lambdas', sa.Column('changed_on', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('lambdas', sa.Column('created_on', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.create_foreign_key('lambdas_changed_by_fk_fkey', 'lambdas', 'ab_user', ['changed_by_fk'], ['id'])
    op.create_foreign_key('lambdas_created_by_fk_fkey', 'lambdas', 'ab_user', ['created_by_fk'], ['id'])
    op.create_table('squad_questions_train',
    sa.Column('Unnamed: 0', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('question', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('answer_text', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('answer_start', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('paragraph', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('is_impossible', sa.BOOLEAN(), autoincrement=False, nullable=True)
    )
    op.drop_table('versions')
    # ### end Alembic commands ###
