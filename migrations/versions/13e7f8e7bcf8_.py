"""empty message

Revision ID: 13e7f8e7bcf8
Revises: a6b1cfd945f2
Create Date: 2021-05-14 23:00:10.459326

"""

# revision identifiers, used by Alembic.
revision = '13e7f8e7bcf8'
down_revision = 'a6b1cfd945f2'

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
    op.create_table('keyword',
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('updated', sa.DateTime(), nullable=False),
    sa.Column('viewed', sa.DateTime(), nullable=False),
    sa.Column('guid', app.extensions.GUID(), nullable=False),
    sa.Column('value', sa.String(), nullable=False),
    sa.Column('source', sa.Enum('user', 'wbia', name='keywordsource'), nullable=False),
    sa.PrimaryKeyConstraint('guid', name=op.f('pk_keyword')),
    sa.UniqueConstraint('value'),
    sa.UniqueConstraint('value', name=op.f('uq_keyword_value'))
    )
    with op.batch_alter_table('keyword', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_keyword_source'), ['source'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    """
    Downgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('keyword', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_keyword_source'))

    op.drop_table('keyword')

    # Remove the enum created as part of the upgrade above
    sa.Enum(name='keywordsource').drop(op.get_bind(), checkfirst=False)

    # ### end Alembic commands ###