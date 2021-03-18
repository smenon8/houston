"""Rename User profile_asset

Revision ID: b6169129db5e
Revises: 60224b2588fd
Create Date: 2021-03-12 23:16:37.670274

"""

# revision identifiers, used by Alembic.
revision = 'b6169129db5e'
down_revision = '757715188c2f'

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
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_fileupload_guid', app.extensions.GUID(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_user_profile_fileupload_guid_file_upload'), 'file_upload', ['profile_fileupload_guid'], ['guid'])
        batch_op.drop_column('profile_asset_guid')

    # ### end Alembic commands ###


def downgrade():
    """
    Downgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_asset_guid', postgresql.UUID(), autoincrement=False, nullable=True))
        batch_op.drop_constraint(batch_op.f('fk_user_profile_fileupload_guid_file_upload'), type_='foreignkey')
        batch_op.drop_column('profile_fileupload_guid')

    # ### end Alembic commands ###