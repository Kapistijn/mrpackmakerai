"""Small encrypted local store for browser-managed integration secrets.

Deployments should set ``MRPACK_SECRET_KEY`` from their secret manager.  For a
local desktop installation a Fernet key is generated in ``data/.secrets.key``;
the encrypted values themselves remain in ``data/secrets.enc`` and never enter
``config.json`` or an API response.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from tempfile import NamedTemporaryFile

from cryptography.fernet import Fernet, InvalidToken


class SecretStoreError(RuntimeError):
    pass


class SecretStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._key_path = data_dir / ".secrets.key"
        self._store_path = data_dir / "secrets.enc"

    def _key(self, *, create: bool) -> bytes | None:
        environment_key = os.getenv("MRPACK_SECRET_KEY")
        if environment_key:
            return environment_key.encode("ascii")
        if self._key_path.exists():
            return self._key_path.read_bytes().strip()
        if not create:
            return None
        self.data_dir.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        self._atomic_write(self._key_path, key + b"\n", binary=True)
        try:
            os.chmod(self._key_path, 0o600)
        except OSError:
            # Windows access control is managed by the user profile instead.
            pass
        return key

    @staticmethod
    def _atomic_write(path: Path, content: bytes, *, binary: bool = True) -> None:
        with NamedTemporaryFile(mode="wb" if binary else "w", delete=False, dir=path.parent) as temporary:
            temporary.write(content)  # type: ignore[arg-type]
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)

    def load(self) -> dict[str, str]:
        if not self._store_path.exists():
            return {}
        key = self._key(create=False)
        if key is None:
            raise SecretStoreError("Encrypted secrets exist but no secret key is available")
        try:
            decrypted = Fernet(key).decrypt(self._store_path.read_bytes())
            values = json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise SecretStoreError("Could not decrypt local integration secrets") from exc
        if not isinstance(values, dict) or not all(isinstance(value, str) for value in values.values()):
            raise SecretStoreError("Encrypted secret store has an invalid shape")
        return values

    def save(self, values: dict[str, str]) -> None:
        key = self._key(create=True)
        assert key is not None
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(values, sort_keys=True).encode("utf-8")
        self._atomic_write(self._store_path, Fernet(key).encrypt(payload), binary=True)
        try:
            os.chmod(self._store_path, 0o600)
        except OSError:
            pass

    def update(self, values: dict[str, str | None]) -> dict[str, str]:
        current = self.load()
        for name, value in values.items():
            if value is not None:
                current[name] = value
        self.save(current)
        return current

    def remove(self, names: Iterable[str]) -> dict[str, str]:
        """Delete one or more secrets. Missing names are ignored.

        Used by the browser-facing settings so a user can permanently clear a
        stored API key at any time without editing files on disk.
        """
        if not self._store_path.exists():
            return {}
        current = self.load()
        changed = False
        for name in names:
            if name in current:
                del current[name]
                changed = True
        if changed:
            self.save(current)
        return current
