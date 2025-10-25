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
    from web3 import Web3
except ImportError:
    print("Error: eth-account/web3 libraries not found. Install with: pip install eth-account web3")
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
        'name': 'Base Sepolia (Testnet)',
        'rpc': 'https://sepolia.base.org'
    },
    'base': {
        'chainId': 8453,
        'usdcAddress': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        'name': 'Base (Mainnet)',
        'rpc': 'https://mainnet.base.org'
    },
    'ethereum': {
        'chainId': 1,
        'usdcAddress': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'name': 'Ethereum (Mainnet)',
        'rpc': 'https://eth.llamarpc.com'
    },
    'ethereum-sepolia': {
        'chainId': 11155111,
        'usdcAddress': '0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238',
        'name': 'Ethereum Sepolia (Testnet)',
        'rpc': 'https://ethereum-sepolia-rpc.publicnode.com'
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
    
    # Return authorization (matching x402 EIP3009Authorization type)
    # Note: v, r, s are NOT part of authorization - they go in the signature field
    return {
        'from': from_address,
        'to': to_address,
        'value': value,
        'validAfter': str(valid_after),  # x402 expects string
        'validBefore': str(valid_before),  # x402 expects string
        'nonce': f"0x{nonce}",
        # Store signature components for later use
        '_signature_v': signed_message.v,
        '_signature_r': hex(signed_message.r),
        '_signature_s': hex(signed_message.s)
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
    
    # Extract signature components for x402 PaymentPayload structure
    signature = f"{authorization['r']}{authorization['s'][2:]}{hex(authorization['v'])[2:]}"
    
    # Build payment payload matching x402 PaymentPayload type
    return {
        'x402.payment.status': 'payment-submitted',
        'x402.payment.payload': {
            'x402_version': 1,  # Required by x402 PaymentPayload type
            'scheme': 'eip3009',
            'network': payment_req['network'],
            'payload': {
                'signature': signature,  # Required at payload level
                'authorization': authorization
            }
        }
    }


def get_usdc_balance(address, network):
    """Get USDC balance for an address on a specific network.
    
    Args:
        address: Wallet address
        network: Network name (e.g., 'base-sepolia')
        
    Returns:
        tuple: (balance_atomic, balance_usdc) or (None, None) if error
    """
    network_config = NETWORKS.get(network)
    if not network_config or 'rpc' not in network_config:
        return None, None
    
    # Try multiple RPC endpoints for Base Sepolia
    rpc_endpoints = [network_config['rpc']]
    if network == 'base-sepolia':
        rpc_endpoints.extend([
            'https://base-sepolia.blockpi.network/v1/rpc/public',
            'https://base-sepolia-rpc.publicnode.com',
            'https://sepolia.base.org'
        ])
    
    for rpc_url in rpc_endpoints:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
            
            # Check connection
            if not w3.is_connected():
                continue
            
            # ERC-20 balanceOf ABI
            balance_of_abi = [{
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }]
            
            usdc_contract = w3.eth.contract(
                address=Web3.to_checksum_address(network_config['usdcAddress']),
                abi=balance_of_abi
            )
            
            balance_atomic = usdc_contract.functions.balanceOf(
                Web3.to_checksum_address(address)
            ).call()
            
            balance_usdc = balance_atomic / 1_000_000  # USDC has 6 decimals
            
            # Success - show which RPC worked
            if balance_atomic > 0:
                console.print(f"[dim]Connected via: {rpc_url}[/dim]")
            
            return balance_atomic, balance_usdc
            
        except Exception as e:
            # Try next RPC endpoint
            if rpc_url == rpc_endpoints[-1]:  # Last attempt
                console.print(f"[yellow]Warning: Could not fetch balance from any RPC[/yellow]")
                console.print(f"[dim]Last error: {e}[/dim]")
            continue
    
    return None, None


def display_payment_info(payment_requirement, account_address):
    """Display payment information in a nice table."""
    table = Table(title="Payment Information", show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="green")
    
    # Calculate amount in USDC (from atomic units)
    amount_atomic = int(payment_requirement['maxAmountRequired'])
    amount_usdc = amount_atomic / 1_000_000  # USDC has 6 decimals
    
    network_config = NETWORKS.get(payment_requirement['network'], {})
    network = payment_requirement['network']
    
    table.add_row("Network", f"{network_config.get('name', network)}")
    table.add_row("Token", payment_requirement['token'])
    table.add_row("Amount", f"{amount_usdc:.6f} USDC ({amount_atomic} atomic units)")
    table.add_row("Pay To", payment_requirement['pay_to'])
    table.add_row("Your Address", account_address)
    
    # Get and display balance
    balance_atomic, balance_usdc = get_usdc_balance(account_address, network)
    if balance_usdc is not None:
        sufficient = balance_usdc >= amount_usdc
        status = "[green]✓ Sufficient[/green]" if sufficient else "[red]✗ Insufficient[/red]"
        table.add_row("Your Balance", f"{balance_usdc:.6f} USDC {status}")
    else:
        table.add_row("Your Balance", "[dim]Unable to fetch[/dim]")
    
    table.add_row("Timeout", f"{payment_requirement.get('max_timeout_seconds', 600)} seconds")
    
    console.print(table)


def load_payment_requirements(args):
    """Load payment requirements from file or stdin."""
    if args.sample_payment_requirements:
        # Load from file
        with open(args.sample_payment_requirements, 'r') as f:
            sample_payment_requirements = json.load(f)
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
        sample_payment_requirements = json.loads(json_str)
    
    # Handle both formats:
    # 1. Full metadata object with "x402.payment.required" key
    # 2. Just the payment requirements object with "accepts" key
    if 'x402.payment.required' in sample_payment_requirements:
        return sample_payment_requirements['x402.payment.required']
    elif 'accepts' in sample_payment_requirements:
        return sample_payment_requirements
    else:
        raise ValueError("Invalid payment requirements format. Expected 'accepts' array.")


def get_account(args):
    """Get account from private key."""
    private_key = None
    
    # Try loading from wallet file if provided
    if args.sample_test_wallet and Path(args.sample_test_wallet).exists():
        try:
            with open(args.sample_test_wallet, 'r') as f:
                private_key = json.load(f).get('private_key')
                if private_key:
                    console.print(f"[green]✓[/green] Loaded from {Path(args.sample_test_wallet).name}")
        except Exception as e:
            console.print(f"[yellow]Warning: {e}[/yellow]")
    
    # Fallback to env var or prompt
    if not private_key:
        private_key = os.getenv('WALLET_PRIVATE_KEY')
        if not private_key:
            from getpass import getpass
            console.print("\n[yellow]Enter private key (or set WALLET_PRIVATE_KEY)[/yellow]")
            private_key = getpass("Private key (0x...): ")
    
    if not private_key:
        console.print("[red]Error: Private key required[/red]")
        sys.exit(1)
    
    # Ensure 0x prefix and create account
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
    
    try:
        return Account.from_key(private_key)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
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
        '--sample_test_wallet',
        '-s',
        help='Use sample test wallet',
        default='examples/test_wallet.json'
    )
    
    parser.add_argument(
        '--sample_payment_requirements',
        '-r',
        help='Use sample payment requirements',
        default='examples/sample_payment_requirements.json'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Save payment payload to file',
        default='examples/payment_payload.json'
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
