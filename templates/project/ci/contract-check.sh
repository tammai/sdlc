#!/usr/bin/env bash
# Every contract version published on BASE_REF (a v<N>/ folder holding SPEC_FILE) may only grow: oasdiff fails a
# breaking change, and a removed version fails too. New version folders have nothing to compare against and pass.
# Usage: contract-check.sh BASE_REF CONTRACT_PATH SPEC_FILE
set -euo pipefail
base_ref=$1 contract=${2%/} spec=$3
failed=0
base_file=$(mktemp)
trap 'rm -f "$base_file"' EXIT

for dir in $(git ls-tree -d --name-only "$base_ref" "$contract/"); do
  [[ $(basename "$dir") =~ ^v[0-9]+$ ]] || continue
  git cat-file -e "$base_ref:$dir/$spec" 2>/dev/null || continue
  if [[ ! -f $dir/$spec ]]; then
    echo "published version $dir was removed: breaking changes need a new version folder"
    failed=1
    continue
  fi
  git show "$base_ref:$dir/$spec" > "$base_file"
  if ! oasdiff breaking --fail-on ERR "$base_file" "$dir/$spec"; then
    echo "breaking change in published version $dir: add a new version folder instead"
    failed=1
  fi
done
exit $failed
