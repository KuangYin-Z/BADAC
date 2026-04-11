import json
import subprocess


class FabricCli:
    def __init__(self, bridge, cwd):
        self.bridge = bridge
        self.cwd = cwd

    def call(self, fn, args=None, submit=False):
        req = {"fn": fn, "args": args or [], "submit": bool(submit)}
        proc = subprocess.run(
            ["node", self.bridge],
            cwd=self.cwd,
            input=json.dumps(req).encode("utf-8"),
            capture_output=True,
            check=False,
        )
        out = proc.stdout.decode("utf-8", errors="ignore").strip()
        if not out:
            err = proc.stderr.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(err or f"Fabric call failed: {fn}")
        data = json.loads(out)
        if proc.returncode != 0 or not data.get("ok"):
            raise RuntimeError(data.get("err") or f"Fabric call failed: {fn}")
        return data.get("data")
