# -*- coding: utf-8 -*-
"""empty message

Revision ID: cb07bac06970
Revises: None
Create Date: 2020-04-22 14:50:09.652260

"""

# revision identifiers, used by Alembic.
revision = 'cb07bac06970'
down_revision = None

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'asset',
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('ext', sa.String(length=5), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_asset')),
    )
    op.create_table(
        'user',
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column(
            'password',
            sqlalchemy_utils.types.password.PasswordType(max_length=128),
            nullable=False,
        ),
        sa.Column('first_name', sa.String(length=30), nullable=False),
        sa.Column('middle_name', sa.String(length=30), nullable=True),
        sa.Column('last_name', sa.String(length=30), nullable=False),
        sa.Column('suffix_name', sa.String(length=8), nullable=True),
        sa.Column('birth_month', sa.Integer(), nullable=True),
        sa.Column('birth_year', sa.Integer(), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('address_line1', sa.String(length=120), nullable=True),
        sa.Column('address_line2', sa.String(length=120), nullable=True),
        sa.Column('address_city', sa.String(length=120), nullable=True),
        sa.Column('address_state', sa.String(length=30), nullable=True),
        sa.Column('address_zip', sa.String(length=10), nullable=True),
        sa.Column('profile_asset_id', sa.Integer(), nullable=True),
        sa.Column('static_roles', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user')),
        sa.UniqueConstraint('email', name=op.f('uq_user_email')),
        sa.UniqueConstraint('username', name=op.f('uq_user_username')),
    )
    op.create_table(
        'code',
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column(
            'code_type',
            sa.Enum('invite', 'email', 'recover', 'onetime', name='codetypes'),
            nullable=False,
        ),
        sa.Column('accept_code', sa.String(length=64), nullable=False),
        sa.Column('reject_code', sa.String(length=64), nullable=False),
        sa.Column('expires', sa.DateTime(), nullable=False),
        sa.Column('response', sa.DateTime(), nullable=True),
        sa.Column(
            'decision',
            sa.Enum(
                'unknown',
                'error',
                'expired',
                'dismiss',
                'reject',
                'accept',
                'override',
                name='codedecisions',
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['user.id'], name=op.f('fk_code_user_id_user')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_code')),
    )
    with op.batch_alter_table('code', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_code_accept_code'), ['accept_code'], unique=True
        )
        batch_op.create_index(
            batch_op.f('ix_code_code_type'), ['code_type'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_code_reject_code'), ['reject_code'], unique=True
        )
        batch_op.create_index(batch_op.f('ix_code_user_id'), ['user_id'], unique=False)

    op.create_table(
        'oauth2_client',
        sa.Column('client_id', sa.String(length=40), nullable=False),
        sa.Column('client_secret', sa.String(length=55), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column(
            'client_type',
            sa.Enum('public', 'confidential', name='clienttypes'),
            nullable=False,
        ),
        sa.Column(
            'redirect_uris',
            sqlalchemy_utils.types.scalar_list.ScalarListType(),
            nullable=False,
        ),
        sa.Column(
            'default_scopes',
            sqlalchemy_utils.types.scalar_list.ScalarListType(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['user.id'],
            name=op.f('fk_oauth2_client_user_id_user'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('client_id', name=op.f('pk_oauth2_client')),
    )
    with op.batch_alter_table('oauth2_client', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_oauth2_client_user_id'), ['user_id'], unique=False
        )

    op.create_table(
        'oauth2_grant',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.String(length=40), nullable=False),
        sa.Column('code', sa.String(length=255), nullable=False),
        sa.Column('redirect_uri', sa.String(length=255), nullable=False),
        sa.Column('expires', sa.DateTime(), nullable=False),
        sa.Column(
            'scopes', sqlalchemy_utils.types.scalar_list.ScalarListType(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ['client_id'],
            ['oauth2_client.client_id'],
            name=op.f('fk_oauth2_grant_client_id_oauth2_client'),
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['user.id'],
            name=op.f('fk_oauth2_grant_user_id_user'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth2_grant')),
    )
    with op.batch_alter_table('oauth2_grant', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_oauth2_grant_client_id'), ['client_id'], unique=False
        )
        batch_op.create_index(batch_op.f('ix_oauth2_grant_code'), ['code'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_oauth2_grant_user_id'), ['user_id'], unique=False
        )

    op.create_table(
        'oauth2_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.String(length=40), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_type', sa.Enum('Bearer', name='tokentypes'), nullable=False),
        sa.Column('access_token', sa.String(length=255), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=True),
        sa.Column('expires', sa.DateTime(), nullable=False),
        sa.Column(
            'scopes', sqlalchemy_utils.types.scalar_list.ScalarListType(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ['client_id'],
            ['oauth2_client.client_id'],
            name=op.f('fk_oauth2_token_client_id_oauth2_client'),
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['user.id'],
            name=op.f('fk_oauth2_token_user_id_user'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth2_token')),
        sa.UniqueConstraint('access_token', name=op.f('uq_oauth2_token_access_token')),
        sa.UniqueConstraint('refresh_token', name=op.f('uq_oauth2_token_refresh_token')),
    )
    with op.batch_alter_table('oauth2_token', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_oauth2_token_client_id'), ['client_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_oauth2_token_user_id'), ['user_id'], unique=False
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('oauth2_token', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_oauth2_token_user_id'))
        batch_op.drop_index(batch_op.f('ix_oauth2_token_client_id'))

    op.drop_table('oauth2_token')
    with op.batch_alter_table('oauth2_grant', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_oauth2_grant_user_id'))
        batch_op.drop_index(batch_op.f('ix_oauth2_grant_code'))
        batch_op.drop_index(batch_op.f('ix_oauth2_grant_client_id'))

    op.drop_table('oauth2_grant')
    with op.batch_alter_table('oauth2_client', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_oauth2_client_user_id'))

    op.drop_table('oauth2_client')
    with op.batch_alter_table('code', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_code_user_id'))
        batch_op.drop_index(batch_op.f('ix_code_reject_code'))
        batch_op.drop_index(batch_op.f('ix_code_code_type'))
        batch_op.drop_index(batch_op.f('ix_code_accept_code'))

    op.drop_table('code')
    op.drop_table('user')
    op.drop_table('asset')
    # ### end Alembic commands ###
