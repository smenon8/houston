"""empty message

Revision ID: cd0bc2d4043a
Revises: 329c594dd8d7
Create Date: 2021-09-27 18:38:39.616025

"""

# revision identifiers, used by Alembic.
revision = 'cd0bc2d4043a'
down_revision = '329c594dd8d7'

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
    with op.batch_alter_table('annotation', schema=None) as batch_op:
        batch_op.add_column(sa.Column('content_guid', app.extensions.GUID(), nullable=True))
        batch_op.add_column(sa.Column('viewpoint', sa.String(length=255), nullable=True))

    # give values to existing annotation.viewpoint (so we can make nullable=False below)
    op.execute("UPDATE annotation SET viewpoint='unknown'")

    # and here we set nullable=False once we have values in
    with op.batch_alter_table('annotation', schema=None) as batch_op:
        batch_op.alter_column('viewpoint', existing_type=sa.VARCHAR, nullable=False)

    # ### end Alembic commands ###


def downgrade():
    """
    Downgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('annotation', schema=None) as batch_op:
        batch_op.drop_column('viewpoint')
        batch_op.drop_column('content_guid')

    # ### end Alembic commands ###
