# Pebble Framework Utility Tools

This directory contains utility tools for the Pebble Framework.

## Security Management (`manage_secrets.py`)

The `manage_secrets.py` script provides tools for managing security-related settings, particularly the secret keys used for API authentication.

### Features

- **Secret Key Generation**: Creates a secure random secret key using OpenSSL
- **Environment File Management**: Maintains secret keys in `.env` files
- **Key Rotation**: Allows easy rotation of secret keys using the awk command pattern
- **Project Root Detection**: Automatically locates the project root directory

### Usage

```bash
# Ensure .env file exists with a SECRET_KEY
python manage_secrets.py ensure

# Rotate the current SECRET_KEY (uses awk -v key="$(openssl rand -base64 42)" pattern)
python manage_secrets.py rotate

# Get the current SECRET_KEY (only for development debugging)
python manage_secrets.py get
```

### Programmatic Usage

```python
from utils.manage_secrets import ensure_env_file, rotate_key_with_awk

# Ensure .env file exists before application startup
ensure_env_file()

# Rotate key if needed (useful for scheduled security updates)
rotate_key_with_awk()
```

### Security Best Practices

1. **Never commit `.env` files to version control**
2. **Rotate keys regularly** for enhanced security
3. **Limit access** to the `get` command in production environments
4. **Include `.env` in your `.gitignore` file**

## Adding to `.gitignore`

Ensure your `.gitignore` file includes:

```
# Environment variables
.env
.env.*
```

This helps prevent accidental exposure of secret keys in version control.
