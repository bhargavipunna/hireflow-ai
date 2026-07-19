"""Base JSON-file-backed repository.

Provides atomic read/write/CRUD over a list of dict records. Concrete
repositories (JobRepository, ApplicationRepository, ...) specialize this
with model-specific helpers.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Generic, Iterable, Optional, TypeVar

from app.config.exceptions import RepositoryError
from app.config.logger import get_logger
from app.config.settings import ensure_dirs

log = get_logger(__name__)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic JSON repository.

    Subclasses must set `path` and implement `to_dict`, `from_dict`,
    and the `key` used for identity.
    """

    path: Path = Path(".default.json")

    def __init__(self, path: Optional[os.PathLike] = None):
        ensure_dirs()
        if path is not None:
            self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    # --- serialization hooks ------------------------------------------------
    def to_dict(self, item: T) -> dict[str, Any]:
        raise NotImplementedError

    def from_dict(self, data: dict[str, Any]) -> T:
        raise NotImplementedError

    def key(self, item: T) -> str:
        raise NotImplementedError

    # --- low-level IO -------------------------------------------------------
    def _read(self) -> list[dict[str, Any]]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise RepositoryError(
                    f"Expected list in {self.path}, got {type(data).__name__}"
                )
            return data
        except (OSError, ValueError) as exc:
            raise RepositoryError(f"Failed to read {self.path}: {exc}") from exc

    def _write(self, records: list[dict[str, Any]]) -> None:
        """Atomic write via a temp file in the same directory."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                prefix=".tmp_",
                suffix=".json",
                dir=str(self.path.parent),
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except OSError as exc:
            raise RepositoryError(f"Failed to write {self.path}: {exc}") from exc

    # --- CRUD ---------------------------------------------------------------
    def all(self) -> list[T]:
        return [self.from_dict(r) for r in self._read()]

    def get(self, key: str) -> Optional[T]:
        for record in self._read():
            item = self.from_dict(record)
            if self.key(item) == key:
                return item
        return None

    def add(self, item: T) -> T:
        """Add an item; replaces an existing one with the same key."""
        records = self._read()
        k = self.key(item)
        records = [r for r in records if self._key_of_record(r) != k]
        records.append(self.to_dict(item))
        self._write(records)
        return item

    def add_many(self, items: Iterable[T]) -> int:
        """Bulk add/replace. Returns the number of unique items written."""
        records = self._read()
        index = {self._key_of_record(r): i for i, r in enumerate(records)}
        for item in items:
            k = self.key(item)
            if k in index:
                records[index[k]] = self.to_dict(item)
            else:
                index[k] = len(records)
                records.append(self.to_dict(item))
        self._write(records)
        return len(index)

    def update(self, key: str, mutate: Callable[[T], T]) -> Optional[T]:
        records = self._read()
        for i, record in enumerate(records):
            item = self.from_dict(record)
            if self.key(item) == key:
                updated = mutate(item)
                records[i] = self.to_dict(updated)
                self._write(records)
                return updated
        return None

    def filter(self, predicate: Callable[[T], bool]) -> list[T]:
        return [item for item in self.all() if predicate(item)]

    def clear(self) -> None:
        self._write([])

    # --- helpers ------------------------------------------------------------
    def _key_of_record(self, record: dict[str, Any]) -> str:
        return self.key(self.from_dict(record))
