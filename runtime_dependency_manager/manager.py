#!/usr/bin/env python

"""
This module provides a RuntimeDependencyManager class for managing Python package dependencies at runtime.
It is designed for simple scripts that do not use a requirements.txt file.

Example usage:

    with RuntimeDependencyManager(install_if_missing=True) as mgr:
        mgr.index_url = 'https://pypi.org/simple'
        mgr.trusted_hosts = ['https://example.com']
        
        with mgr.package('IPy', '>=1.1') as pkg:
            pkg.from_module('IPy').import_modules('IP', 'IPSet')

        with mgr.package('pymongo', '>=3.11.4, <4.0.0') as pkg:
            pkg.import_module('pymongo')
            pkg.from_module('bson').import_module('ObjectId')

        with mgr.package('paramiko', '==2.7.2') as pkg:
            pkg.import_modules('SSHClient', 'AutoAddPolicy', 'SSHConfig', 'SSHException')

        with mgr.package('pyyaml', '>=5.4.1, <6.0.0', optional=True) as pkg:
            pkg.import_module('yaml')
"""

import importlib
import logging
import subprocess
import sys

from importlib.metadata import version, PackageNotFoundError
from packaging.requirements import Requirement
from packaging.version import Version, InvalidVersion
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class RuntimeDependencyManagerException(Exception):
    """Base exception for RuntimeDependencyManager."""
    pass

class DependentPackageNotFoundError(RuntimeDependencyManagerException):
    """Exception raised when a package is not found."""
    def __init__(self, package_name: str):
        super().__init__(f"Package {package_name} not found after installation")

class VersionCompatibilityError(RuntimeDependencyManagerException):
    """Exception raised when a package version does not satisfy the specified constraints."""
    def __init__(self, package_name: str, installed_version: str, version_spec: Optional[str]):
        super().__init__(f"Installed version {installed_version} of {package_name} does not satisfy {version_spec}")

class PackageInstallationError(Exception):
    """Exception raised for errors in the package installation process."""
    def __init__(self, message):
        super().__init__(message)

class Package:
    """
    Represents a package with its name, version specification, and import statements.

    Attributes:
        name (str): The name of the package.
        version_spec (Optional[str]): The version specification of the package.
        optional (bool): Indicates if the package is optional.
        imports (list[dict]): List of import statements for the package.
    """
    def __init__(self, name: str, version_spec: Optional[str] = None, optional: bool = False):
        self.name = name
        self.version_spec = str(Requirement(f'pkgname{version_spec}').specifier) # normalize
        self.optional = optional
        self.imports: list[dict] = []

    def import_module(self, module_name: str) -> "Package":
        """
        Adds an import statement for the specified module.

        Args:
            module_name (str): The name of the module to import.

        Returns:
            Package: The current package instance for chaining.
        """
        self.imports.append({'type': 'import', 'module': module_name})
        return self

    def import_modules(self, *modules: str) -> "Package":
        """
        Adds import statements for multiple modules.

        Args:
            *modules (tuple[str, ...]): The names of the modules to import.

        Returns:
            Package: The current package instance for chaining.
        """
        for module_name in modules:
            self.import_module(module_name)
        return self

    def from_module(self, from_name: str) -> "ImportFrom":
        """
        Creates an ImportFrom object for importing specific items from a module.

        Args:
            from_name (str): The module name to import from.

        Returns:
            ImportFrom: An ImportFrom instance for specifying imports.
        """
        return ImportFrom(from_name, self)

    def as_module(self, alias: str) -> "Package":
        """
        Specifies an alias for the imported module.

        Args:
            alias (str): The alias name for the module.

        Returns:
            Package: The current package instance for chaining.
        """
        if self.imports:
            self.imports[-1]['alias'] = alias
        return self

    def __enter__(self) -> "Package":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class ImportFrom:
    """
    Represents an import statement for importing specific items from a module.

    Attributes:
        from_name (str): The module name to import from.
        package (Package): The package instance that this import belongs to.
    """
    def __init__(self, from_name: str, package: Package):
        self.from_name = from_name
        self.package = package

    def import_module(self, module_name: str) -> Package:
        """
        Adds an import statement for importing a specific item from a module.

        Args:
            module_name (str): The name of the item to import.

        Returns:
            Package: The package instance for chaining.
        """
        self.package.imports.append({'type': 'from', 'from': self.from_name, 'module': module_name})
        return self.package

    def import_modules(self, *modules: str) -> Package:
        """
        Adds import statements for importing multiple items from a module.

        Args:
            *modules (tuple[str, ...]): The names of the items to import.

        Returns:
            Package: The package instance for chaining.
        """
        for module_name in modules:
            self.import_module(module_name)
        return self.package

