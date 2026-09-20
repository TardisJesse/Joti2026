"""Run locally; copy output to Railway secrets. Never commit the generated values."""
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

key = ec.generate_private_key(ec.SECP256R1())
encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip('=')
print('VAPID_PRIVATE_KEY=' + encode(key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())))
print('VAPID_PUBLIC_KEY=' + encode(key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)))
print('VAPID_SUBJECT=mailto:REPLACE_WITH_YOUR_EMAIL')
