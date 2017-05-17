#!make
include envfile

build:
	python setup.py sdist

kolla-build:
	.venv/bin/kolla-build -b centos --tag 4.0.0 --template-override networking-cisco-override.j2 neutron-server

kolla-build-premerge:
	.venv/bin/kolla-build -b centos --tag 4.0.0 --template-override networking-cisco-override-premerge.j2 neutron-server

docker-push:
	docker tag kolla/centos-binary-neutron-server:4.0.0 ${OSCORE_REGISTRY}/${OSCORE_NAMESPACE}/centos-binary-neutron-server:${OSCORE_VERSION}
	docker push ${OSCORE_REGISTRY}/${OSCORE_NAMESPACE}/centos-binary-neutron-server:${OSCORE_VERSION}

pep8:
	ls -l .venv/bin/activate
	. .venv/bin/activate
	.venv/bin/pep8 cisco/*

clean:
	rm -rf .venv
	virtualenv .venv
	. .venv/bin/activate
	.venv/bin/pip install -U six pip
	.venv/bin/pip install -r build-requirements.txt -U
