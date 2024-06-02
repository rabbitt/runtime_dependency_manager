#!/bin/bash

# Get the latest tag
LATEST_TAG=$(git describe --tags $(git rev-list --tags --max-count=1) 2>/dev/null)
if [ -z "$LATEST_TAG" ]; then
  LATEST_TAG="0.1.0"
fi

# Increment the patch version
IFS='.' read -r MAJOR MINOR PATCH <<< "${LATEST_TAG//v/}"
if [[ ${LATEST_TAG} = "0.1.0" ]]; then
    DEFAULT_VERSION="${MAJOR}.${MINOR}.${PATCH}"
else
    DEFAULT_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
fi

# Prompt for the new version
read -p "Enter the version [${DEFAULT_VERSION}]: " VERSION
VERSION=${VERSION:-$DEFAULT_VERSION}

# Validate the version
if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Invalid version: ${VERSION}" >&2
  exit 1
fi

# Output the version
echo $VERSION