class RuntimeDependencyManager:
    """
    Manages runtime package dependencies and installs missing packages if necessary.

    Attributes:
        packages (list[Package]): List of packages to manage.
        install_if_missing (bool): Whether to install missing packages automatically.
        index_url (Optional[str]): The base URL of the Python Package Index.
        extra_index_urls (Optional[list[str]]): Additional URLs of package indexes.
        trusted_hosts (Optional[list[str]]): List of trusted hosts.
    """
    def __init__(
        self, 
        install_if_missing: bool = False,
        index_url: Optional[str] = None,
        extra_index_urls: Optional[list[str]] = None,
        trusted_hosts: Optional[list[str]] = None
    ):
        self.packages: list[Package] = []
        self.install_if_missing = install_if_missing
        self.index_url = index_url
        self.extra_index_urls = extra_index_urls or []
        self.trusted_hosts = trusted_hosts or []

    def package(self, name: str, version_spec: Optional[str] = None, optional: bool = False) -> Package:
        """
        Adds a package to the dependency list.

        Args:
            name (str): The name of the package.
            version_spec (Optional[str]): The version specification of the package.
            optional (bool): Indicates if the package is optional.

        Returns:
            Package: A new Package instance.
        """
        pkg = Package(name, version_spec, optional)
        self.packages.append(pkg)
        return pkg

    def __enter__(self) -> "RuntimeDependencyManager":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.install_if_missing:
            self.install()

    def install(self):
        """
        Installs missing packages and imports all modules.
        """
        missing_packages = self._get_missing_packages()
        if missing_packages:
            self._install_missing_packages(missing_packages)
            importlib.invalidate_caches()
        self._import_all_modules()

    def _get_missing_packages(self) -> list[Package]:
        """
        Returns a list of missing packages.

        Returns:
            list[Package]: List of missing Package instances.
        """
        missing_packages = []
        optional_missing_packages = []

        for pkg in self.packages:
            if not self._are_imports_available(pkg):
                if pkg.optional:
                    optional_missing_packages.append(pkg)
                else:
                    missing_packages.append(pkg)

        if optional_missing_packages:
            logger.warning("Optional packages not found: %s", ", ".join(pkg.name for pkg in optional_missing_packages))

        return missing_packages

    def _are_imports_available(self, pkg: Package) -> bool:
        """
        Checks if all import statements for a package are available.

        Args:
            pkg (Package): The package to check.

        Returns:
            bool: True if all imports are available, False otherwise.
        """
        for imp in pkg.imports:
            if not self._try_import(imp):
                return False
        return True

    def _try_import(self, imp: dict) -> bool:
        """
        Tries to import a module and returns True if successful, False otherwise.

        Args:
            imp (dict): The import statement dictionary.

        Returns:
            bool: True if import is successful, False otherwise.
        """
        try:
            if imp['type'] == 'import':
                module_name = imp['module']
                if 'alias' in imp:
                    exec(f"import {module_name} as {imp['alias']}", globals())
                else:
                    exec(f"import {module_name}", globals())
            elif imp['type'] == 'from':
                from_name = imp['from']
                module_name = imp['module']
                if 'alias' in imp:
                    exec(f"from {from_name} import {module_name} as {imp['alias']}", globals())
                else:
                    exec(f"from {from_name} import {module_name}", globals())
            return True
        except ImportError:
            return False

    def _import_all_modules(self):
        """
        Imports all modules specified in the package dependencies.
        """
        for pkg in self.packages:
            for imp in pkg.imports:
                self._import_module(imp)

    def _import_module(self, imp: dict):
        """
        Imports a module based on the import statement.

        Args:
            imp (dict): The import statement dictionary.
        """
        try:
            if imp['type'] == 'import':
                module_name = imp['module']
                if 'alias' in imp:
                    globals()[imp['alias']] = importlib.import_module(module_name)
                else:
                    globals()[module_name] = importlib.import_module(module_name)
            elif imp['type'] == 'from':
                from_name = imp['from']
                module_name = imp['module']
                if 'alias' in imp:
                    globals()[imp['alias']] = getattr(importlib.import_module(from_name), module_name)
                else:
                    globals()[module_name] = getattr(importlib.import_module(from_name), module_name)
        except ImportError as e:
            logger.error("Error importing %s from %s: %s", imp['module'], imp.get('from', ''), str(e))

    def _install_missing_packages(self, packages: list[Package]):
        """
        Installs missing packages using pip.

        Args:
            packages (list[Package]): List of packages to install.
        """
        try:
            cmd = [sys.executable, '-m', 'pip', 'install']
            
            if self.index_url:
                cmd.extend(['--index-url', self.index_url])
                
            for url in self.extra_index_urls:
                cmd.extend(['--extra-index-url', url])
                
            for host in self.trusted_hosts:
                cmd.extend(['--trusted-host', host])
            
            cmd.extend([f"{pkg.name}{pkg.version_spec}" if pkg.version_spec else pkg.name for pkg in packages])

            subprocess.check_call(cmd)

            for pkg in packages:
                if pkg.version_spec:
                    self._check_version_compatibility(pkg)

        except subprocess.CalledProcessError as e:
            logger.error("Error installing packages: %s", str(e))
            raise PackageInstallationError(f"Error installing packages: {str(e)}")

    def _check_version_compatibility(self, pkg: Package):
        """
        Checks if the installed version of a package satisfies the specified version constraints.

        Args:
            pkg (Package): The package to check.
        """
        try:
            installed_version = version(pkg.name)
            if not self._is_version_satisfying(installed_version, pkg.version_spec):
                raise VersionCompatibilityError(pkg.name, installed_version, pkg.version_spec)
        except PackageNotFoundError:
            raise DependentPackageNotFoundError(pkg.name)
        except VersionCompatibilityError as e:
            logger.error(str(e))
            raise e

    def _is_version_satisfying(self, installed_version: str, version_spec: Optional[str]) -> bool:
        """
        Checks if the installed version satisfies the version specification.

        Args:
            installed_version (str): The installed version of the package.
            version_spec (str): The version specification to check against.

        Returns:
            bool: True if the version satisfies the specification, False otherwise.
        """
        if not version_spec:
            return True

        try:
            return Version(installed_version) in Requirement(f"pkgname{version_spec}").specifier
        except InvalidVersion:
            logger.error("Invalid version: %s", installed_version)
            return False
