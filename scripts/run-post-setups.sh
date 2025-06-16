#!/bin/bash

for dir in ../../*/; do
  if [ -f "$dir/post-setup.sh" ]; then
    (cd "$dir" && bash post-setup.sh)
  fi
done
