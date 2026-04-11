import json
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

from .util import canon_text, dump_obj, load_obj


class Store:
    def __init__(self, group, root):
        self.group = group
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.csp_dir = self.root / "csp"
        self.csp_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.root / "state.json"
        self.lock = RLock()

    def empty(self):
        return {"sys": {}, "doms": {}}

    def _load(self):
        if not self.state_file.exists():
            return self.empty()
        raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        return load_obj(self.group, raw)

    def _save(self, state):
        raw = dump_obj(self.group, state)
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(canon_text(raw), encoding="utf-8")
        tmp.replace(self.state_file)

    def read(self):
        with self.lock:
            return self._load()

    @contextmanager
    def edit(self):
        with self.lock:
            state = self._load()
            yield state
            self._save(state)

    def reset(self, state):
        with self.lock:
            self._save(state)

    def obj_path(self, hct):
        return self.csp_dir / f"{hct}.json"

    def put_obj(self, hct, payload):
        with self.lock:
            self.obj_path(hct).write_text(canon_text(payload), encoding="utf-8")
