import json
import os
import secrets
import urllib.error
import urllib.request

from charm.toolbox.pairinggroup import PairingGroup
from flask import Flask, jsonify, request, send_file

from .crypto_abs import Abs3
from .crypto_fame import FameBox
from .fabric import FabricCli
from .state import Store
from .util import dump_obj, hash_json, load_obj, norm_attrs, norm_dom, norm_pol


APP_PORT = int(os.getenv("APP_PORT", "8000"))
APP_URL = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")
DATA_DIR = os.getenv("DATA_DIR", "/work/data")
APP_ROOT = os.getenv("APP_ROOT", "/work")
GW_PATH = os.getenv("GW_PATH", "/work/bridge/gw.js")
ABS_TMAX = int(os.getenv("ABS_TMAX", "16"))

group = PairingGroup("BN254")
fame = FameBox(group)
abs3 = Abs3(group, ABS_TMAX)
store = Store(group, DATA_DIR)
fabric = FabricCli(GW_PATH, APP_ROOT)
app = Flask(__name__)


def fail(msg, code=400):
    return jsonify({"err": msg}), code


def need_sys(state):
    if "fame" not in state["sys"] or "abs" not in state["sys"]:
        raise ValueError("system has not been initialized")


def need_dom(state, dom):
    info = state["doms"].get(dom)
    if not info:
        raise ValueError(f"domain {dom} is not registered")
    return info


@app.post("/init")
def init_route():
    pk_fame, msk_fame = fame.setup()
    mpk_abs, msk_abs = abs3.setup()
    state = {
        "sys": {
            "fame": {"pk": pk_fame, "msk": msk_fame},
            "abs": {"mpk": mpk_abs, "msk": msk_abs},
        },
        "doms": {},
    }
    store.reset(state)
    pp = {
        "mpk_abe": dump_obj(group, pk_fame),
        "mpk_abs": dump_obj(group, mpk_abs),
    }
    fabric.call("putPp", [json.dumps(pp, sort_keys=True, separators=(",", ":"))], submit=True)
    return jsonify({"res": "ok"})


@app.post("/reg")
def reg_route():
    data = request.get_json(silent=True) or {}
    try:
        dom = norm_dom(data.get("dom"))
        attrs = norm_attrs(data.get("attrs"))
        with store.edit() as state:
            need_sys(state)
            sk_fame = fame.keygen(state["sys"]["fame"]["pk"], state["sys"]["fame"]["msk"], attrs)
            sk_abs = abs3.keygen(state["sys"]["abs"]["mpk"], state["sys"]["abs"]["msk"]["ask"], attrs)
            state["doms"][dom] = {
                "attrs": attrs,
                "sk_fame": sk_fame,
                "sk_abs": sk_abs,
                "pull": {},
                "pub": {},
                "sids": [],
                "seen": [],
            }
        return jsonify({"dom": dom, "attrs": attrs})
    except Exception as exc:
        return fail(str(exc))


@app.post("/pub")
def pub_route():
    data = request.get_json(silent=True) or {}
    try:
        dom = norm_dom(data.get("dom"))
        pol = norm_pol(data.get("pol"))
        if abs3.width(pol) > ABS_TMAX:
            raise ValueError("policy is too complex for the ABS limit")
        with store.edit() as state:
            need_sys(state)
            need_dom(state, dom)
            infor = {"k": secrets.token_hex(16), "pol": pol}
            ct = fame.encrypt(state["sys"]["fame"]["pk"], infor, pol)
            hct = hash_json(ct)
            store.put_obj(hct, ct)
            url = f"{APP_URL}/obj/{hct}"
            state["doms"][dom]["pub"] = {"infor": infor, "pol": pol, "hct": hct, "url": url}
        fabric.call("putCh", [dom, url, hct], submit=True)
        return jsonify({"url": url, "hct": hct})
    except Exception as exc:
        return fail(str(exc))


