# -*- coding: utf-8 -*-
"""empty message

Revision ID: ed7b9eb99d21
Revises: 272bc58baeff
Create Date: 2022-04-26 09:54:19.649695

"""
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'ed7b9eb99d21'
down_revision = '272bc58baeff'


def upgrade():
    """
    Upgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('collaboration', schema=None) as batch_op:
        batch_op.alter_column(
            'initiator_guid', existing_type=postgresql.UUID(), nullable=True
        )

    # ### end Alembic commands ###


def downgrade():
    """
    Downgrade Semantic Description:
        ENTER DESCRIPTION HERE
    """
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('collaboration', schema=None) as batch_op:
        batch_op.alter_column(
            'initiator_guid', existing_type=postgresql.UUID(), nullable=False
        )

    # ### end Alembic commands ###