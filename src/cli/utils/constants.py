"""CLI constants and styling definitions."""

from rich import box

# Box styles for tables
BOX_STYLE_TITLE = box.ROUNDED
BOX_STYLE_DEFAULT = box.ROUNDED
BOX_STYLE_SIMPLE = box.SIMPLE

# Color styles
STYLE_HEADER = "cyan bold"
STYLE_SUCCESS = "green"
STYLE_ERROR = "red"
STYLE_WARNING = "yellow"
STYLE_INFO = "blue"
STYLE_SUBTLE = "dim"

# Table columns default style
COLUMN_STYLE_KEY = "cyan"
COLUMN_STYLE_VALUE = "green"
COLUMN_STYLE_STATUS = "magenta"
COLUMN_STYLE_DESCRIPTION = "blue"

# Error message prefixes
PREFIX_ERROR = "✗"
PREFIX_SUCCESS = "✓"
PREFIX_WARNING = "⚠"
PREFIX_INFO = "ℹ"

# Common strings
MSG_NOT_FOUND = "not found"
MSG_CREATED = "created successfully"
MSG_UPDATED = "updated successfully"
MSG_DELETED = "deleted successfully"
MSG_ERROR = "Error"
MSG_USAGE = "Usage"
MSG_EXAMPLE = "Example"

# Date format
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
