"""Back-compat wrappers around dbc_decode."""

from dbc_decode import default_dbc_path, load_dbc_names, short_name  # noqa: F401

__all__ = ["default_dbc_path", "load_dbc_names", "short_name"]
