"""Certificate manager for mTLS in Pebbling agents using Sheldon CA."""

import os
import datetime
import json
import requests
from typing import Dict, Tuple, Optional, Any
import ipaddress
import socket
import jwt
import base64
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from loguru import logger

from pebbling.security.did_manager import DIDManager


class CertificateManager:
    """Certificate manager for mTLS in Pebbling agents using Sheldon CA.
    
    This class manages certificates for secure mTLS connections between agents
    by integrating with Sheldon CA for certificate issuance and verification.
    The certificates are linked to agent DIDs to provide a unified identity system.
    """

    def __init__(
        self, 
        did_manager: DIDManager,
        cert_path: Optional[str] = None,
        sheldon_ca_url: Optional[str] = None,
    ):
        """Initialize the certificate manager.
        
        Args:
            did_manager: The DID manager for the agent
            cert_path: Path to store/load certificates (defaults to 'certs/{did_id}/')
            sheldon_ca_url: URL of the Sheldon CA service
        """
        self.did_manager = did_manager
        self.did = did_manager.get_did()
        self.did_id = self.did.split(':')[-1]
        
        # Set default cert path if not provided
        if cert_path is None:
            cert_path = f"certs/{self.did_id}"
            
        # Set up paths for certificates and related files
        self.cert_path = cert_path
        self.sheldon_public_cert_path = os.path.join(cert_path, "sheldon_public_cert.pem")
        self.csr_path = os.path.join(cert_path, "agent_csr.pem")
        self.client_cert_path = os.path.join(cert_path, "client_cert.pem")
        
        # Create the cert directory if it doesn't exist
        os.makedirs(cert_path, exist_ok=True)
        
        # Sheldon CA configuration
        self.sheldon_ca_url = sheldon_ca_url or os.environ.get('SHELDON_CA_URL', 'http://localhost:19190')
              
    def _save_sheldon_token(self, token_data: Dict[str, Any]) -> None:
        """Save the Sheldon CA token to file."""
        try:
            with open(self.token_path, 'w') as f:
                json.dump(token_data, f, indent=2)
            self.sheldon_token = token_data.get('token')
            expiry = token_data.get('token_expires', 'unknown')
            logger.info(f"Saved Sheldon token (expires {expiry})")
        except Exception as e:
            logger.error(f"Error saving Sheldon token: {e}")
    
    def _create_csr(self) -> None:
        """Create a Certificate Signing Request (CSR).
        
        Args:
            csr_path: Path to save the CSR
        """
        logger.info(f"Creating CSR for agent DID {self.did}")
        
        # Get the private key from the DID manager
        private_key = self.did_manager.get_private_key_object()
        
        # Create a name with the agent's DID
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"Pebbling Agent {self.did_id}"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Pebbling Framework"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, self.did)
        ])
        
        # Create SAN extension with localhost and local IP
        alt_names = [
            x509.DNSName("localhost")
        ]
        
        # Add local IP address
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            alt_names.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
            logger.info(f"Added local IP {local_ip} to CSR")
        except Exception as e:
            logger.warning(f"Could not add local IP to CSR: {e}")
            
        # Add loopback IP
        alt_names.append(x509.IPAddress(ipaddress.IPv4Address('127.0.0.1')))
        
        # Create CSR
        csr = x509.CertificateSigningRequestBuilder().subject_name(
            subject
        ).add_extension(
            x509.SubjectAlternativeName(alt_names),
            critical=False
        ).sign(private_key, hashes.SHA256())
        
        # Save CSR
        with open(self.csr_path, "wb") as f:
            f.write(csr.public_bytes(serialization.Encoding.PEM))
        logger.info(f"CSR created and saved to {self.csr_path}")
    
    def create_csr_for_sheldon(self) -> str:
        """Create a CSR for use with Sheldon CA.
        
        Returns:
            Path to CSR
        """
        logger.info("Creating CSR for Sheldon CA certificate issuance")
        # Create CSR using DID key
        self._create_csr()
        
        return self.csr_path
        
    def _generate_jwt_token(self, expiry_hours: int = 1) -> str:
        """Generate a JWT token signed by the agent's private key.
        
        Args:
            expiry_hours: Token expiry in hours
            
        Returns:
            JWT token string
        """
        logger.info(f"Generating JWT token for DID {self.did}")
        
        # Get the PEM string for the private key rather than the object
        # This is what the PyJWT library expects
        private_key = self.did_manager.get_private_key()
        
        # Create the payload with required claims
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            "did": self.did,
            "sub": self.did,
            "iat": int(now.timestamp()),  # Use integer timestamps for better compatibility
            "exp": int((now + datetime.timedelta(hours=expiry_hours)).timestamp()),
        }
        
        logger.info(f"JWT payload: {payload}")
        
        # Sign the token with the private key
        try:
            logger.info("Signing JWT with RS256")
            token = jwt.encode(
                payload,
                private_key,  # Use the PEM string directly
                algorithm="RS256"
            )
            logger.info("JWT signed successfully")
            return token
        except Exception as e:
            logger.error(f"Failed to generate JWT token: {e}")
            # Try a different approach - load the key ourselves
            try:
                logger.info("Trying alternate JWT signing approach")
                from cryptography.hazmat.primitives.serialization import load_pem_private_key
                
                # Load the private key from PEM format if it's a string
                if isinstance(private_key, str):
                    key_obj = load_pem_private_key(
                        private_key.encode('utf-8'),
                        password=None
                    )
                    token = jwt.encode(
                        payload,
                        key_obj,
                        algorithm="RS256"
                    )
                    logger.info("Alternate JWT signing succeeded")
                    return token
            except Exception as e2:
                logger.error(f"Alternative JWT signing failed: {e2}")
            
            raise ValueError(f"Failed to generate JWT token: {e}")
        
    def fetch_ca_certificate(self) -> Dict[str, Any]:
        """Fetch the Sheldon CA root certificate.
        
        Returns:
            Dictionary with success status and data/error
        """
        try:
            logger.info(f"Fetching CA certificate from {self.sheldon_ca_url}/issue/public-certificate")
            headers = {}
            
            response = requests.get(
                f"{self.sheldon_ca_url}/issue/public-certificate",
                headers=headers
            )
            
            if response.status_code != 200:
                error_msg = f"Failed to fetch CA certificate: HTTP {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            response_data = response.json()
            ca_certificate = response_data.get('certificate')
            
            if not ca_certificate:
                error_msg = "No CA certificate returned by Sheldon CA"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            # Save CA certificate
            with open(self.sheldon_public_cert_path, "w") as f:
                f.write(ca_certificate)
            logger.info(f"CA certificate saved to {self.sheldon_public_cert_path}")
            
            return {"success": True, "data": {"ca_cert_path": self.sheldon_public_cert_path}}
        except Exception as e:
            error_msg = f"Error fetching CA certificate: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
    def issue_certificate(self) -> Dict[str, Any]:
        """Issue a certificate from Sheldon CA using the agent's DID.
        
        Returns:
            Dictionary with success status and data/error information
        """
        try:
            logger.info("Requesting certificate from Sheldon CA")
            
            # Create CSR if not exists
            if not os.path.exists(self.csr_path):
                logger.info("No CSR found, creating a new one")
                self.create_csr_for_sheldon()
                
            # Read CSR file
            with open(self.csr_path, "rb") as f:
                csr_data = f.read()
            
            # Generate JWT token for authentication
            jwt_token = self._generate_jwt_token()
            
            # Send request to Sheldon CA
            headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {jwt_token}'
            }
            
            # Prepare multipart form data
            files = {
                'csr': ('agent_csr.pem', csr_data, 'application/x-pem-file'),
                'agent_did': (None, self.did, 'text/plain')
            }
            
            logger.info(f"Sending certificate issuance request to {self.sheldon_ca_url}/issue/")
            response = requests.post(f"{self.sheldon_ca_url}/issue/", 
                                    headers=headers, 
                                    files=files)
            
            if response.status_code != 200:
                error_msg = f"Failed to issue certificate: HTTP {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
            response_data = response.json()
            certificate_pem = response_data.get('certificate')
            
            if not certificate_pem:
                error_msg = "No certificate returned by Sheldon CA"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
            # Save certificate
            with open(self.client_cert_path, "w") as f:
                f.write(certificate_pem)
            logger.info(f"Certificate saved to {self.client_cert_path}")

            return {"success": True, "data": {"cert_path": self.client_cert_path}}
            
        except Exception as e:
            error_msg = f"Error requesting certificate from Sheldon CA: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def verify_certificate(self, certificate_pem: str) -> bool:
        """Verify certificate with Sheldon CA and get token.
        
        Args:
            certificate_pem: PEM-encoded certificate
            
        Returns:
            True if certificate is valid, False otherwise
        """
        logger.info("Verifying certificate with Sheldon CA")
        try:
            # Generate JWT token for authentication
            jwt_token = self._generate_jwt_token()
            
            # Send verification request to Sheldon CA
            headers = {
                'Authorization': f'Bearer {jwt_token}',
                'Content-Type': 'application/json',
                'X-API-Key': self.sheldon_api_key
            }
            
            data = {
                'agent_did': self.did,
                'certificate': certificate_pem
            }
            
            logger.info(f"Sending verification request to {self.sheldon_ca_url}/verify/")
            response = requests.post(f"{self.sheldon_ca_url}/verify/", 
                                    headers=headers, 
                                    json=data)
            
            if response.status_code != 200:
                logger.error(f"Failed to verify certificate: HTTP {response.status_code} - {response.text}")
                return False
                
            response_data = response.json()
            
            # Check verification result
            if not response_data.get('valid', False):
                logger.error("Certificate verification failed: not valid")
                return False
                
            # Save token
            if 'token' in response_data:
                logger.info("Received token from Sheldon CA")
                self._save_sheldon_token(response_data)
                
            logger.info("Certificate verified successfully")
            return True
                
        except Exception as e:
            logger.error(f"Error verifying certificate with Sheldon CA: {e}")
            return False

    def extract_did_from_certificate(self, cert_pem: str) -> Dict[str, Any]:
        """Extract DID and other information from a certificate.
        
        Args:
            cert_pem: PEM-encoded certificate
            
        Returns:
            Dictionary with certificate information including DID
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode('utf-8'))
            
            # Extract DID from OU field
            subject = cert.subject
            ou = None
            for attr in subject:
                if attr.oid == NameOID.ORGANIZATIONAL_UNIT_NAME:
                    ou = attr.value
                    break
                    
            if not ou:
                raise ValueError("No DID found in certificate")
                
            return {
                "did": ou,
                "subject": str(subject),
                "issuer": str(cert.issuer),
                "not_before": cert.not_valid_before,
                "not_after": cert.not_valid_after,
            }
        except Exception as e:
            logger.error(f"Error extracting DID from certificate: {e}")
            raise
            
    def is_sheldon_token_valid(self) -> bool:
        """Check if the Sheldon token is valid.
        
        Returns:
            True if token is valid, False otherwise
        """
        if not self.sheldon_token:
            return False
            
        # Check if token file exists and load expiry date
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'r') as f:
                    token_data = json.load(f)
                    
                expiry = token_data.get('token_expires')
                if expiry:
                    expiry_date = datetime.datetime.fromisoformat(expiry.replace('+00:00', 'Z'))
                    # Return True if token is not expired (with 1 hour margin)
                    margin = datetime.timedelta(hours=1)
                    return expiry_date > (datetime.datetime.now(datetime.timezone.utc) + margin)
            except Exception as e:
                logger.error(f"Error checking token validity: {e}")
                
        return False
        
    def get_server_context(self) -> Dict[str, str]:
        """Get server certificate context for SSL connections.
        
        For simplicity, we use the same cert for both client and server.
        
        Returns:
            Dict with certfile, keyfile, and ca_certs paths
        """
        # Simply reuse client certificates for now
        return self.get_client_context()
        
    def get_client_context(self) -> Dict[str, str]:
        """Get client certificate context for SSL connections.
        
        Returns:
            Dict with certfile, keyfile, and ca_certs paths
        """
        # Extract private key from DID JSON file and save to a PEM file
        try:
            # Create client key path if it doesn't exist
            client_key_path = os.path.join(self.cert_path, "client_key.pem")
            
            # Extract PEM key from JSON file
            private_key_pem = self.did_manager.get_private_key()
            
            if private_key_pem and not os.path.exists(client_key_path):
                with open(client_key_path, "w") as f:
                    f.write(private_key_pem)
                logger.info(f"Extracted private key from DID document to {client_key_path}")
        except Exception as e:
            logger.error(f"Error extracting private key from DID document: {e}")
            # Fall back to using the JSON file directly if extraction fails
            client_key_path = self.did_manager.key_path
        
        return {
            "certfile": self.client_cert_path,
            "keyfile": client_key_path,
            "ca_certs": self.sheldon_public_cert_path
        }

    def get_certificate_info(self) -> Dict[str, str]:
        """Get certificate information for sharing with other agents.
        
        Returns:
            Dictionary with agent ID, DID, server certificate, and CA certificate
        """
        # Get certificate paths
        server_context = self.get_server_context()
        
        # Read certificate files
        server_cert = ""
        ca_cert = ""
        
        try:
            with open(server_context["certfile"], "r") as f:
                server_cert = f.read()
        except Exception as e:
            logger.error(f"Error reading server certificate: {e}")
            
        try:
            with open(server_context["ca_certs"], "r") as f:
                ca_cert = f.read()
        except Exception as e:
            logger.error(f"Error reading CA certificate: {e}")
            
        # Return certificate info
        return {
            "agent_id": self.did_id,
            "did": self.did,
            "server_cert": server_cert,
            "ca_cert": ca_cert
        }
