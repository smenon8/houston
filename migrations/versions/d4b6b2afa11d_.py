"""empty message

Revision ID: d4b6b2afa11d
Revises: b823ccfc2d9b
Create Date: 2021-08-13 23:35:11.947441

"""

# revision identifiers, used by Alembic.
revision = 'd4b6b2afa11d'
down_revision = 'b823ccfc2d9b'

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

import app
import app.extensions



def upgrade():
    """
    Upgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('individual', schema=None) as batch_op:
        batch_op.add_column(sa.Column('featured_asset_guid', app.extensions.GUID(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    """
    Downgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('individual', schema=None) as batch_op:
        batch_op.drop_column('featured_asset_guid')

    # ### end Alembic commands ###
