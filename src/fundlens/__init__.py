from importlib.metadata import version

# Read from the installed distribution, so `pyproject.toml` is the only place the version is
# written and `fundlens --version` cannot drift from it.
__version__ = version("fundlens")
