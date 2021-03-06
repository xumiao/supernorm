"""adding unique constraint to lambda

Revision ID: 732ed9e22eb3
Revises: bc7ed65d68b8
Create Date: 2018-11-27 21:45:03.086319

"""

# revision identifiers, used by Alembic.
revision = '732ed9e22eb3'
down_revision = 'bc7ed65d68b8'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('unique_lambda', 'lambdas', ['namespace', 'name', 'version'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('unique_lambda', 'lambdas')
    # ### end Alembic commands ###
