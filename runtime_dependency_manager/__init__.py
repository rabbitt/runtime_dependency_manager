# runtime_dependency_manager
# Copyright (C) 2024 Carl Corliss
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
