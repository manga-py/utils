from pathlib import Path
from sys import platform

__all__ = ['sanitize_filename', ]

__is_win = platform == 'win32'

if __is_win:
    __illegal = ':<>|"?*\\/'
else:
    __illegal = '/'

_sanitize_table = str.maketrans(__illegal, '_' * len(__illegal))


def sanitize_filename(name: str):
    """Replace bad characters and remove trailing dots from parts."""
    return name.translate(_sanitize_table)


def sanitize_full_path(path: Path) -> Path:
    parts = path.parts

    if not __is_win or len(parts) == 0:
        return path.resolve()

    start, *other_parts = parts

    if len(other_parts) == 0:
        return path

    return Path(start).joinpath(*map(sanitize_filename, other_parts)).resolve()

