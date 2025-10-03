"""
TLS Certificate management for secure whisper ASR service.
Handles automatic certificate generation, validation, and renewal.
"""

import os
import ssl
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TLSCertificateManager:
    """Manages TLS certificates for secure connections."""
    
    def __init__(self):
        self.cert_dir = Path(settings.TLS_CERT_PATH).parent
        self.cert_file = Path(settings.TLS_CERT_PATH)
        self.key_file = Path(settings.TLS_KEY_PATH)
        self.cert_days = getattr(settings, 'TLS_CERT_DAYS', 365)
        
    async def initialize(self) -> bool:
        """Initialize TLS certificate system."""
        try:
            # Create certificate directory if it doesn't exist
            self.cert_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
            
            # Check if certificates exist and are valid
            if await self._certificates_exist() and await self._certificates_valid():
                logger.info("Valid TLS certificates found")
                return True
            
            # Generate new certificates if needed
            if settings.TLS_AUTO_GENERATE:
                logger.info("Generating new TLS certificates")
                success = await self._generate_self_signed_certificate()
                if success:
                    logger.info("TLS certificates generated successfully")
                    return True
                else:
                    logger.error("Failed to generate TLS certificates")
                    return False
            else:
                logger.error("TLS certificates not found and auto-generation is disabled")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize TLS certificate system: {e}")
            return False
    
    async def _certificates_exist(self) -> bool:
        """Check if certificate files exist."""
        return self.cert_file.exists() and self.key_file.exists()
    
    async def _certificates_valid(self) -> bool:
        """Check if existing certificates are valid."""
        try:
            if not await self._certificates_exist():
                return False
            
            # Read certificate
            with open(self.cert_file, 'rb') as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data)
            
            # Check if certificate is still valid (not expired)
            now = datetime.utcnow()
            if cert.not_valid_after <= now:
                logger.warning("TLS certificate has expired")
                return False
            
            # Check if certificate expires within 30 days
            if cert.not_valid_after <= now + timedelta(days=30):
                logger.warning("TLS certificate expires within 30 days")
                return False
            
            # Validate private key matches certificate
            with open(self.key_file, 'rb') as f:
                key_data = f.read()
            
            private_key = serialization.load_pem_private_key(key_data, password=None)
            public_key = cert.public_key()
            
            # Compare public key numbers (basic validation)
            if hasattr(private_key, 'public_key'):
                private_public_key = private_key.public_key()
                if (private_public_key.public_numbers().n != 
                    public_key.public_numbers().n):
                    logger.error("Private key does not match certificate")
                    return False
            
            logger.info(f"TLS certificate valid until: {cert.not_valid_after}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating TLS certificates: {e}")
            return False
    
    async def _generate_self_signed_certificate(self) -> bool:
        """Generate self-signed TLS certificate."""
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Create certificate subject
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Whisper ASR Secure"),
                x509.NameAttribute(NameOID.COMMON_NAME, "whisper-asr-secure"),
            ])
            
            # Create certificate
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=self.cert_days)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("whisper-asr-secure"),
                    x509.DNSName("127.0.0.1"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    x509.IPAddress(ipaddress.IPv6Address("::1")),
                ]),
                critical=False,
            ).add_extension(
                x509.KeyUsage(
                    key_cert_sign=False,
                    crl_sign=False,
                    digital_signature=True,
                    key_agreement=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    content_commitment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                ]),
                critical=True,
            ).sign(private_key, hashes.SHA256())
            
            # Write private key
            with open(self.key_file, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Set proper permissions for private key
            os.chmod(self.key_file, 0o600)
            
            # Write certificate
            with open(self.cert_file, 'wb') as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Set proper permissions for certificate
            os.chmod(self.cert_file, 0o644)
            
            logger.info(f"Generated self-signed certificate valid until: {cert.not_valid_after}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate self-signed certificate: {e}")
            return False
    
    async def renew_certificate(self) -> bool:
        """Renew TLS certificate."""
        logger.info("Renewing TLS certificate")
        
        # Backup existing certificates
        if await self._certificates_exist():
            backup_cert = self.cert_file.with_suffix('.pem.backup')
            backup_key = self.key_file.with_suffix('.pem.backup')
            
            try:
                self.cert_file.rename(backup_cert)
                self.key_file.rename(backup_key)
                logger.info("Backed up existing certificates")
            except Exception as e:
                logger.error(f"Failed to backup certificates: {e}")
        
        # Generate new certificate
        success = await self._generate_self_signed_certificate()
        
        if not success:
            # Restore backup if generation failed
            if backup_cert.exists() and backup_key.exists():
                backup_cert.rename(self.cert_file)
                backup_key.rename(self.key_file)
                logger.error("Certificate renewal failed, restored backup")
            return False
        
        # Clean up backup files on success
        try:
            if backup_cert.exists():
                backup_cert.unlink()
            if backup_key.exists():
                backup_key.unlink()
        except Exception as e:
            logger.warning(f"Failed to clean up certificate backups: {e}")
        
        return True
    
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure connections."""
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(str(self.cert_file), str(self.key_file))
            
            # Security settings
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            
            logger.info("SSL context created successfully")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            return None
    
    async def get_certificate_info(self) -> Dict[str, Any]:
        """Get information about current certificates."""
        try:
            if not await self._certificates_exist():
                return {"status": "missing", "message": "Certificate files not found"}
            
            with open(self.cert_file, 'rb') as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data)
            
            # Extract certificate information
            subject_name = cert.subject.rfc4514_string()
            issuer_name = cert.issuer.rfc4514_string()
            serial_number = str(cert.serial_number)
            not_before = cert.not_valid_before
            not_after = cert.not_valid_after
            
            # Calculate days until expiration
            days_until_expiry = (not_after - datetime.utcnow()).days
            
            # Get subject alternative names
            san_list = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                san_list = [name.value for name in san_ext.value]
            except x509.ExtensionNotFound:
                pass
            
            return {
                "status": "valid" if days_until_expiry > 0 else "expired",
                "subject": subject_name,
                "issuer": issuer_name,
                "serial_number": serial_number,
                "not_before": not_before.isoformat(),
                "not_after": not_after.isoformat(),
                "days_until_expiry": days_until_expiry,
                "subject_alt_names": san_list,
                "is_self_signed": subject_name == issuer_name,
                "cert_file": str(self.cert_file),
                "key_file": str(self.key_file)
            }
            
        except Exception as e:
            logger.error(f"Failed to get certificate info: {e}")
            return {"status": "error", "message": str(e)}
    
    async def validate_certificate_chain(self) -> bool:
        """Validate certificate chain and key pair."""
        try:
            if not await self._certificates_exist():
                return False
            
            # Load certificate and private key
            with open(self.cert_file, 'rb') as f:
                cert_data = f.read()
            with open(self.key_file, 'rb') as f:
                key_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data)
            private_key = serialization.load_pem_private_key(key_data, password=None)
            
            # Validate key pair
            public_key = cert.public_key()
            private_public_key = private_key.public_key()
            
            if hasattr(public_key, 'public_numbers') and hasattr(private_public_key, 'public_numbers'):
                if (public_key.public_numbers().n != private_public_key.public_numbers().n):
                    logger.error("Certificate and private key do not match")
                    return False
            
            # Check certificate validity period
            now = datetime.utcnow()
            if cert.not_valid_before > now or cert.not_valid_after <= now:
                logger.error("Certificate is not within its validity period")
                return False
            
            logger.info("Certificate chain validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Certificate chain validation failed: {e}")
            return False


# Global TLS manager instance
tls_manager = TLSCertificateManager()


# Startup and shutdown handlers
async def init_tls():
    """Initialize TLS certificate system."""
    success = await tls_manager.initialize()
    if not success:
        raise RuntimeError("Failed to initialize TLS certificate system")
    return tls_manager


async def cleanup_tls():
    """Cleanup TLS certificate system."""
    # No cleanup needed for certificate manager
    pass


# Import fix for ipaddress
import ipaddress