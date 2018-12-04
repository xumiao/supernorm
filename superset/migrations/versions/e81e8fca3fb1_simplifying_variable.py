"""simplifying variable

Revision ID: e81e8fca3fb1
Revises: e140fc9266a0
Create Date: 2018-09-30 01:08:07.842277

"""

# revision identifiers, used by Alembic.
revision = 'e81e8fca3fb1'
down_revision = 'e140fc9266a0'

from alembic import op
import sqlalchemy as sa

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('variables', 'fullname')
    op.drop_column('variables', 'attribute')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('variables', sa.Column('attribute', sa.VARCHAR(length=256), autoincrement=False, nullable=True))
    op.add_column('variables', sa.Column('fullname', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    # ### end Alembic commands ###