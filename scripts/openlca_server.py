"""Disposable openLCA gdt-server lifecycle for integration tests."""

from __future__ import annotations

import hashlib
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import uuid
import zipfile
from contextlib import AbstractContextManager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLATFORM = os.environ.get("OPENLCA_TEST_PLATFORM", "linux/amd64")
IMAGE = os.environ.get(
    "OPENLCA_TEST_IMAGE", "lca-mock-tests-gdt-server:2.7-dev-amd64-native"
)


def _docker(*args: str, check: bool = True, capture: bool = False):
    return subprocess.run(
        ["docker", *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def ensure_image() -> None:
    found = _docker("image", "inspect", IMAGE, check=False, capture=True)
    if found.returncode == 0:
        return
    dockerfile = ROOT / "docker" / "gdt-server.Dockerfile"
    print(f"Building {IMAGE} from GreenDelta's official image layers ...")
    _docker(
        "build",
        "--platform", PLATFORM,
        "-f", str(dockerfile),
        "-t", IMAGE,
        str(ROOT),
    )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_bafu_template(
    archive: Path,
    cache_root: Path,
    expected_sha256: str | None = None,
) -> Path:
    """Extract the nested BAFU .zolca into a reusable pristine template."""
    archive = archive.resolve()
    if not archive.is_file():
        raise FileNotFoundError(f"BAFU openLCA archive not found: {archive}")

    digest = _sha256(archive)
    if expected_sha256 is not None and digest != expected_sha256:
        raise RuntimeError(
            f"Unexpected checksum for {archive.name}: expected "
            f"{expected_sha256}, got {digest}"
        )
    template = cache_root / f"bafu-{digest[:12]}"
    database = template / "databases" / "bafu"
    stamp = template / ".source-sha256"
    if database.is_dir() and stamp.is_file() and stamp.read_text().strip() == digest:
        return template

    shutil.rmtree(template, ignore_errors=True)
    template.mkdir(parents=True)
    nested_path = template / "bafu.zolca"
    with zipfile.ZipFile(archive) as outer:
        entries = [name for name in outer.namelist() if name.lower().endswith(".zolca")]
        if len(entries) != 1:
            raise RuntimeError(f"Expected one .zolca in {archive}, found {len(entries)}")
        with outer.open(entries[0]) as source, nested_path.open("wb") as target:
            shutil.copyfileobj(source, target)

    database.mkdir(parents=True)
    with zipfile.ZipFile(nested_path) as zolca:
        zolca.extractall(database)
    nested_path.unlink()
    stamp.write_text(digest + "\n")
    return template


class OpenLcaServer(AbstractContextManager):
    """Run gdt-server with a copied or empty disposable openLCA workspace."""

    def __init__(self, database: str, template: Path | None = None):
        self.database = database
        self.template = template
        self.port = _free_port()
        self.endpoint = f"http://127.0.0.1:{self.port}/"
        self.name = f"lca-mock-{uuid.uuid4().hex[:12]}"
        self._temp: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self):
        ensure_image()
        self._temp = tempfile.TemporaryDirectory(prefix="lca-mock-openlca-")
        workspace = Path(self._temp.name) / "data"
        if self.template is None:
            (workspace / "databases").mkdir(parents=True)
        else:
            shutil.copytree(self.template, workspace)

        command = [
            "run", "-d",
            "--platform", PLATFORM,
            "--name", self.name,
            "-p", f"127.0.0.1:{self.port}:8080",
            "-v", f"{workspace}:/app/data",
            "-m", os.environ.get("OPENLCA_TEST_MEMORY", "6g"),
            IMAGE,
            "-db", self.database,
            "-threads", "1",
        ]
        started = _docker(*command, capture=True)
        if started.returncode != 0:
            raise RuntimeError(started.stdout)

        deadline = time.monotonic() + 90
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(self.endpoint + "api/version", timeout=2) as response:
                    if response.status == 200:
                        print(f"openLCA IPC ready at {self.endpoint} (database: {self.database})")
                        return self
            except Exception as error:
                last_error = error
                running = _docker(
                    "inspect", "-f", "{{.State.Running}}", self.name,
                    check=False, capture=True,
                )
                if running.returncode == 0 and running.stdout.strip() == "false":
                    break
                time.sleep(0.5)
        logs = _docker("logs", self.name, check=False, capture=True).stdout
        self.__exit__(None, None, None)
        raise RuntimeError(f"gdt-server did not become ready: {last_error}\n{logs}")

    def __exit__(self, exc_type, exc, traceback):
        _docker("stop", "--time", "10", self.name, check=False, capture=True)
        _docker("rm", "-f", self.name, check=False, capture=True)
        if self._temp is not None:
            self._temp.cleanup()
        return False
