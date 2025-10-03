# This file makes Python treat the directory as a package
from .base import *

# Import development settings by default
try:
    from .development import *
except ImportError:
    pass
