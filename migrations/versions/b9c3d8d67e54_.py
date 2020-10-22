"""empty message

Revision ID: b9c3d8d67e54
Revises: 7d6530ba3fd6
Create Date: 2020-10-09 13:48:24.271564

"""

# revision identifiers, used by Alembic.
revision = 'b9c3d8d67e54'
down_revision = '7d6530ba3fd6'

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

import app
import app.extensions


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('magic_signiture', sa.String(), nullable=True))
        batch_op.execute('UPDATE asset SET magic_signiture = ""')
        batch_op.alter_column('magic_signiture', nullable=True)

    with op.batch_alter_table('submission', schema=None) as batch_op:
        batch_op.add_column(sa.Column('commit_houston_api_version', sa.String(), nullable=False))
        batch_op.add_column(sa.Column('commit_mime_whitelist_guid', app.extensions.GUID(), nullable=False))
        batch_op.create_index(batch_op.f('ix_submission_commit_houston_api_version'), ['commit_houston_api_version'], unique=False)
        batch_op.create_index(batch_op.f('ix_submission_commit_mime_whitelist_guid'), ['commit_mime_whitelist_guid'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('submission', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_submission_commit_mime_whitelist_guid'))
        batch_op.drop_index(batch_op.f('ix_submission_commit_houston_api_version'))
        batch_op.drop_column('commit_mime_whitelist_guid')
        batch_op.drop_column('commit_houston_api_version')

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('magic_signiture')

    # ### end Alembic commands ###
