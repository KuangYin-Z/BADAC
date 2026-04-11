#!/usr/bin/env python3
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE = "http://localhost:8000"
STATE = ROOT / "data" / "state.json"


def req(path, payload=None, expect=200):
    data = None if payload is None else json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    req_obj = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req_obj, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            if resp.status != expect:
                raise RuntimeError(f"{path} returned unexpected status: {resp.status}")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        if exc.code != expect:
            raise RuntimeError(f"{path} request failed: {exc.code} {body}") from exc
        return json.loads(body)


def wait_app():
    for _ in range(120):
        try:
            urllib.request.urlopen(f"{BASE}/obj/nope", timeout=2)
        except urllib.error.HTTPError:
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("application did not start within the expected time")


def bridge(fn, args=None, submit=False, ok=True):
    payload = json.dumps({"fn": fn, "args": args or [], "submit": submit}, separators=(",", ":"))
    proc = subprocess.run(
        ["docker", "exec", "-i", "badac-app", "node", "/work/bridge/gw.js"],
        input=payload.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    out = proc.stdout.decode("utf-8", errors="ignore").strip()
    if not out:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))
    data = json.loads(out)
    if ok and (proc.returncode != 0 or not data.get("ok")):
        raise RuntimeError(data.get("err") or "bridge call failed")
    if not ok and proc.returncode == 0 and data.get("ok"):
        raise RuntimeError("call was expected to fail but returned success")
    return data


def edit_state(fn):
    raw = json.loads(STATE.read_text(encoding="utf-8"))
    fn(raw)
    STATE.unlink()
    STATE.write_text(json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def break_csp(hct):
    path = ROOT / "data" / "csp" / f"{hct}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["ct"] = raw["ct"][:-2] + "AA"
    path.unlink()
    path.write_text(json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def main():
    wait_app()

    req("/init", {})
    req("/reg", {"dom": "A", "attrs": ["AUTH"]})
    req("/reg", {"dom": "B", "attrs": ["ALPHA", "BETA"]})
    req("/reg", {"dom": "C", "attrs": ["ALPHA"]})

    pol = "(ALPHA and BETA)"

    pub1 = req("/pub", {"dom": "A", "pol": pol})
    pp = bridge("getPp")["data"]
    if "mpk_abe" not in pp or "mpk_abs" not in pp:
        raise RuntimeError("putPp/getPp validation failed")
    ch = bridge("getCh", ["A"])["data"]
    if ch["hct"] != pub1["hct"]:
        raise RuntimeError("putCh/getCh validation failed")

    pull1 = req("/pull", {"dom": "B", "auth": "A"})
    if pull1["pol"] != pol:
        raise RuntimeError("pull returned an unexpected policy value")
    sid1 = req("/sign", {"dom": "B", "auth": "A"})["sid"]
    rq1 = bridge("getRq", ["A"])["data"]
    if not any(item["sid"] == sid1 for item in rq1):
        raise RuntimeError("putRq/getRq validation failed")
    ver1 = req("/verify", {"dom": "A"})
    if not any(item["sid"] == sid1 and item["res"] == "Auth_Success" for item in ver1):
        raise RuntimeError("happy-path authentication validation failed")
    rs1 = bridge("getRs", [sid1])["data"]
    if rs1["res"] != "Auth_Success":
        raise RuntimeError("putRs/getRs validation failed")
    out1 = req("/result", {"dom": "B", "sid": sid1})
    if out1["res"] != "Auth_Success":
        raise RuntimeError("result did not return Auth_Success")

    bad_pull = req("/pull", {"dom": "C", "auth": "A"}, expect=400)
    if "err" not in bad_pull:
        raise RuntimeError("attribute-mismatch scenario did not fail as expected")

    pub2 = req("/pub", {"dom": "A", "pol": pol})
    break_csp(pub2["hct"])
    tamper = req("/pull", {"dom": "B", "auth": "A"}, expect=400)
    if "hash mismatch" not in tamper["err"]:
        raise RuntimeError("tampered-ciphertext scenario did not hit the expected error")

    req("/pub", {"dom": "A", "pol": pol})
    req("/pull", {"dom": "B", "auth": "A"})

    def flip_msg(raw):
        raw["doms"]["B"]["pull"]["A"]["infor"]["k"] = "deadbeefdeadbeefdeadbeefdeadbeef"

    edit_state(flip_msg)
    sid2 = req("/sign", {"dom": "B", "auth": "A"})["sid"]
    ver2 = req("/verify", {"dom": "A"})
    if not any(item["sid"] == sid2 and item["res"] == "Auth_Fail" for item in ver2):
        raise RuntimeError("signature-failure scenario did not hit the expected result")
    out2 = req("/result", {"dom": "B", "sid": sid2})
    if out2["res"] != "Auth_Fail":
        raise RuntimeError("Auth_Fail was not recorded on chain as expected")

    req("/pub", {"dom": "A", "pol": pol})
    req("/pull", {"dom": "B", "auth": "A"})
    sid3 = req("/sign", {"dom": "B", "auth": "A"})["sid"]
    rq3 = bridge("getRq", ["A"])["data"]
    item3 = next(item for item in rq3 if item["sid"] == sid3)
    bridge("putRq", ["A", item3["sig"], sid3], submit=True, ok=False)
    ver3 = req("/verify", {"dom": "A"})
    if len([item for item in ver3 if item["sid"] == sid3]) != 1:
        raise RuntimeError("replay scenario result did not match expectations")

    print("demo ok")


if __name__ == "__main__":
    main()
