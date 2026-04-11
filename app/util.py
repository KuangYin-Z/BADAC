import base64
import hashlib
import json
import re


TOK_RE = re.compile(r"\(|\)|[^()\s]+")


def b64e(data):
    return base64.b64encode(data).decode("ascii")


def b64d(text):
    return base64.b64decode(text.encode("ascii"))


def canon_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canon_text(obj):
    return canon_bytes(obj).decode("utf-8")


def hash_json(obj):
    return hashlib.sha256(canon_bytes(obj)).hexdigest()


def norm_dom(dom):
    dom = str(dom or "").strip().upper()
    if not dom:
        raise ValueError("dom must not be empty")
    return dom


def norm_attrs(attrs):
    if not isinstance(attrs, list):
        raise ValueError("attrs must be a list")
    vals = []
    for item in attrs:
        text = str(item or "").strip().upper()
        if not text:
            continue
        vals.append(text)
    vals = sorted(set(vals))
    if not vals:
        raise ValueError("attrs must not be empty")
    return vals


def norm_pol(policy):
    tokens = TOK_RE.findall(str(policy or "").strip())
    if not tokens:
        raise ValueError("pol must not be empty")
    out = []
    for tok in tokens:
        if tok in {"(", ")"}:
            out.append(tok)
        elif tok.lower() in {"and", "or"}:
            out.append(tok.lower())
        else:
            out.append(tok.upper())
    text = " ".join(out)
    text = text.replace("( ", "(").replace(" )", ")")
    return text


def dump_obj(group, obj):
    if isinstance(obj, dict):
        return {str(k): dump_obj(group, v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [dump_obj(group, x) for x in obj]
    if isinstance(obj, tuple):
        return {"__t__": [dump_obj(group, x) for x in obj]}
    if isinstance(obj, bytes):
        return {"__b__": b64e(obj)}
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    try:
        return {"__g__": b64e(group.serialize(obj))}
    except Exception as exc:
        raise TypeError(f"unsupported object type: {type(obj)!r}") from exc


def load_obj(group, obj):
    if isinstance(obj, list):
        return [load_obj(group, x) for x in obj]
    if isinstance(obj, dict):
        if "__g__" in obj:
            return group.deserialize(b64d(obj["__g__"]))
        if "__b__" in obj:
            return b64d(obj["__b__"])
        if "__t__" in obj:
            return tuple(load_obj(group, x) for x in obj["__t__"])
        return {k: load_obj(group, v) for k, v in obj.items()}
    return obj


def pad_row(row, width):
    return list(row) + [0] * (width - len(row))


def solve_msp(msp, chosen, mod):
    if not chosen:
        raise ValueError("policy not satisfied; cannot solve MSP coefficients")
    width = max(len(row) for row in msp.values())
    mat = []
    for idx in range(width):
        eq = []
        for key in chosen:
            row = pad_row(msp[key], width)
            eq.append(row[idx] % mod)
        mat.append(eq)
    rhs = [1] + [0] * (width - 1)
    vals = solve_linear(mat, rhs, mod)
    out = {key: 0 for key in msp}
    for key, val in zip(chosen, vals):
        out[key] = val % mod
    return out


def solve_linear(mat, rhs, mod):
    rows = len(mat)
    cols = len(mat[0]) if rows else 0
    aug = [list(mat[i]) + [rhs[i] % mod] for i in range(rows)]
    pivots = []
    r = 0
    for c in range(cols):
        pivot = None
        for i in range(r, rows):
            if aug[i][c] % mod != 0:
                pivot = i
                break
        if pivot is None:
            continue
        aug[r], aug[pivot] = aug[pivot], aug[r]
        inv = pow(aug[r][c], -1, mod)
        for j in range(c, cols + 1):
            aug[r][j] = (aug[r][j] * inv) % mod
        for i in range(rows):
            if i == r or aug[i][c] % mod == 0:
                continue
            factor = aug[i][c] % mod
            for j in range(c, cols + 1):
                aug[i][j] = (aug[i][j] - factor * aug[r][j]) % mod
        pivots.append((r, c))
        r += 1
        if r == rows:
            break
    for i in range(rows):
        if all(aug[i][j] % mod == 0 for j in range(cols)) and aug[i][cols] % mod != 0:
            raise ValueError("MSP coefficients have no solution")
    out = [0] * cols
    for row, col in reversed(pivots):
        val = aug[row][cols]
        for j in range(col + 1, cols):
            val = (val - aug[row][j] * out[j]) % mod
        out[col] = val % mod
    return out
