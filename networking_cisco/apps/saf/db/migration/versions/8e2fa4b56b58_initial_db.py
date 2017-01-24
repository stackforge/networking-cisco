# Copyright 2016 Cisco Systems, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""initial db

Revision ID: 8e2fa4b56b58
Revises:
Create Date: 2017-01-17 06:24:55.000268

"""

# revision identifiers, used by Alembic.
revision = '8e2fa4b56b58'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('agents',
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('heartbeat', sa.DateTime(), nullable=True),
        sa.Column('configurations', sa.String(length=4095), nullable=True),
        sa.PrimaryKeyConstraint('host')
    )
    op.create_table('firewall',
        sa.Column('fw_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('fw_type', sa.String(length=8), nullable=True),
        sa.Column('tenant_id', sa.String(length=36), nullable=True),
        sa.Column('in_network_id', sa.String(length=36), nullable=True),
        sa.Column('in_service_node_ip', sa.String(length=16), nullable=True),
        sa.Column('out_network_id', sa.String(length=36), nullable=True),
        sa.Column('out_service_node_ip', sa.String(length=16), nullable=True),
        sa.Column('router_id', sa.String(length=36), nullable=True),
        sa.Column('router_net_id', sa.String(length=36), nullable=True),
        sa.Column('router_subnet_id', sa.String(length=36), nullable=True),
        sa.Column('fw_mgmt_ip', sa.String(length=16), nullable=True),
        sa.Column('openstack_provision_status',
                  sa.String(length=34), nullable=True),
        sa.Column('dcnm_provision_status',
                  sa.String(length=38), nullable=True),
        sa.Column('device_provision_status',
                  sa.String(length=30), nullable=True),
        sa.Column('rules', sa.String(length=4096), nullable=True),
        sa.Column('result', sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint('fw_id')
    )
    op.create_table('in_service_subnet',
        sa.Column('subnet_address', sa.String(length=20),
                  autoincrement=False, nullable=False),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('subnet_id', sa.String(length=36), nullable=True),
        sa.Column('allocated', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('subnet_address')
    )
    op.create_table('instances',
        sa.Column('port_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('mac', sa.String(length=17), nullable=True),
        sa.Column('status', sa.String(length=8), nullable=True),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('instance_id', sa.String(length=36), nullable=True),
        sa.Column('ip', sa.String(length=16), nullable=True),
        sa.Column('segmentation_id', sa.Integer(), nullable=True),
        sa.Column('fwd_mod', sa.String(length=16), nullable=True),
        sa.Column('gw_mac', sa.String(length=17), nullable=True),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('result', sa.String(length=16), nullable=True),
        sa.PrimaryKeyConstraint('port_id')
    )
    op.create_table('networks',
        sa.Column('network_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('config_profile', sa.String(length=255), nullable=True),
        sa.Column('segmentation_id', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.String(length=36), nullable=True),
        sa.Column('fwd_mod', sa.String(length=16), nullable=True),
        sa.Column('vlan', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=16), nullable=True),
        sa.Column('result', sa.String(length=16), nullable=True),
        sa.PrimaryKeyConstraint('network_id')
    )
    op.create_table('out_service_subnet',
        sa.Column('subnet_address', sa.String(length=20),
                  autoincrement=False, nullable=False),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('subnet_id', sa.String(length=36), nullable=True),
        sa.Column('allocated', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('subnet_address')
    )
    op.create_table('segmentation_id',
        sa.Column('segmentation_id', sa.Integer(),
                  autoincrement=False, nullable=False),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('allocated', sa.Boolean(), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=True),
        sa.Column('delete_time', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('segmentation_id')
    )
    op.create_table('tenants',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('dci_id', sa.Integer(), nullable=True),
        sa.Column('result', sa.String(length=16), nullable=True),
        sa.PrimaryKeyConstraint('id', 'name')
    )
    op.create_table('vlan_id',
        sa.Column('segmentation_id', sa.Integer(),
                  autoincrement=False, nullable=False),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('allocated', sa.Boolean(), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=True),
        sa.Column('delete_time', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('segmentation_id')
    )


def downgrade():
    op.drop_table('vlan_id')
    op.drop_table('tenants')
    op.drop_table('segmentation_id')
    op.drop_table('out_service_subnet')
    op.drop_table('networks')
    op.drop_table('instances')
    op.drop_table('in_service_subnet')
    op.drop_table('firewall')
    op.drop_table('agents')
