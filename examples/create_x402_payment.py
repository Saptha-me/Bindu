#!/usr/bin/env python3
"""
Create x402 Payment Payload

This script generates a signed x402 payment payload for Bindu agents.
It takes payment requirements from the agent and creates a properly signed
EIP-3009 authorization that can be submitted with your message.

Usage:
    # Interactive mode (paste payment requirements)
    python create_x402_payment.py

    # With private key from environment
    export WALLET_PRIVATE_KEY="0x..."
    python create_x402_payment.py --requirements payment_requirements.json

    # Copy to clipboard
    python create_x402_payment.py --copy

Example payment requirements input:
{
    "accepts": [{
        "scheme": "eip3009",
        "network": "base-sepolia",
        "token": "USDC",
        "maxAmountRequired": "10000",
        "pay_to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        "max_timeout_seconds": 600
    }]
}
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich.table import Table
    from rich import print as rprint
except ImportError:
    print("Error: rich library not found. Install with: pip install rich")
    sys.exit(1)

try:
    from eth_account import Account
    from eth_account.messages import encode_typed_data
except ImportError:
    print("Error: eth-account library not found. Install with: pip install eth-account")
    sys.exit(1)

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

console = Console()

# Network configurations
NETWORKS = {
    'base-sepolia': {
        'chainId': 84532,
        'usdcAddress': '0x036CbD53842c5426634e7929541eC2318f3dCF7e',
        'name': 'Base Sepolia (Testnet)'
    },
    'base': {
        'chainId': 8453,
        'usdcAddress': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        'name': 'Base (Mainnet)'
    },
    'ethereum': {
        'chainId': 1,
        'usdcAddress': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'name': 'Ethereum (Mainnet)'
    },
    'ethereum-sepolia': {
        'chainId': 11155111,
        'usdcAddress': '0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238',
        'name': 'Ethereum Sepolia (Testnet)'
    }
}


def create_eip3009_authorization(account, payment_requirement):
    """Create EIP-3009 authorization for USDC payment.
    
    Args:
        account: eth_account.Account instance
        payment_requirement: Payment requirement dict from agent
        
    Returns:
        dict: Signed authorization with v, r, s
    """
    network = payment_requirement['network']
    network_config = NETWORKS.get(network)
    
    if not network_config:
        raise ValueError(f"Unsupported network: {network}")
    
    # Create authorization parameters
    from_address = account.address
    to_address = payment_requirement['pay_to']
    value = payment_requirement['maxAmountRequired']
    valid_after = 0
    valid_before = int(time.time()) + payment_requirement.get('max_timeout_seconds', 600)
    nonce = os.urandom(32).hex()
    
    # EIP-712 domain
    domain = {
        'name': 'USD Coin',
        'version': '2',
        'chainId': network_config['chainId'],
        'verifyingContract': network_config['usdcAddress']
    }
    
    # EIP-712 types
    types = {
        'EIP712Domain': [
            {'name': 'name', 'type': 'string'},
            {'name': 'version', 'type': 'string'},
            {'name': 'chainId', 'type': 'uint256'},
            {'name': 'verifyingContract', 'type': 'address'}
        ],
        'ReceiveWithAuthorization': [
            {'name': 'from', 'type': 'address'},
            {'name': 'to', 'type': 'address'},
            {'name': 'value', 'type': 'uint256'},
            {'name': 'validAfter', 'type': 'uint256'},
            {'name': 'validBefore', 'type': 'uint256'},
            {'name': 'nonce', 'type': 'bytes32'}
        ]
    }
    
    # Message to sign
    message = {
        'from': from_address,
        'to': to_address,
        'value': int(value),
        'validAfter': valid_after,
        'validBefore': valid_before,
        'nonce': f"0x{nonce}"
    }
    
    # Create typed data
    typed_data = {
        'types': types,
        'primaryType': 'ReceiveWithAuthorization',
        'domain': domain,
        'message': message
    }
    
    # Sign
    encoded_data = encode_typed_data(full_message=typed_data)
    signed_message = account.sign_message(encoded_data)
    
    # Return authorization with signature
    return {
        'from': from_address,
        'to': to_address,
        'value': value,
        'validAfter': valid_after,
        'validBefore': valid_before,
        'nonce': f"0x{nonce}",
        'v': signed_message.v,
        'r': hex(signed_message.r),
        's': hex(signed_message.s)
    }


def create_payment_payload(account, payment_requirements):
    """Create complete x402 payment payload.
    
    Args:
        account: eth_account.Account instance
        payment_requirements: Payment requirements from agent
        
    Returns:
        dict: Complete payment payload ready to send
    """
    # Get first accepted payment method
    accepts = payment_requirements.get('accepts', [])
    if not accepts:
        raise ValueError("No payment methods accepted")
    
    payment_req = accepts[0]
    
    # Validate scheme
    if payment_req.get('scheme') != 'eip3009':
        raise ValueError(f"Unsupported scheme: {payment_req.get('scheme')}")
    
    # Create authorization
    authorization = create_eip3009_authorization(account, payment_req)
    
    # Build payment payload
    return {
        'x402.payment.status': 'payment-submitted',
        'x402.payment.payload': {
            'scheme': 'eip3009',
            'network': payment_req['network'],
            'payload': {
                'authorization': authorization
            }
        }
    }


def display_payment_info(payment_requirement, account_address):
    """Display payment information in a nice table."""
    table = Table(title="Payment Information", show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="green")
    
    # Calculate amount in USDC (from atomic units)
    amount_atomic = int(payment_requirement['maxAmountRequired'])
    amount_usdc = amount_atomic / 1_000_000  # USDC has 6 decimals
    
    network_config = NETWORKS.get(payment_requirement['network'], {})
    
    table.add_row("Network", f"{network_config.get('name', payment_requirement['network'])}")
    table.add_row("Token", payment_requirement['token'])
    table.add_row("Amount", f"{amount_usdc:.6f} USDC ({amount_atomic} atomic units)")
    table.add_row("Pay To", payment_requirement['pay_to'])
    table.add_row("Your Address", account_address)
    table.add_row("Timeout", f"{payment_requirement.get('max_timeout_seconds', 600)} seconds")
    
    console.print(table)


def load_payment_requirements(args):
    """Load payment requirements from file or stdin."""
    if args.requirements:
        # Load from file
        with open(args.requirements, 'r') as f:
            data = json.load(f)
    else:
        # Interactive mode
        console.print("\n[bold cyan]Paste the payment requirements JSON[/bold cyan]")
        console.print("[dim](Paste the 'x402.payment.required' object from the agent response)[/dim]")
        console.print("[dim]Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done:[/dim]\n")
        
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        
        json_str = '\n'.join(lines)
        data = json.loads(json_str)
    
    # Handle both formats:
    # 1. Full metadata object with "x402.payment.required" key
    # 2. Just the payment requirements object with "accepts" key
    if 'x402.payment.required' in data:
        return data['x402.payment.required']
    elif 'accepts' in data:
        return data
    else:
        raise ValueError("Invalid payment requirements format. Expected 'accepts' array.")


def get_account(args):
    """Get account from private key."""
    private_key = args.private_key or os.getenv('WALLET_PRIVATE_KEY')
    
    if not private_key:
        console.print("\n[yellow]No private key provided.[/yellow]")
        console.print("[dim]You can provide it via:[/dim]")
        console.print("  1. --private-key argument")
        console.print("  2. WALLET_PRIVATE_KEY environment variable")
        console.print("  3. Enter it now (will not be displayed)\n")
        
        from getpass import getpass
        private_key = getpass("Enter private key (0x...): ")
    
    if not private_key:
        console.print("[red]Error: Private key is required[/red]")
        sys.exit(1)
    
    # Ensure 0x prefix
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
    
    try:
        account = Account.from_key(private_key)
        return account
    except Exception as e:
        console.print(f"[red]Error loading account:[/red] {e}")
        sys.exit(1)


def main():
    """Generate x402 payment payload for Bindu agents."""
    parser = argparse.ArgumentParser(
        description="Create x402 payment payload for Bindu agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python create_x402_payment.py
  
  # From file
  python create_x402_payment.py --requirements payment_req.json
  
  # With private key
  python create_x402_payment.py --private-key 0x1234...
  
  # Copy to clipboard
  python create_x402_payment.py --copy
  
  # Save to file
  python create_x402_payment.py --output payment.json
        """
    )
    
    parser.add_argument(
        '--requirements',
        '-r',
        help='Path to JSON file containing payment requirements'
    )
    parser.add_argument(
        '--private-key',
        '-k',
        help='Wallet private key (or use WALLET_PRIVATE_KEY env var)'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Save payment payload to file'
    )
    parser.add_argument(
        '--copy',
        '-c',
        action='store_true',
        help='Copy payment payload to clipboard'
    )
    parser.add_argument(
        '--pretty',
        '-p',
        action='store_true',
        default=True,
        help='Pretty print JSON output (default: True)'
    )
    
    args = parser.parse_args()
    
    try:
        # Display header
        console.print(Panel.fit(
            "[bold cyan]x402 Payment Payload Generator[/bold cyan]\n"
            "[dim]Create signed payment authorizations for Bindu agents[/dim]",
            border_style="cyan"
        ))
        
        # Load payment requirements
        console.print("\n[bold]Step 1:[/bold] Loading payment requirements...")
        payment_requirements = load_payment_requirements(args)
        console.print("[green]✓[/green] Payment requirements loaded\n")
        
        # Get account
        console.print("[bold]Step 2:[/bold] Loading wallet...")
        account = get_account(args)
        console.print(f"[green]✓[/green] Wallet loaded: {account.address}\n")
        
        # Display payment info
        console.print("[bold]Step 3:[/bold] Payment details:")
        display_payment_info(payment_requirements['accepts'][0], account.address)
        
        # Confirm
        if not Confirm.ask("\n[bold]Proceed with payment authorization?[/bold]", default=True):
            console.print("[yellow]Cancelled[/yellow]")
            sys.exit(0)
        
        # Create payment payload
        console.print("\n[bold]Step 4:[/bold] Creating payment authorization...")
        payment_payload = create_payment_payload(account, payment_requirements)
        console.print("[green]✓[/green] Payment authorization created\n")
        
        # Format output
        if args.pretty:
            json_output = json.dumps(payment_payload, indent=2)
        else:
            json_output = json.dumps(payment_payload)
        
        # Display result
        console.print(Panel(
            Syntax(json_output, "json", theme="monokai", line_numbers=False),
            title="[bold green]Payment Payload[/bold green]",
            border_style="green"
        ))
        
        # Save to file
        if args.output:
            with open(args.output, 'w') as f:
                f.write(json_output)
            console.print(f"\n[green]✓[/green] Saved to: {args.output}")
        
        # Copy to clipboard
        if args.copy:
            if CLIPBOARD_AVAILABLE:
                pyperclip.copy(json_output)
                console.print("[green]✓[/green] Copied to clipboard")
            else:
                console.print("[yellow]⚠[/yellow] Clipboard not available (install pyperclip)")
        
        # Usage instructions
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("1. Copy the payment payload above")
        console.print("2. Add it to your message metadata:")
        console.print("[dim]   message['metadata'] = <payment_payload>[/dim]")
        console.print("3. Send the message to the agent")
        console.print("4. Agent will validate payment and execute your task\n")
        
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing JSON:[/red] {e}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