@app.post("/pull")
def pull_route():
    data = request.get_json(silent=True) or {}
    try:
        dom = norm_dom(data.get("dom"))
        auth = norm_dom(data.get("auth"))
        with store.edit() as state:
            need_sys(state)
            info = need_dom(state, dom)
            ch = fabric.call("getCh", [auth], submit=False)
            if not ch:
                raise ValueError("challenge metadata is not available on chain")
            try:
                raw = urllib.request.urlopen(ch["url"], timeout=10).read().decode("utf-8")
            except urllib.error.URLError as exc:
                raise ValueError(f"failed to fetch URL: {exc}") from exc
            ct = json.loads(raw)
            if hash_json(ct) != ch["hct"]:
                raise ValueError("ciphertext hash mismatch")
            infor = fame.decrypt(state["sys"]["fame"]["pk"], ct, info["sk_fame"])
            if infor is None:
                raise ValueError("FAME decryption failed")
            info["pull"][auth] = {"infor": infor}
        return jsonify({"pol": infor["pol"], "k": infor["k"]})
    except Exception as exc:
        return fail(str(exc))


@app.post("/sign")
def sign_route():
    data = request.get_json(silent=True) or {}
    try:
        dom = norm_dom(data.get("dom"))
        auth = norm_dom(data.get("auth"))
        with store.edit() as state:
            need_sys(state)
            info = need_dom(state, dom)
            pulled = info["pull"].get(auth)
            if not pulled:
                raise ValueError("challenge has not been pulled yet")
            infor = pulled["infor"]
            msg = hash_json(infor)
            sig = abs3.sign(state["sys"]["abs"]["mpk"], info["sk_abs"], msg, infor["pol"])
            sig_wire = dump_obj(group, sig)
            sid = hash_json(sig_wire)
            info["sids"] = sorted(set(info["sids"] + [sid]))
        fabric.call("putRq", [auth, json.dumps(sig_wire, sort_keys=True, separators=(",", ":")), sid], submit=True)
        return jsonify({"sid": sid})
    except Exception as exc:
        return fail(str(exc))


@app.post("/verify")
def verify_route():
    data = request.get_json(silent=True) or {}
    try:
        dom = norm_dom(data.get("dom"))
        with store.edit() as state:
            need_sys(state)
            info = need_dom(state, dom)
            pub = info.get("pub") or {}
            if not pub:
                raise ValueError("this domain has not published a challenge")
            msg = hash_json(pub["infor"])
            pol = pub["pol"]
            reqs = fabric.call("getRq", [dom], submit=False) or []
            done = set(info["seen"])
            out = []
            for item in reqs:
                sid = item["sid"]
                if sid in done:
                    continue
                sig = load_obj(group, json.loads(item["sig"]))
                ok = abs3.verify(state["sys"]["abs"]["mpk"], sig, msg, pol)
                res = "Auth_Success" if ok else "Auth_Fail"
                fabric.call("putRs", [sid, res], submit=True)
                done.add(sid)
                out.append({"sid": sid, "res": res})
            info["seen"] = sorted(done)
        return jsonify(out)
    except Exception as exc:
        return fail(str(exc))


@app.post("/result")
def result_route():
    data = request.get_json(silent=True) or {}
    try:
        dom = norm_dom(data.get("dom"))
        sid = str(data.get("sid") or "").strip()
        if not sid:
            raise ValueError("sid must not be empty")
        state = store.read()
        need_sys(state)
        need_dom(state, dom)
        item = fabric.call("getRs", [sid], submit=False) or {}
        return jsonify({"res": item.get("res", "")})
    except Exception as exc:
        return fail(str(exc))


@app.get("/obj/<hct>")
def obj_route(hct):
    path = store.obj_path(hct)
    if not path.exists():
        return fail("object not found", 404)
    return send_file(path, mimetype="application/json")


def main():
    app.run(host="0.0.0.0", port=APP_PORT)


if __name__ == "__main__":
    main()
