# Copyright 2017 Cisco Systems, Inc.
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

"""Add Port Profile delete table for UCSM plugin

Revision ID: 203b495958cf
Revises: b29f1026b281
Create Date: 2017-01-03 16:25:03.426346

"""

# revision identifiers, used by Alembic.
revision = '203b495958cf'
down_revision = 'b29f1026b281'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('ml2_ucsm_delete_port_profiles',
        sa.Column('profile_id', sa.String(length=64), nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('profile_id', 'device_id')
    )
