#!/bin/bash

# Configuration
REMOTE_HOST="nbservices"  # Set the remote host here

# Function to check for a clean working branch
check_clean_branch() {
    if ! git diff-index --quiet HEAD --; then
        echo "Error: Working directory is not clean. Please commit or stash your changes before running this script."
        exit 1
    fi

    if [ -n "$(git ls-files --others --exclude-standard)" ]; then
        echo "Error: There are untracked files in the repository. Please add or remove them before running this script."
        exit 1
    fi

    echo "Working directory is clean."
}

# Function to check SSH connectivity
check_ssh_connectivity() {
    echo "Checking SSH connectivity to $REMOTE_HOST..."
    if ssh -q $REMOTE_HOST exit; then
        echo "SSH connection successful."
    else
        echo "Error: Unable to establish SSH connection to $REMOTE_HOST. Please check your SSH configuration."
        exit 1
    fi
}

# Function to publish a single connector
publish_connector() {
    local connector=$1
    echo "Publishing connector: $connector"

    # Get the directory of the script
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

    # Path to metadata.yaml relative to the script location
    METADATA_PATH="$SCRIPT_DIR/../airbyte-integrations/connectors/$connector/metadata.yaml"

    # Check if metadata.yaml exists
    if [ ! -f "$METADATA_PATH" ]; then
        echo "Error: metadata.yaml not found at $METADATA_PATH"
        return 1
    fi

    # Extract the version from metadata.yaml
    VERSION=$(awk '/dockerImageTag:/ {print $2}' "$METADATA_PATH")

    # Check if VERSION is empty
    if [ -z "$VERSION" ]; then
        echo "Error: Could not extract version from metadata.yaml for $connector"
        return 1
    fi

    # Extract the dockerRepository from metadata.yaml
    DOCKER_REPO=$(awk '/dockerRepository:/ {print $2}' "$METADATA_PATH")

    # Check if DOCKER_REPO is empty
    if [ -z "$DOCKER_REPO" ]; then
        echo "Error: Could not extract dockerRepository from metadata.yaml for $connector"
        return 1
    fi

    echo "Extracted version: $VERSION"
    echo "Docker repository: $DOCKER_REPO"

    # Build the connector
    airbyte-ci connectors --name="$connector" build --architecture=linux/amd64 

    # Tag the Docker image with the extracted version and latest
    docker tag airbyte/"$connector":dev "$DOCKER_REPO":"$VERSION"
    docker tag airbyte/"$connector":dev "$DOCKER_REPO":latest

    # Push the Docker images
    docker push "$DOCKER_REPO":"$VERSION"
    docker push "$DOCKER_REPO":latest

    echo "Successfully built and pushed $DOCKER_REPO:$VERSION and $DOCKER_REPO:latest"

    # Run remote commands
    echo "Running remote commands on $REMOTE_HOST..."
    ssh $REMOTE_HOST << EOF
        set -e
        docker pull $DOCKER_REPO:latest
        kind load docker-image $DOCKER_REPO:latest --name airbyte-abctl
EOF

    if [ $? -ne 0 ]; then
        echo "Error: Remote commands failed on $REMOTE_HOST. Exiting without creating GitHub tag."
        return 1
    fi

    echo "Remote commands executed successfully on $REMOTE_HOST."

    # Create and push GitHub tag
    TAG_NAME="$connector-$VERSION"
    git tag -a "$TAG_NAME" -m "Release $connector version $VERSION"
    git push origin "$TAG_NAME"

    echo "Created and pushed GitHub tag: $TAG_NAME"
}

# Function to check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
        echo "Error: This script must be run from within a Git repository."
        exit 1
    fi
}

# Function to check if we're on the correct branch
check_correct_branch() {
    local required_branch="neonblue-connectors"
    local current_branch=$(git rev-parse --abbrev-ref HEAD)

    if [ "$current_branch" != "$required_branch" ]; then
        echo "Error: Not on the required branch. Current branch is $current_branch, but should be $required_branch."
        echo "Please switch to the $required_branch branch and run the script again."
        exit 1
    else
        echo "Confirmed: On the correct branch ($required_branch)."
    fi
}

# Array of connectors to publish
CONNECTORS=("source-klaviyo")  # Add more connectors here as needed

# Check if we're in a git repository
check_git_repo

# Check if we're on the correct branch
check_correct_branch

# Check for a clean working branch
check_clean_branch

# Check SSH connectivity
check_ssh_connectivity

# Loop through each connector and publish it
for connector in "${CONNECTORS[@]}"; do
    publish_connector "$connector"
done