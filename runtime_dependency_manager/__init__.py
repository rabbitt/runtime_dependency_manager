"""
runtime_dependency_manager

A simple Python module for managing dependencies at runtime. 
It is designed for small scripts that do not use a requirements.txt file.
"""

__author__ = "Carl Corliss"
__email__ = "rabbitt@gmail.com"

from .manager import (
    RuntimeDependencyManagerException,
    DependentPackageNotFoundError,
    VersionCompatibilityError,
    Package,
    ImportFrom,
    RuntimeDependencyManager
)

__all__ = [
    'RuntimeDependencyManagerException',
    'DependentPackageNotFoundError',
    'VersionCompatibilityError',
    'Package',
    'ImportFrom',
    'RuntimeDependencyManager'
]
