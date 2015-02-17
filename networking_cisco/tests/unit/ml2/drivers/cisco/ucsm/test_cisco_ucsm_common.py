#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from neutron.common import config as neutron_config
from neutron.plugins.ml2 import config as ml2_config
from networking_cisco.plugins.ml2.drivers.cisco.ucsm import config
from neutron.tests import base

UCSM_IP_ADDRESS = '1.1.1.1'
UCSM_USERNAME = 'username'
UCSM_PASSWORD = 'password'
UCSM_PHY_NETS = ['test_physnet']
HOST_CONFIG1 = ['Hostname1:Service_profile1']


class ConfigMixin(object):

    """Mock config for UCSM driver."""

    def __init__(self):
        self.mocked_parser = None

    def set_up_mocks(self):
        # Mock the configuration file

        args = ['--config-file', base.etcdir('neutron.conf.test')]
        neutron_config.init(args=args)

        # Configure the ML2 mechanism drivers and network types
        ml2_opts = {
            'mechanism_drivers': ['cisco_ucsm'],
            'tenant_network_types': ['vlan'],
        }
        for opt, val in ml2_opts.items():
            ml2_config.cfg.CONF.set_override(opt, val, 'ml2')

        # Configure the Cisco UCS Manager mechanism driver
        ucsm_test_config = {
            'ucsm_ip': UCSM_IP_ADDRESS,
            'ucsm_username': UCSM_USERNAME,
            'ucsm_password': UCSM_PASSWORD,
            'ucsm_host_list': HOST_CONFIG1,
        }

        for opt, val in ucsm_test_config.items():
            ml2_ucsm_config.cfg.CONF.set_override(opt, val, 'ml2_cisco_ucsm')
