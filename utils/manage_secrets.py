#!/usr/bin/env python
"""
Secret Management Utility for Pebble Framework

This script provides utilities for managing secret keys used by the Pebble framework,
including generating and rotating keys securely.
"""

import argparse
import base64
import os
import pathlib
import subprocess
import sys
from typing import Optional

# Ensure we can import from parent directory
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv


def get_project_root() -> pathlib.Path:
    """Find the project root by searching for .env file or returning script parent's parent."""
    script_dir = pathlib.Path(__file__).parent.absolute()
    
    # Try to find .env file
    current_dir = script_dir
    while current_dir != current_dir.parent:
        env_file = current_dir / ".env"
        if env_file.exists():
            return current_dir
        current_dir = current_dir.parent
    
    # If no .env found, use the script's parent directory
    return script_dir.parent


def get_env_file_path() -> pathlib.Path:
    """Get the path to the .env file."""
    root_dir = get_project_root()
    return root_dir / ".env"


def ensure_env_file(env_file: Optional[pathlib.Path] = None) -> pathlib.Path:
    """Ensure the .env file exists with a SECRET_KEY."""
    if env_file is None:
        env_file = get_env_file_path()
    
    if not env_file.exists():
        # Create a new .env file with a random secret key
        with open(env_file, "w") as f:
            secret_key = base64.b64encode(os.urandom(42)).decode()
            f.write(f"SECRET_KEY={secret_key}\n")
        print(f"Created new .env file at {env_file} with a random SECRET_KEY")
    else:
        # Check if SECRET_KEY exists in the .env file
        with open(env_file, "r") as f:
            content = f.read()
        
        if "SECRET_KEY=" not in content:
            # Add SECRET_KEY to the existing .env file
            with open(env_file, "a") as f:
                secret_key = base64.b64encode(os.urandom(42)).decode()
                f.write(f"\nSECRET_KEY={secret_key}\n")
            print(f"Added SECRET_KEY to existing .env file at {env_file}")
        else:
            print(f"Verified .env file at {env_file} already contains SECRET_KEY")
    
    return env_file


def rotate_key_with_awk(env_file: Optional[pathlib.Path] = None) -> bool:
    """Rotate the SECRET_KEY in the .env file using awk command.
    
    This uses the exact command format: 
    awk -v key="$(openssl rand -base64 42)" '/^SECRET_KEY=/ {sub(/=.*/, "=" key)} 1' .env > temp_env && mv temp_env .env
    
    Returns:
        bool: True if rotation was successful, False otherwise.
    """
    if env_file is None:
        env_file = get_env_file_path()
    
    # Ensure the .env file exists
    env_file = ensure_env_file(env_file)
    
    try:
        # Generate a new random key using openssl as requested
        new_key = subprocess.check_output(["openssl", "rand", "-base64", "42"]).decode().strip()
        
        # Create the awk command exactly as specified
        awk_cmd = f'awk -v key="{new_key}" \'/^SECRET_KEY=/ {{sub(/=.*/, "=" key)}} 1\' {env_file} > {env_file}.tmp'
        mv_cmd = f'mv {env_file}.tmp {env_file}'
        
        # Execute the commands
        subprocess.run(awk_cmd, shell=True, check=True)
        subprocess.run(mv_cmd, shell=True, check=True)
        
        print(f"Successfully rotated SECRET_KEY in {env_file}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"Error rotating key with awk: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error rotating key: {e}")
        return False


def get_current_secret_key() -> Optional[str]:
    """Get the current SECRET_KEY from the .env file."""
    env_file = ensure_env_file()
    load_dotenv(env_file)
    return os.environ.get("SECRET_KEY")


def main():
    """Main function to parse arguments and run commands."""
    parser = argparse.ArgumentParser(description="Manage secret keys for Pebble framework")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Ensure command
    ensure_parser = subparsers.add_parser("ensure", help="Ensure .env file exists with SECRET_KEY")
    ensure_parser.add_argument("--env-file", type=str, help="Path to .env file")
    
    # Rotate command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate the SECRET_KEY in the .env file")
    rotate_parser.add_argument("--env-file", type=str, help="Path to .env file")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get the current SECRET_KEY")
    
    args = parser.parse_args()
    
    if args.command == "ensure":
        env_file = pathlib.Path(args.env_file) if args.env_file else None
        ensure_env_file(env_file)
    
    elif args.command == "rotate":
        env_file = pathlib.Path(args.env_file) if args.env_file else None
        rotate_key_with_awk(env_file)
    
    elif args.command == "get":
        secret_key = get_current_secret_key()
        if secret_key:
            print(f"Current SECRET_KEY: {secret_key}")
        else:
            print("No SECRET_KEY found")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
