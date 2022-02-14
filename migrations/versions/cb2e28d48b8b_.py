"""empty message

Revision ID: cb2e28d48b8b
Revises: e9df5182903a
Create Date: 2022-02-14 19:57:07.179865

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

import app
import app.extensions




# revision identifiers, used by Alembic.
revision = 'cb2e28d48b8b'
down_revision = 'e9df5182903a'


def upgrade():
    """
    Upgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('collaboration', schema=None) as batch_op:
        batch_op.add_column(sa.Column('init_req_notification_guuid', app.extensions.GUID(), nullable=True))
        batch_op.add_column(sa.Column('edit_req_notification_guuid', app.extensions.GUID(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_collaboration_edit_req_notification_guuid_notification'), 'notification', ['edit_req_notification_guuid'], ['guid'])
        batch_op.create_foreign_key(batch_op.f('fk_collaboration_init_req_notification_guuid_notification'), 'notification', ['init_req_notification_guuid'], ['guid'])

    # ### end Alembic commands ###


def downgrade():
    """
    Downgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('collaboration', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_collaboration_init_req_notification_guuid_notification'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_collaboration_edit_req_notification_guuid_notification'), type_='foreignkey')
        batch_op.drop_column('edit_req_notification_guuid')
        batch_op.drop_column('init_req_notification_guuid')

    # ### end Alembic commands ###
