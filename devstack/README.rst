======================
 Enabling in Devstack
======================

1. Download DevStack

2. Add this repo as an external repository::

     > cat local.conf
     [[local|localrc]]
     enable_plugin networking-cisco https://github.com/stackforge/networking-cisco.git
     enable_service cisco-ml2


3. run ``stack.sh``