"""empty message

Revision ID: 8c28b9a9dd59
Revises: cb2e28d48b8b
Create Date: 2022-02-15 17:39:49.031995

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

import app
import app.extensions

from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '8c28b9a9dd59'
down_revision = 'cb2e28d48b8b'


def upgrade():
    """
    Upgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('collaboration', schema=None) as batch_op:
        batch_op.add_column(sa.Column('init_req_notification_guid', app.extensions.GUID(), nullable=True))
        batch_op.add_column(sa.Column('edit_req_notification_guid', app.extensions.GUID(), nullable=True))
        batch_op.drop_constraint('fk_collaboration_init_req_notification_guuid_notification', type_='foreignkey')
        batch_op.drop_constraint('fk_collaboration_edit_req_notification_guuid_notification', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_collaboration_init_req_notification_guid_notification'), 'notification', ['init_req_notification_guid'], ['guid'])
        batch_op.create_foreign_key(batch_op.f('fk_collaboration_edit_req_notification_guid_notification'), 'notification', ['edit_req_notification_guid'], ['guid'])
        batch_op.drop_column('edit_req_notification_guuid')
        batch_op.drop_column('init_req_notification_guuid')

    # ### end Alembic commands ###


def downgrade():
    """
    Downgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('collaboration', schema=None) as batch_op:
        batch_op.add_column(sa.Column('init_req_notification_guuid', postgresql.UUID(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('edit_req_notification_guuid', postgresql.UUID(), autoincrement=False, nullable=True))
        batch_op.drop_constraint(batch_op.f('fk_collaboration_edit_req_notification_guid_notification'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_collaboration_init_req_notification_guid_notification'), type_='foreignkey')
        batch_op.create_foreign_key('fk_collaboration_edit_req_notification_guuid_notification', 'notification', ['edit_req_notification_guuid'], ['guid'])
        batch_op.create_foreign_key('fk_collaboration_init_req_notification_guuid_notification', 'notification', ['init_req_notification_guuid'], ['guid'])
        batch_op.drop_column('edit_req_notification_guid')
        batch_op.drop_column('init_req_notification_guid')

    # ### end Alembic commands ###
