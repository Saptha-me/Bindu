"""Certificate manager for mTLS in pebbling agents."""

import os
import json
import datetime
from typing import Dict, Tuple, Optional, Any
import ipaddress
import socket
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509.extensions import SubjectAlternativeName

from pebbling.security.did_manager import DIDManager


class CertificateManager:
    """Certificate manager for mTLS in pebbling agents.
    
    This class manages certificates for secure mTLS connections between agents.
    The certificates are linked to agent DIDs to provide a unified identity system.
    """

    def __init__(
        self, 
        did_manager: DIDManager,
        cert_path: Optional[str] = None,
        cert_validity_days: int = 365
    ):
        """Initialize the certificate manager.
        
        Args:
            did_manager: The DID manager for the agent
            cert_path: Path to store/load certificates (defaults to 'certs/{did_id}/')
            cert_validity_days: Number of days the certificate is valid for
        """
        self.did_manager = did_manager
        self.did = did_manager.get_did()
        self.did_id = self.did.split(':')[-1]
        
        # Set default cert path if not provided
        if cert_path is None:
            cert_path = f"certs/{self.did_id}"
            
        self.cert_path = cert_path
        self.ca_cert_path = os.path.join(cert_path, "ca.crt")
        self.ca_key_path = os.path.join(cert_path, "ca.key")
        self.server_cert_path = os.path.join(cert_path, "server.crt")
        self.server_key_path = os.path.join(cert_path, "server.key")
        self.client_cert_path = os.path.join(cert_path, "client.crt")
        self.client_key_path = os.path.join(cert_path, "client.key")
        
        # Create the cert directory if it doesn't exist
        os.makedirs(cert_path, exist_ok=True)
        
        # Certificate validity period
        self.cert_validity_days = cert_validity_days
        
        # Load or create CA and certificates
        self._load_or_create_certificates()
        
        # Store trusted client certificates from other agents
        self.trusted_certs: Dict[str, x509.Certificate] = {}
    
    def _load_or_create_certificates(self) -> None:
        """Load existing certificates or create new ones if they don't exist."""
        # Check if CA certificate exists
        if os.path.exists(self.ca_cert_path) and os.path.exists(self.ca_key_path):
            # Load existing CA
            self.ca_cert, self.ca_key = self._load_ca()
        else:
            # Create new CA
            self.ca_cert, self.ca_key = self._create_ca()
            
        # Check if server certificate exists
        if os.path.exists(self.server_cert_path) and os.path.exists(self.server_key_path):
            # Load existing server certificate
            self.server_cert, self.server_key = self._load_certificate(self.server_cert_path, self.server_key_path)
        else:
            # Create new server certificate
            self.server_cert, self.server_key = self._create_server_certificate()
            
        # Check if client certificate exists
        if os.path.exists(self.client_cert_path) and os.path.exists(self.client_key_path):
            # Load existing client certificate
            self.client_cert, self.client_key = self._load_certificate(self.client_cert_path, self.client_key_path)
        else:
            # Create new client certificate
            self.client_cert, self.client_key = self._create_client_certificate()
    
    def _create_ca(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Create a Certificate Authority certificate.
        
        Returns:
            Tuple of (CA certificate, CA private key)
        """
        # Generate key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Create a name with the agent's DID
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"Pebbling Agent CA {self.did_id}"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Pebbling Framework"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, self.did)
        ])
        
        # Create certificate
        certificate = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=self.cert_validity_days * 2)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        ).sign(private_key, hashes.SHA256())
        
        # Save certificate and key
        with open(self.ca_cert_path, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))
            
        with open(self.ca_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        return certificate, private_key
    
    def _load_ca(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Load CA certificate and private key.
        
        Returns:
            Tuple of (CA certificate, CA private key)
        """
        with open(self.ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())
            
        with open(self.ca_key_path, "rb") as f:
            ca_key = load_pem_private_key(f.read(), password=None)
            
        return ca_cert, ca_key
    
    def _create_server_certificate(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Create a server certificate signed by the CA.
        
        Returns:
            Tuple of (server certificate, server private key)
        """
        return self._create_certificate(
            common_name=f"Pebbling Server {self.did_id}",
            cert_path=self.server_cert_path,
            key_path=self.server_key_path,
            is_server=True
        )
    
    def _create_client_certificate(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Create a client certificate signed by the CA.
        
        Returns:
            Tuple of (client certificate, client private key)
        """
        return self._create_certificate(
            common_name=f"Pebbling Client {self.did_id}",
            cert_path=self.client_cert_path,
            key_path=self.client_key_path,
            is_server=False
        )
    
    def _create_certificate(
        self, 
        common_name: str,
        cert_path: str,
        key_path: str,
        is_server: bool = False
    ) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Create a certificate signed by the CA.
        
        Args:
            common_name: Common name for the certificate
            cert_path: Path to save the certificate
            key_path: Path to save the private key
            is_server: Whether this is a server certificate
            
        Returns:
            Tuple of (certificate, private key)
        """
        # Generate key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Create a name with the agent's DID
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
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
        except Exception:
            pass  # Ignore if we can't get the local IP
            
        # Add loopback IP
        alt_names.append(x509.IPAddress(ipaddress.IPv4Address('127.0.0.1')))
        
        # Create certificate
        cert_builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            self.ca_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=self.cert_validity_days)
        ).add_extension(
            x509.SubjectAlternativeName(alt_names),
            critical=False
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True
        )
        
        # Add appropriate key usage extensions
        if is_server:
            cert_builder = cert_builder.add_extension(
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
            cert_builder = cert_builder.add_extension(
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
            
        # Sign with CA key
        certificate = cert_builder.sign(self.ca_key, hashes.SHA256())
        
        # Save certificate and key
        with open(cert_path, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))
            
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        return certificate, private_key
    
    def _load_certificate(self, cert_path: str, key_path: str) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Load certificate and private key.
        
        Args:
            cert_path: Path to the certificate
            key_path: Path to the private key
            
        Returns:
            Tuple of (certificate, private key)
        """
        with open(cert_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
            
        with open(key_path, "rb") as f:
            key = load_pem_private_key(f.read(), password=None)
            
        return cert, key
    
    def register_peer_certificate(self, agent_id: str, cert_pem: str) -> None:
        """Register a peer agent's certificate.
        
        Args:
            agent_id: ID of the peer agent
            cert_pem: PEM-encoded certificate
        """
        cert = x509.load_pem_x509_certificate(cert_pem.encode('utf-8'))
        self.trusted_certs[agent_id] = cert
        
        # Save to disk for persistence
        peer_cert_dir = os.path.join(self.cert_path, "peers")
        os.makedirs(peer_cert_dir, exist_ok=True)
        
        with open(os.path.join(peer_cert_dir, f"{agent_id}.crt"), "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    def get_certificate_info(self) -> Dict[str, str]:
        """Get information about this agent's certificates.
        
        Returns:
            Dictionary with certificate information
        """
        server_cert_pem = self.server_cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        ca_cert_pem = self.ca_cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        
        return {
            "agent_id": self.did_id,
            "did": self.did,
            "server_cert": server_cert_pem,
            "ca_cert": ca_cert_pem
        }
    
    def get_client_context(self) -> Dict[str, str]:
        """Get SSL context parameters for client connections.
        
        Returns:
            Dictionary with client certificate paths
        """
        return {
            "certfile": self.client_cert_path,
            "keyfile": self.client_key_path,
            "ca_certs": self.ca_cert_path
        }
    
    def get_server_context(self) -> Dict[str, str]:
        """Get SSL context parameters for server connections.
        
        Returns:
            Dictionary with server certificate paths
        """
        return {
            "certfile": self.server_cert_path,
            "keyfile": self.server_key_path,
            "ca_certs": self.ca_cert_path
        }
    
    def export_certificates(self, export_path: str) -> Dict[str, str]:
        """Export all certificates to a directory.
        
        Args:
            export_path: Directory to export certificates to
            
        Returns:
            Dictionary with paths to exported certificates
        """
        os.makedirs(export_path, exist_ok=True)
        
        # Export CA certificate
        ca_path = os.path.join(export_path, "ca.crt")
        with open(ca_path, "wb") as f:
            f.write(self.ca_cert.public_bytes(serialization.Encoding.PEM))
            
        # Export server certificate
        server_path = os.path.join(export_path, "server.crt")
        with open(server_path, "wb") as f:
            f.write(self.server_cert.public_bytes(serialization.Encoding.PEM))
            
        # Export client certificate
        client_path = os.path.join(export_path, "client.crt")
        with open(client_path, "wb") as f:
            f.write(self.client_cert.public_bytes(serialization.Encoding.PEM))
            
        return {
            "ca_cert": ca_path,
            "server_cert": server_path,
            "client_cert": client_path
        }
    
    def verify_peer_certificate(self, peer_cert_pem: str) -> bool:
        """Verify a peer certificate against trusted certificates.
        
        Args:
            peer_cert_pem: PEM-encoded certificate
            
        Returns:
            True if certificate is trusted, False otherwise
        """
        try:
            peer_cert = x509.load_pem_x509_certificate(peer_cert_pem.encode('utf-8'))
            
            # Check if we directly trust this certificate
            for cert in self.trusted_certs.values():
                if cert.fingerprint(hashes.SHA256()) == peer_cert.fingerprint(hashes.SHA256()):
                    return True
                    
            return False
        except Exception:
            return False
