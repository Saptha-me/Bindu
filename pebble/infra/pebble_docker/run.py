"""
Run Pebble server in Docker container
"""
import argparse

from pebble.infra.pebble_docker.resources import PebbleDockerResources


def main():
    """Run Pebble server in Docker"""
    parser = argparse.ArgumentParser(description="Run Pebble server in Docker")
    parser.add_argument("--force", action="store_true", help="Force recreation of resources")
    parser.add_argument("--pull", action="store_true", help="Pull latest images")
    args = parser.parse_args()

    # Initialize Docker resources
    resources = PebbleDockerResources()

    # Create resources (containers, networks, etc.)
    print("Creating Pebble Docker resources...")
    num_created, num_total = resources.create_resources(
        force=args.force,
        pull=args.pull,
        auto_confirm=True
    )
    
    print(f"Created {num_created}/{num_total} resources")


if __name__ == "__main__":
    main()
