#!/bin/bash
#start all containers
for dir in ../*/; do
  if [ -f "$dir/docker compose.yml" ]; then
    if [ -f "$dir/setup.sh" ]; then
      (cd "$dir" && bash setup.sh)
    fi
    (cd "$dir" && bash docker compose up -d)
  fi
done
