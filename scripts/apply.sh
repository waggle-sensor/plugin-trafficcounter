#!/bin/bash

# This script uploads and applies lane configurations to a node.
# WARNING: This requires a privileged access to the node.
# WARNING: This script contains lots of hardcoded variables. Please change them as needed.

node=$1
node=$(echo "$node" | tr '[:lower:]' '[:upper:]')

# Change the path as needed
config_path="./data"

# Uncomment below to apply all configurations for the node
# files=$(ls ${config_path}/${node}*.json 2>/dev/null)
# if [ -z "$files" ]; then
#     echo "No configuration files found for node ${node}."
#     exit 1
# fi

leftlane=${config_path}/${node}_left_resized.json
rightlane=${config_path}/${node}_right_resized.json

rsync -av $leftlane node-${node}:/root/LEFTLANE
rsync -av $rightlane node-${node}:/root/RIGHTLANE

echo "Applying configurations to node-${node}..."
ssh node-${node} -x "
  kubectl -n default delete secret mysecret
  kubectl -n ses delete secret mysecret
  kubectl -n default create secret generic mysecret --from-file=/root/RIGHTLANE --from-file=/root/LEFTLANE
  kubectl -n ses create secret generic mysecret --from-file=/root/RIGHTLANE --from-file=/root/LEFTLANE
"