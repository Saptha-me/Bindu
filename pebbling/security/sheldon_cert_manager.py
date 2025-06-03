"""Certificate manager for mTLS in pebbling agents using Sheldon CA."""

import os
import datetime
import tempfile
import requests
import json
from typing import Dict, Tuple, Optional, Any
import ipaddress
import socket
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import subprocess

from pebbling.security.did_manager import DIDManager


class SheldonCertificateManager:
    """Certificate manager for mTLS in pebbling agents using Sheldon CA.
    
    This class manages certificates for secure mTLS connections between agents
    by interacting with the Sheldon centralized CA authority.
    The certificates are linked to agent DIDs to provide a unified identity system.
    """

    def __init__(
        self, 
        did_manager: DIDManager,
        sheldon_url: str = "http://localhost:8000",
        cert_path: Optional[str] = None
    ):
        """Initialize the certificate manager.
        
        Args:
            did_manager: The DID manager for the agent
            sheldon_url: URL of the Sheldon CA service
            cert_path: Path to store/load certificates (defaults to 'certs/{did_id}/')
        """
        self.did_manager = did_manager
        self.did = did_manager.get_did()
        self.did_id = self.did.split(':')[-1]
        self.sheldon_url = sheldon_url
        
        # Set default cert path if not provided
        if cert_path is None:
            cert_path = f"certs/{self.did_id}"
            
        self.cert_path = cert_path
        self.server_cert_path = os.path.join(cert_path, "server.crt")
        self.server_key_path = os.path.join(cert_path, "server.key")
        self.client_cert_path = os.path.join(cert_path, "client.crt")
        self.client_key_path = os.path.join(cert_path, "client.key")
        self.root_ca_path = os.path.join(cert_path, "root_ca.crt")
        
        # Verification tokens for other agents
        self.verification_tokens: Dict[str, str] = {}
        
        # Create the cert directory if it doesn't exist
        os.makedirs(cert_path, exist_ok=True)
        
        # Load or create certificates
        self._load_or_create_certificates()
    
    def _load_or_create_certificates(self) -> None:
        """Load existing certificates or create new ones if they don't exist."""
        # Check if we need to create server certificates
        if not (os.path.exists(self.server_cert_path) and os.path.exists(self.server_key_path)):
            self._create_server_certificate()
            
        # Check if we need to create client certificates
        if not (os.path.exists(self.client_cert_path) and os.path.exists(self.client_key_path)):
            self._create_client_certificate()
    
    def _generate_csr_with_step(self, common_name: str, key_path: str, csr_path: str, is_server: bool = False) -> None:
        """Generate a Certificate Signing Request using step-cli.
        
        Args:
            common_name: Common name for the certificate
            key_path: Path to save the private key
            csr_path: Path to save the CSR
            is_server: Whether this is a server certificate
        """
        # Generate a private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Save private key
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Create a name with the agent's DID
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Pebbling Framework"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, self.did)
        ])
        
        # Create SAN extension with localhost, local IP, and the agent's DID
        alt_names = [
            x509.DNSName("localhost"),
            x509.DNSName(self.did)  # Include the DID as a SAN
        ]
        
        # Add local IP address
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            alt_names.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
        except Exception:
            pass  # Ignore if we can't get the local IP
            
        # Add loopback IP
        alt_names.append(x509.IPAddress(ipaddress.IPv4Address('127.0.0.1')))
        
        # Create CSR
        csr_builder = x509.CertificateSigningRequestBuilder().subject_name(
            subject
        ).add_extension(
            x509.SubjectAlternativeName(alt_names),
            critical=False
        )
        
        # Add key usage based on certificate type
        if is_server:
            csr_builder = csr_builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH
                ]),
                critical=False
            )
        else:
            csr_builder = csr_builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH
                ]),
                critical=False
            )
        
        # Sign the CSR
        csr = csr_builder.sign(private_key, hashes.SHA256())
        
        # Save CSR
        with open(csr_path, "wb") as f:
            f.write(csr.public_bytes(serialization.Encoding.PEM))
    
    def _request_certificate_from_sheldon(self, csr_path: str, cert_path: str) -> bool:
        """Request a certificate from the Sheldon CA service.
        
        Args:
            csr_path: Path to the CSR file
            cert_path: Path to save the certificate
            
        Returns:
            True if certificate was successfully issued, False otherwise
        """
        try:
            # Read CSR file
            with open(csr_path, "rb") as f:
                csr_data = f.read()
            
            # Send CSR to Sheldon
            files = {'csr': ('csr.pem', csr_data)}
            response = requests.post(f"{self.sheldon_url}/issue-certificate", files=files)
            
            if response.status_code == 200:
                cert_data = response.json().get('certificate', '')
                
                # Save the certificate
                with open(cert_path, "w") as f:
                    f.write(cert_data)
                
                return True
            else:
                print(f"Failed to get certificate from Sheldon: {response.text}")
                return False
        except Exception as e:
            print(f"Error requesting certificate from Sheldon: {e}")
            return False
    
    def _create_server_certificate(self) -> bool:
        """Create a server certificate through the Sheldon CA.
        
        Returns:
            True if certificate was successfully created, False otherwise
        """
        try:
            # Create temp file for CSR
            with tempfile.NamedTemporaryFile(suffix='.csr', delete=False) as temp_csr:
                csr_path = temp_csr.name
            
            # Generate CSR
            self._generate_csr_with_step(
                f"Pebbling Server {self.did_id}", 
                self.server_key_path, 
                csr_path,
                is_server=True
            )
            
            # Request certificate from Sheldon
            success = self._request_certificate_from_sheldon(csr_path, self.server_cert_path)
            
            # Clean up temp file
            if os.path.exists(csr_path):
                os.unlink(csr_path)
                
            return success
        except Exception as e:
            print(f"Error creating server certificate: {e}")
            return False
    
    def _create_client_certificate(self) -> bool:
        """Create a client certificate through the Sheldon CA.
        
        Returns:
            True if certificate was successfully created, False otherwise
        """
        try:
            # Create temp file for CSR
            with tempfile.NamedTemporaryFile(suffix='.csr', delete=False) as temp_csr:
                csr_path = temp_csr.name
            
            # Generate CSR
            self._generate_csr_with_step(
                f"Pebbling Client {self.did_id}", 
                self.client_key_path, 
                csr_path,
                is_server=False
            )
            
            # Request certificate from Sheldon
            success = self._request_certificate_from_sheldon(csr_path, self.client_cert_path)
            
            # Clean up temp file
            if os.path.exists(csr_path):
                os.unlink(csr_path)
                
            return success
        except Exception as e:
            print(f"Error creating client certificate: {e}")
            return False

    async def verify_peer_certificate(self, cert_pem: str, peer_id: str) -> bool:
        """Verify a peer certificate through the Sheldon CA service.
        
        Args:
            cert_pem: PEM-encoded certificate
            peer_id: ID of the peer agent
            
        Returns:
            True if certificate is valid, False otherwise
        """
        try:
            # Save cert to temporary file
            with tempfile.NamedTemporaryFile(suffix='.crt', delete=False) as temp_cert:
                temp_cert.write(cert_pem.encode('utf-8'))
                cert_path = temp_cert.name
            
            # Send certificate to Sheldon for verification
            files = {'cert': ('cert.pem', open(cert_path, 'rb'))}
            response = requests.post(f"{self.sheldon_url}/verify-certificate", files=files)
            
            # Clean up temp file
            os.unlink(cert_path)
            
            if response.status_code == 200:
                # Store the verification token
                verification_token = response.json().get('verification_token', '')
                if verification_token:
                    self.verification_tokens[peer_id] = verification_token
                    return True
            
            return False
        except Exception as e:
            print(f"Error verifying certificate: {e}")
            return False
    
    def get_verification_token(self, peer_id: str) -> str:
        """Get the verification token for a peer agent.
        
        Args:
            peer_id: ID of the peer agent
            
        Returns:
            The verification token, or empty string if not available
        """
        return self.verification_tokens.get(peer_id, '')
        
    def get_certificate_info(self) -> Dict[str, str]:
        """Get information about this agent's certificates.
        
        Returns:
            Dictionary with certificate information
        """
        server_cert_pem = ""
        if os.path.exists(self.server_cert_path):
            with open(self.server_cert_path, "r") as f:
                server_cert_pem = f.read()
        
        return {
            "agent_id": self.did_id,
            "did": self.did,
            "server_cert": server_cert_pem
        }
    
    def get_client_context(self) -> Dict[str, str]:
        """Get SSL context parameters for client connections.
        
        Returns:
            Dictionary with client certificate paths
        """
        return {
            "certfile": self.client_cert_path,
            "keyfile": self.client_key_path,
            "ca_certs": self.root_ca_path if os.path.exists(self.root_ca_path) else None
        }
    
    def get_server_context(self) -> Dict[str, str]:
        """Get SSL context parameters for server connections.
        
        Returns:
            Dictionary with server certificate paths
        """
        return {
            "certfile": self.server_cert_path,
            "keyfile": self.server_key_path,
            "ca_certs": self.root_ca_path if os.path.exists(self.root_ca_path) else None
        }
    
    def download_root_ca(self) -> bool:
        """Download the root CA certificate from Sheldon.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.get(f"{self.sheldon_url}/root-ca")
            if response.status_code == 200:
                with open(self.root_ca_path, "wb") as f:
                    f.write(response.content)
                return True
            return False
        except Exception as e:
            print(f"Error downloading root CA: {e}")
            return False
