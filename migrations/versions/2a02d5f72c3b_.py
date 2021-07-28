"""empty message

Revision ID: 2a02d5f72c3b
Revises: 628399bcec88
Create Date: 2021-07-26 13:37:11.516001

"""

# revision identifiers, used by Alembic.
revision = '2a02d5f72c3b'
down_revision = '628399bcec88'

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

import app
import app.extensions

from sqlalchemy.dialects import postgresql

def upgrade():
    """
    Upgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('asset_group', schema=None) as batch_op:
        batch_op.alter_column('config',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    """
    Downgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('asset_group', schema=None) as batch_op:
        batch_op.alter_column('config',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               nullable=True)

    # ### end Alembic commands ###
