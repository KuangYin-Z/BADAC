import hashlib
import json
import os

from charm.schemes.abenc.ac17 import AC17CPABE
from charm.toolbox.pairinggroup import GT
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .util import b64d, b64e, canon_bytes, dump_obj, load_obj, norm_pol


class FameBox:
    def __init__(self, group):
        self.group = group
        self.cpabe = AC17CPABE(group, 2)

    def setup(self):
        return self.cpabe.setup()

    def keygen(self, pk, msk, attrs):
        return self.cpabe.keygen(pk, msk, attrs)

    def encrypt(self, pk, infor, policy):
        policy = norm_pol(policy)
        msg = self.group.random(GT)
        abe = self.cpabe.encrypt(pk, msg, policy)
        key = hashlib.sha256(self.group.serialize(msg)).digest()
        iv = os.urandom(12)
        ct = AESGCM(key).encrypt(iv, canon_bytes(infor), None)
        return {
            "abe": {
                "pol": policy,
                "c0": dump_obj(self.group, abe["C_0"]),
                "c": dump_obj(self.group, abe["C"]),
                "cp": dump_obj(self.group, abe["Cp"]),
            },
            "iv": b64e(iv),
            "ct": b64e(ct),
        }

    def decrypt(self, pk, payload, sk):
        abe = payload["abe"]
        ctxt = {
            "policy": self.cpabe.util.createPolicy(abe["pol"]),
            "C_0": load_obj(self.group, abe["c0"]),
            "C": load_obj(self.group, abe["c"]),
            "Cp": load_obj(self.group, abe["cp"]),
        }
        msg = self.cpabe.decrypt(pk, ctxt, sk)
        if msg is None:
            return None
        key = hashlib.sha256(self.group.serialize(msg)).digest()
        plain = AESGCM(key).decrypt(b64d(payload["iv"]), b64d(payload["ct"]), None)
        return json.loads(plain.decode("utf-8"))

