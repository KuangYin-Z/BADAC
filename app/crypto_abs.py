from charm.toolbox.msp import MSP
from charm.toolbox.pairinggroup import G1, G2, GT, ZR, pair

from .util import canon_text, norm_pol, pad_row, solve_msp


class Abs3:
    def __init__(self, group, tmax):
        self.group = group
        self.tmax = tmax
        self.util = MSP(group, False)
        self.mod = int(group.order())

    def setup(self):
        tpk = self.tsetup()
        apk, ask = self.asetup(tpk)
        return {"tpk": tpk, "apk": apk}, {"ask": ask}

    def tsetup(self):
        g = self.group.random(G1)
        h = [self.group.random(G2) for _ in range(self.tmax + 1)]
        return {"g": g, "h": h, "tmax": self.tmax}

    def asetup(self, tpk):
        a0 = self.rand_nonzero()
        a = self.rand_nonzero()
        b = self.rand_nonzero()
        c = self.rand_nonzero()
        apk = {
            "A0": tpk["h"][0] ** a0,
            "A": [tpk["h"][idx] ** a for idx in range(1, self.tmax + 1)],
            "B": [tpk["h"][idx] ** b for idx in range(1, self.tmax + 1)],
            "C": tpk["g"] ** c,
        }
        ask = {"a0": a0, "a": a, "b": b}
        return apk, ask

    def keygen(self, mpk, ask, attrs):
        kb = self.group.random(G1)
        out = {"attrs": list(attrs), "kb": kb, "k0": kb ** (ask["a0"] ** -1), "ku": {}}
        for attr in attrs:
            u = self.hash_attr(attr)
            den = ask["a"] + ask["b"] * u
            if int(den) == 0:
                raise ValueError(f"attribute {attr} makes the denominator zero")
            out["ku"][attr] = kb ** (den ** -1)
        return out

    def width(self, policy):
        policy = norm_pol(policy)
        self.util.convert_policy_to_msp(self.util.createPolicy(policy))
        return self.util.len_longest_row

    def sign(self, mpk, sk, msg, policy):
        policy = norm_pol(policy)
        tree = self.util.createPolicy(policy)
        msp = self.util.convert_policy_to_msp(tree)
        width = self.util.len_longest_row
        if width > self.tmax:
            raise ValueError("policy width exceeds the ABS limit")
        nodes = self.util.prune(tree, sk["attrs"])
        if not nodes:
            raise ValueError("attributes do not satisfy the policy")
        chosen = [node.getAttributeAndIndex() for node in nodes]
        coeffs = solve_msp(msp, chosen, self.mod)
        mu = self.hash_msg(msg, policy)
        r0 = self.rand_nonzero()
        cg_mu = mpk["apk"]["C"] * (mpk["tpk"]["g"] ** mu)
        y = sk["kb"] ** r0
        w = sk["k0"] ** r0
        rows = list(msp.keys())
        sig_s = []
        sig_p = [mpk["tpk"]["h"][0] ** 0 for _ in range(width)]
        for row_name in rows:
            row = pad_row(msp[row_name], width)
            attr = self.util.strip_index(row_name)
            ri = self.group.random(ZR)
            vi = coeffs.get(row_name, 0)
            left = mpk["tpk"]["g"] ** 0
            if vi != 0:
                left = sk["ku"][attr] ** (self.group.init(ZR, vi) * r0)
            sig_s.append(left * (cg_mu ** ri))
            u = self.hash_attr(attr)
            for idx, mij in enumerate(row):
                if mij == 0:
                    continue
                base = mpk["apk"]["A"][idx] * (mpk["apk"]["B"][idx] ** u)
                sig_p[idx] *= base ** (ri * mij)
        return {"y": y, "w": w, "s": sig_s, "p": sig_p}

    def verify(self, mpk, sig, msg, policy):
        policy = norm_pol(policy)
        tree = self.util.createPolicy(policy)
        msp = self.util.convert_policy_to_msp(tree)
        width = self.util.len_longest_row
        if width > self.tmax:
            return False
        if len(sig["s"]) != len(msp) or len(sig["p"]) != width:
            return False
        if sig["y"] == (mpk["tpk"]["g"] ** 0):
            return False
        mu = self.hash_msg(msg, policy)
        cg_mu = mpk["apk"]["C"] * (mpk["tpk"]["g"] ** mu)
        if pair(sig["w"], mpk["apk"]["A0"]) != pair(sig["y"], mpk["tpk"]["h"][0]):
            return False
        rows = list(msp.keys())
        gt_one = pair(mpk["tpk"]["g"], mpk["tpk"]["h"][0]) ** 0
        for idx in range(width):
            lhs = gt_one
            for pos, row_name in enumerate(rows):
                row = pad_row(msp[row_name], width)
                mij = row[idx]
                if mij == 0:
                    continue
                attr = self.util.strip_index(row_name)
                u = self.hash_attr(attr)
                base = mpk["apk"]["A"][idx] * (mpk["apk"]["B"][idx] ** u)
                lhs *= pair(sig["s"][pos], base ** mij)
            rhs = pair(cg_mu, sig["p"][idx])
            if idx == 0:
                rhs *= pair(sig["y"], mpk["tpk"]["h"][1])
            if lhs != rhs:
                return False
        return True

    def hash_attr(self, text):
        seed = f"a:{text}"
        while True:
            val = self.group.hash(seed, ZR)
            if int(val) != 0:
                return val
            seed += "#"

    def hash_msg(self, msg, policy):
        seed = canon_text({"m": msg, "pol": policy})
        while True:
            val = self.group.hash(seed, ZR)
            if int(val) != 0:
                return val
            seed += "#"

    def rand_nonzero(self):
        while True:
            val = self.group.random(ZR)
            if int(val) != 0:
                return val
