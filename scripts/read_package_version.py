from pathlib import Path

import tomlkit

path = Path(__file__).parent.parent / "pyproject.toml"
with open(path) as pyproject:
    file_contents = pyproject.read()

pkg_meta = tomlkit.parse(file_contents)["tool"]["poetry"]

# The short X.Y version
version = str(pkg_meta["version"])
print(version)
