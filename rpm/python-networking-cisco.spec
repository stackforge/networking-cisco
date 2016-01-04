%global drv_vendor Cisco
%global srcname networking_cisco
%global package_name networking-cisco
%global docpath doc/build/html

%{!?upstream_version: %global upstream_version %{version}%{?milestone}}

Name:           python-%{package_name}
Version:        XXX
Release:        XXX
Summary:        %{drv_vendor} OpenStack Neutron driver

License:        ASL 2.0
URL:            https://pypi.python.org/pypi/%{package_name}
Source0:        https://pypi.python.org/packages/source/n/networking-cisco/networking-cisco-2015.1.2.tar.gz
Source1:        neutron-cisco-cfg-agent.service
Source2:        neutron-cisco-apic-host-agent.service
Source3:        neutron-cisco-apic-service-agent.service

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-mock
BuildRequires:  python-neutron-tests
BuildRequires:  python-oslo-sphinx
BuildRequires:  python-pbr
BuildRequires:  python-setuptools
BuildRequires:  python-sphinx
BuildRequires:  python-testrepository
BuildRequires:  python-testtools
BuildRequires:	systemd-units

Requires:       python-babel
Requires:       python-pbr
Requires:       openstack-neutron-common
Requires:       python-UcsSdk
Requires:       python-ncclient
Requires:       python-lxml

Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
This package contains %{drv_vendor} networking driver for OpenStack Neutron.

%prep
%setup -q -n %{package_name}-%{upstream_version}

%build
%{__python2} setup.py build
%{__python2} setup.py build_sphinx
rm %{docpath}/.buildinfo

%install
export PBR_VERSION=%{version}
export SKIP_PIP_INSTALL=1
%{__python2} setup.py install --skip-build --root %{buildroot}
install -d -m 755 %{buildroot}%{_sysconfdir}/neutron/
mv %{buildroot}/usr/etc/neutron/*.ini %{buildroot}%{_sysconfdir}/neutron/
install -d -m 755 %{buildroot}%{_sysconfdir}/saf/
mv %{buildroot}/usr/etc/saf/enabler_conf.ini %{buildroot}%{_sysconfdir}/saf/

# Install systemd units
install -p -D -m 644 %{SOURCE1} %{buildroot}%{_unitdir}/neutron-cisco-cfg-agent.service
install -p -D -m 644 %{SOURCE2} %{buildroot}%{_unitdir}/neutron-cisco-apic-host-agent.service
install -p -D -m 644 %{SOURCE3} %{buildroot}%{_unitdir}/neutron-cisco-apic-service-agent.service
mv %{buildroot}/usr/etc/saf/init/*.service %{buildroot}%{_unitdir}

# Remove upstart files, they are not needed
rm %{buildroot}/usr/etc/saf/init/*.conf

mkdir -p %{buildroot}/%{_sysconfdir}/neutron/conf.d/neutron-cisco-cfg-agent

%files
%license LICENSE
%doc README.rst
%doc %{docpath}
%{python2_sitelib}/%{srcname}
%{python2_sitelib}/%{srcname}-%{version}-py%{python2_version}.egg-info
%config(noreplace) %attr(0640, root, neutron) %{_sysconfdir}/neutron/*.ini
%config(noreplace) %attr(0640, root, neutron) %{_sysconfdir}/saf/*.ini
%{_bindir}/neutron-cisco-cfg-agent
%{_bindir}/neutron-cisco-apic-host-agent
%{_bindir}/neutron-cisco-apic-service-agent
%{_bindir}/fabric-enabler-agent
%{_bindir}/fabric-enabler-cli
%{_bindir}/fabric-enabler-server
%{_unitdir}/neutron-cisco-cfg-agent.service
%{_unitdir}/neutron-cisco-apic-host-agent.service
%{_unitdir}/neutron-cisco-apic-service-agent.service
%{_unitdir}/fabric-enabler-agent.service
%{_unitdir}/fabric-enabler-server.service

%post
%systemd_post neutron-cisco-cfg-agent.service
%systemd_post neutron-cisco-apic-host-agent.service
%systemd_post neutron-cisco-apic-service-agent.service
%systemd_post fabric-enabler-agent.service
%systemd_post fabric-enabler-server.service

%preun
%systemd_preun neutron-cisco-cfg-agent.service
%systemd_preun neutron-cisco-apic-host-agent.service
%systemd_preun neutron-cisco-apic-service-agent.service
%systemd_preun fabric-enabler-agent.service
%systemd_preun fabric-enabler-server.service

%postun
%systemd_postun_with_restart neutron-cisco-cfg-agent.service
%systemd_postun_with_restart neutron-cisco-apic-host-agent.service
%systemd_postun_with_restart neutron-cisco-apic-service-agent.service
%systemd_postun_with_restart fabric-enabler-agent.service
%systemd_postun_with_restart fabric-enabler-server.service

%changelog
