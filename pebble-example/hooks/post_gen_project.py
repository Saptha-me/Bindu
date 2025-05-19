#!/usr/bin/env python
from __future__ import annotations

import os
import shutil
import toml
from pathlib import Path

PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)


def remove_file(filepath: str) -> None:
    os.remove(os.path.join(PROJECT_DIRECTORY, filepath))


def remove_dir(filepath: str) -> None:
    shutil.rmtree(os.path.join(PROJECT_DIRECTORY, filepath))


def move_file(filepath: str, target: str) -> None:
    os.rename(os.path.join(PROJECT_DIRECTORY, filepath), os.path.join(PROJECT_DIRECTORY, target))


def move_dir(src: str, target: str) -> None:
    shutil.move(os.path.join(PROJECT_DIRECTORY, src), os.path.join(PROJECT_DIRECTORY, target))


def write_file(filepath: str, content: str) -> None:
    """Write content to a file."""
    full_path = os.path.join(PROJECT_DIRECTORY, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w') as f:
        f.write(content)


def setup_deployment_files():
    """Set up deployment-specific files based on the selected platform."""
    deployment_platform = "{{cookiecutter.deployment_platform}}"
    project_slug = "{{cookiecutter.project_slug}}"
    
    # Platform-specific files
    if deployment_platform == "fly.io":
        # fly.toml file for Fly.io deployment
        fly_toml_content = f'''
# fly.toml app configuration file
app = "{{cookiecutter.project_slug}}"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
'''
        write_file('fly.toml', fly_toml_content)
        
        # Create a CLI script for deployments
        deploy_script = '''#!/usr/bin/env python
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
'''
        write_file(os.path.join(project_slug, 'deploy.py'), deploy_script)
        
        # Make the deploy script executable
        deploy_script_path = os.path.join(PROJECT_DIRECTORY, project_slug, 'deploy.py')
        os.chmod(deploy_script_path, 0o755)
        
    elif deployment_platform == "render":
        # render.yaml file for Render deployment
        render_yaml_content = f'''
services:
  - type: web
    name: {{cookiecutter.project_slug}}
    runtime: python
    plan: free
    buildCommand: uv sync
    startCommand: python -m pebbling
    envVars:
      - key: PYTHONPATH
        value: .
      - key: PORT
        value: 8000
'''
        write_file('render.yaml', render_yaml_content)
        
    elif deployment_platform == "kubernetes":
        # Kubernetes deployment yaml file
        k8s_deployment_content = f'''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{cookiecutter.project_slug}}
  labels:
    app: {{cookiecutter.project_slug}}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {{cookiecutter.project_slug}}
  template:
    metadata:
      labels:
        app: {{cookiecutter.project_slug}}
    spec:
      containers:
      - name: {{cookiecutter.project_slug}}
        image: {{cookiecutter.project_slug}}:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
        env:
        - name: PORT
          value: "8000"
---
apiVersion: v1
kind: Service
metadata:
  name: {{cookiecutter.project_slug}}
spec:
  selector:
    app: {{cookiecutter.project_slug}}
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
'''
        write_file('k8s/deployment.yaml', k8s_deployment_content)


if __name__ == "__main__":
    # Set up deployment files based on the selected platform
    setup_deployment_files()
    
    print("Project generated successfully!")
