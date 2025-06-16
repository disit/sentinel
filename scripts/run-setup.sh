#!/bin/bash

for dir in ../../*/; do
  if [ -f "$dir/setup.sh" ]; then
    (cd "$dir" && bash setup.sh)
  fi
done
