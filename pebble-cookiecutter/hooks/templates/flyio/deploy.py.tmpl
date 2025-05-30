#!/usr/bin/env python
"""
Deploy this pebble to Fly.io and get the deployment URL for registry registration.
"""

import os
import subprocess
import sys
import json
import time

def run_command(command, check=True):
    """Run a command and return its output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=check, 
            text=True, 
            capture_output=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error message: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def check_flyctl_installed():
    """Check if flyctl is installed."""
    try:
        run_command("flyctl version")
        return True
    except:
        return False

def install_flyctl():
    """Install flyctl."""
    print("Installing flyctl...")
    if sys.platform == "darwin":  # MacOS
        run_command("brew install flyctl")
    elif sys.platform == "linux":
        run_command('curl -L https://fly.io/install.sh | sh')
    else:
        print("Please install flyctl manually: https://fly.io/docs/hands-on/install-flyctl/")
        sys.exit(1)

def ensure_flyctl_logged_in():
    """Ensure user is logged into Fly.io."""
    try:
        result = run_command("flyctl auth whoami", check=False)
        if "not logged in" in result.lower():
            print("You are not logged in to Fly.io. Please log in:")
            run_command("flyctl auth login")
    except:
        print("Please log in to Fly.io:")
        run_command("flyctl auth login")

def deploy_to_fly():
    """Deploy the application to Fly.io."""
    # Check if app already exists
    app_name = os.path.basename(os.getcwd())
    result = run_command(f"flyctl status --json", check=False)
    
    if "no such app" in result.lower():
        print(f"Creating new Fly.io app: {app_name}")
        run_command("flyctl launch --no-deploy --copy-config")
    
    print(f"Deploying {app_name} to Fly.io...")
    run_command("flyctl deploy")
    
def get_app_url():
    """Get the URL of the deployed app."""
    result = run_command("flyctl status --json")
    try:
        status = json.loads(result)
        hostname = status.get("Hostname", "")
        if hostname:
            url = f"https://{hostname}"
            print(f"App deployed successfully at: {url}")
            return url
    except:
        pass
    
    # Fallback method
    result = run_command("flyctl info")
    for line in result.splitlines():
        if "hostname" in line.lower():
            url = f"https://{line.split(':')[1].strip()}"
            print(f"App deployed successfully at: {url}")
            return url
    
    print("Could not determine the app URL. Please check 'flyctl info'.")
    return None

def register_with_registry(url):
    """Register the pebble with a registry."""
    registry_url = input("Enter the registry URL (leave blank to skip): ")
    if not registry_url.strip():
        print("Skipping registry registration.")
        return
    
    print(f"Registering pebble at {url} with registry at {registry_url}")
    
    # Save the URL to a config file for future use
    config_data = {
        "pebble_url": url,
        "registry_url": registry_url
    }
    
    with open("pebble_config.json", "w") as f:
        json.dump(config_data, f, indent=2)
    
    print(f"Configuration saved to pebble_config.json")
    print(f"To complete registration, please visit the registry at {registry_url}")
    print(f"And provide your pebble URL: {url}")

def main():
    """Main entry point."""
    print("=== Pebble Deployment Tool ===")
    
    # Check for flyctl and install if needed
    if not check_flyctl_installed():
        print("flyctl not found. It's required for deployment.")
        install = input("Would you like to install it now? (y/n): ")
        if install.lower() == 'y':
            install_flyctl()
        else:
            print("Please install flyctl and try again: https://fly.io/docs/hands-on/install-flyctl/")
            sys.exit(1)
    
    # Ensure logged in
    ensure_flyctl_logged_in()
    
    # Deploy
    deploy_to_fly()
    
    # Get URL
    url = get_app_url()
    
    # Register with registry if URL was obtained
    if url:
        register = input("Do you want to register this pebble with a registry? (y/n): ")
        if register.lower() == 'y':
            register_with_registry(url)
    
    print("Deployment complete!")

if __name__ == "__main__":
    main()
