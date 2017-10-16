===================================================
ASR1000 L3 Router Service Plugin Installation Guide
===================================================

This is an installation guide for enabling the ASR1000 L3 Router Service Plugin
(L3P) support on OpenStack.  This guide only covers details on the ASR1k L3P
install and does not cover OpenStack or ASR1000 router installation.
The `Prerequisites`_ section contains links for this.

Prerequisites
~~~~~~~~~~~~~

The prerequisites for installing the ASR1k L3P as follows:

* Cisco IOS XE image version -

* The ASR1k L3P has been tested on these OSs.

    * Ubuntu 14.04 or above

* Your ASR1k router must be set-up as described in the next section
  `ASR1k Router Setup`_.

* As the ASR1k L3P uses ncclient the following must also be installed:

    * ``Paramiko`` library, the SSHv2 protocol library for python
    * The ``ncclient`` (minimum version v0.4.2) python library for NETCONF
      clients.  Install the ncclient library by using the pip package
      manager at your shell prompt:
      :command:`pip install ncclient == 0.4.2`

ASR1k Router Setup
~~~~~~~~~~~~~~~~~~~

This section lists what is required to prepare the ASR1k router for operation
with the ASR1k L3P.

#. Your ASR1k router must be connected to a management network separate from
   the OpenStack data network. The ASR1k L3P *must* be able to access this
   network so it can communicate with the router to set up tenant data flows.


ASR1k L3P Installation
~~~~~~~~~~~~~~~~~~~~~~