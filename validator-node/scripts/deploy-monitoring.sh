#!/usr/bin/env bash
ansible-playbook -i ./ansible/inventory.ini ./ansible/monitoring.yml --ask-vault-pass