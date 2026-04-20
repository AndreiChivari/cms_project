# import datetime
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509.oid import NameOID
from cryptography import x509
from cryptography.fernet import Fernet
from django.conf import settings

def genereaza_identitate_digitala(user):
    """
    Generează o cheie privată RSA și un certificat X.509 (Self-Signed) pentru utilizator.
    Cheia privată este criptată cu Fernet înainte de salvarea în baza de date.
    """
    
    # 1. Generăm CHEIA PRIVATĂ RSA (2048 biți) pentru semnătura digitală
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 2. Construim NUMELE pentru CERTIFICAT
    unitate_user = getattr(user, 'unitate', 'Sistemul de Management al Dosarelor')
    nume_complet = user.get_full_name() or user.username

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"RO"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, str(unitate_user)),
        x509.NameAttribute(NameOID.COMMON_NAME, str(nume_complet)),
    ])

    # 3. Generăm CERTIFICATUL PUBLIC (setăm valabilitatea la 1 an)
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(timezone.utc)
    ).not_valid_after(
        datetime.now(timezone.utc) + timedelta(days=365)
    ).sign(private_key, hashes.SHA256())

    # 4. transformăm în TEXT/BYTES pentru stocare în baza de date
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
    
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # 5. CRIPTĂM cheia privată cu cheia secretă Fernet din settings (ENCRYPTION_KEY) pentru securitate
    f = Fernet(settings.ENCRYPTION_KEY) 
    encrypted_private_key = f.encrypt(private_key_pem)

    # 6. SALVĂM datele în modelul userului
    user.certificat_pem = cert_pem
    user.cheie_privata_criptata = encrypted_private_key
    user.save()
    
    return True