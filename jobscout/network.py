"""Use a verified system CA bundle when python.org's CA symlink is missing."""
import os
import ssl
from pathlib import Path


def tls_context():
    if os.environ.get('SSL_CERT_FILE') or os.environ.get('SSL_CERT_DIR') or ssl.get_default_verify_paths().cafile:
        return ssl.create_default_context()
    for path in ['/opt/homebrew/etc/openssl@3/cert.pem','/etc/ssl/cert.pem']:
        if Path(path).is_file():
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()
