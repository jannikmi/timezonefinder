#!/bin/bash
# Script to filter outdated packages to only show those that can actually be upgraded
# This excludes packages that are constrained by other dependencies

set -e

LOCKFILE="uv.lock"
LOCKFILE_BACKUP="uv.lock.backup"

# Cleanup function to restore lockfile
cleanup() {
    if [ -f "$LOCKFILE_BACKUP" ]; then
        mv "$LOCKFILE_BACKUP" "$LOCKFILE" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT ERR

# Get package version from lockfile
get_version() {
    local package="$1"
    local lockfile="$2"
    awk -v pkg="$package" '/^name = / {name = $3; gsub(/"/, "", name); next} /^version = / && name == pkg {gsub(/"/, "", $3); print $3; exit}' "$lockfile" 2>/dev/null || echo ""
}

# Get list of outdated packages
OUTDATED_OUTPUT=$(uv tree --outdated 2>&1 || true)
if [ -z "$OUTDATED_OUTPUT" ] || echo "$OUTDATED_OUTPUT" | grep -q "No outdated packages"; then
    echo "No outdated packages found"
    exit 0
fi

# Extract package names from outdated output
OUTDATED_PACKAGES=$(echo "$OUTDATED_OUTPUT" | grep -E "^\w+ " | awk '{print $1}' | sort -u)

if [ -z "$OUTDATED_PACKAGES" ]; then
    echo "No outdated packages found"
    exit 0
fi

# Backup lockfile
cp "$LOCKFILE" "$LOCKFILE_BACKUP"

# Try to upgrade all packages
if ! uv lock --upgrade >/dev/null 2>&1; then
    # If upgrade fails, restore and show all outdated (they might all be constrained)
    mv "$LOCKFILE_BACKUP" "$LOCKFILE"
    echo "Warning: Could not perform upgrade check. Showing all outdated packages:"
    echo "$OUTDATED_OUTPUT"
    exit 0
fi

# Find packages that actually changed versions
UPGRADEABLE_PACKAGES=()
while IFS= read -r package; do
    if [ -n "$package" ]; then
        old_ver=$(get_version "$package" "$LOCKFILE_BACKUP")
        new_ver=$(get_version "$package" "$LOCKFILE")
        if [ -n "$old_ver" ] && [ -n "$new_ver" ] && [ "$old_ver" != "$new_ver" ]; then
            UPGRADEABLE_PACKAGES+=("$package")
        fi
    fi
done <<< "$OUTDATED_PACKAGES"

# Restore original lockfile
mv "$LOCKFILE_BACKUP" "$LOCKFILE"

# Show only packages that can actually be upgraded
if [ ${#UPGRADEABLE_PACKAGES[@]} -eq 0 ]; then
    echo "No upgradeable packages found (all outdated packages are constrained by dependencies)"
else
    echo "Upgradeable packages:"
    for package in "${UPGRADEABLE_PACKAGES[@]}"; do
        echo "$OUTDATED_OUTPUT" | grep "^$package " || true
    done
fi
