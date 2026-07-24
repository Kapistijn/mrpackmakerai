"""Single source of truth for safe MRPack in-instance paths."""
from __future__ import annotations
from pathlib import PurePosixPath

def validate_install_path(value: str) -> str:
    if not isinstance(value,str) or not value or '\\' in value:
        raise ValueError('Install path must be a non-empty POSIX relative path')
    path=PurePosixPath(value)
    if path.is_absolute() or not path.parts or '..' in path.parts or '.' in path.parts:
        raise ValueError(f'Unsafe MRPack path: {value}')
    return str(path)

def is_safe_install_path(value: str|None) -> bool:
    try: validate_install_path(value or '')
    except ValueError: return False
    return True
