#!/usr/bin/env bash

set -e

curl -X POST -d "branches=master" -d "token=37dc4f4a56e0788ca90f057b8337a822fea0123f" https://readthedocs.org/api/v2/webhook/networking-cisco/10827/
