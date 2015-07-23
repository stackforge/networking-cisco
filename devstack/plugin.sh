#!/bin/bash

DIR_CISCO=$DEST/networking-cisco

if is_service_enabled net-cisco; then

    if [[ "$1" == "source" ]]; then
        :
    fi

    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then        :
        :

    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        cd $DIR_CISCO
        echo "Installing Networking-Cisco"
        sudo python setup.py install

        if is_service_enabled cisco-fwaas; then
            echo "Installing neutron-fwaas"
            source $DIR_CISCO/devstack/csr1kv/cisco_fwaas
            install_cisco_fwaas
        fi
        if is_service_enabled cisco-vpn; then
            echo "Installing neutron-vpnaas"
            source $DIR_CISCO/devstack/csr1kv/cisco_vpn
            install_cisco_vpn
        fi

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        if is_service_enabled q-ciscorouter && is_service_enabled ciscocfgagent; then
            source $DIR_CISCO/devstack/csr1kv/cisco_neutron
            if is_service_enabled cisco-fwaas; then
                configure_cisco_fwaas
            fi
            if is_service_enabled cisco-vpn; then
                configure_cisco_vpn
            fi
            configure_cisco_csr_router
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        if is_service_enabled q-ciscorouter && is_service_enabled ciscocfgagent; then
           if is_service_enabled cisco-fwaas; then
               start_cisco_fwaas
           fi
           if is_service_enabled cisco-vpn; then
               start_cisco_vpn
           fi
           start_cisco_csr_router
        fi
    fi

    if [[ "$1" == "unstack" ]]; then
        net_stop_neutron
    fi

    if [[ "$1" == "clean" ]]; then
        :
    fi
fi
