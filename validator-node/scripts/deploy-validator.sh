#!/usr/bin/env bash

CWD=$(dirname "$0")/..
set -e
declare -a NODES=(
  "validator-example-node-1"
)

for NODE in "${NODES[@]}"
do
  ssh-copy-id user@${NODE}
  rsync -av --rsync-path="sudo rsync" "${CWD}/mtc_backup/${NODE}/" "user@${NODE}:/root/mtc_backup" && echo 'ok'
  rsync -av ${CWD}/monitoring-exporters user@${NODE}:~/ --exclude node_modules --exclude mtc_backup --exclude ansible
done

ansible-playbook -i ./ansible/inventory.ini ./ansible/validators.yml --ask-vault-pass

for NODE in "${NODES[@]}"
do
echo "Backup " $NODE
  rsync -av --rsync-path="sudo rsync" "user@${NODE}:/root/mtc_backup/" ${CWD}/mtc_backup/${NODE}/ && echo 'ok'
done
