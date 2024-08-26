# -*- coding: utf-8 -*-
"""Namespace-only module."""

# This line must appear in the __init__.py for all namespace packages
__path__ = __import__('pkgutil').extend_path(__path__, __name__)