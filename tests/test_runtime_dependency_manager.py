#!/usr/bin/env python

import subprocess
import sys
import unittest
from unittest.mock import patch, MagicMock
from importlib.metadata import PackageNotFoundError

from runtime_dependency_manager.manager import (
    RuntimeDependencyManager, 
    DependentPackageNotFoundError, 
    VersionCompatibilityError, 
    Package, 
    ImportFrom, 
    PackageInstallationError
)

class TestRuntimeDependencyManager(unittest.TestCase):

    @patch('runtime_dependency_manager.manager.subprocess.check_call', return_value=None)
    @patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock())
    @patch('runtime_dependency_manager.manager.version', side_effect=['1.1', '3.11.4', '2.7.2', '5.4.1'])
    @patch('runtime_dependency_manager.manager.logger')
    def test_install_missing_packages(self, mock_logger, mock_version, mock_import_module, mock_check_call):
        mgr = RuntimeDependencyManager(install_if_missing=True)
        mgr.index_url = "https://pypi.org/simple"
        mgr.extra_index_urls = ["https://extra.index.url"]
        mgr.trusted_hosts = ["https://trusted.host"]

        package_checks = []
        
        with mgr:
            with mgr.package('IPy', '>=1.1') as pkg:
                pkg.from_module('IPy').import_modules('IP', 'IPSet')

            with mgr.package('pymongo', '>=3.11.4, <4.0.0') as pkg:
                pkg.import_module('pymongo')
                pkg.from_module('bson').import_module('ObjectId')

            with mgr.package('paramiko', '==2.7.2') as pkg:
                pkg.import_modules('SSHClient', 'AutoAddPolicy', 'SSHConfig', 'SSHException')

            with mgr.package('pyyaml', '>=5.4.1, <6.0.0', optional=True) as pkg:
                pkg.import_module('yaml')

        package_checks = [ f'{pkg.name}{pkg.version_spec or ""}' for pkg in mgr.packages if not pkg.optional]
        
        self.assertEqual(mock_import_module.call_count, 9)
        mock_check_call.assert_called_once_with([
            sys.executable, '-m', 'pip', 'install', 
            '--index-url', 'https://pypi.org/simple', 
            '--extra-index-url', 'https://extra.index.url', 
            '--trusted-host', 'https://trusted.host'
        ] + package_checks)
        
        
    @patch('runtime_dependency_manager.manager.subprocess.check_call', return_value=None)
    @patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock())
    @patch('runtime_dependency_manager.manager.version', side_effect=['1.0.0', '3.0.0'])
    @patch('runtime_dependency_manager.manager.logger')
    def test_version_compatibility(self, mock_logger, mock_version, mock_import_module, mock_check_call):
        with self.assertRaises(VersionCompatibilityError):
            with RuntimeDependencyManager(install_if_missing=True) as mgr:
                with mgr.package('pymongo', '>=3.11.4, <4.0.0') as pkg:
                    pkg.import_module('pymongo')

    @patch('runtime_dependency_manager.manager.subprocess.check_call', return_value=None)
    @patch('runtime_dependency_manager.manager.importlib.import_module', side_effect=ImportError)
    @patch('runtime_dependency_manager.manager.version', side_effect=PackageNotFoundError)
    @patch('runtime_dependency_manager.manager.logger')
    def test_package_not_found(self, mock_logger, mock_version, mock_import_module, mock_check_call):
        with self.assertRaises(DependentPackageNotFoundError):
            with RuntimeDependencyManager(install_if_missing=True) as mgr:
                with mgr.package('nonexistent_package', '>=1.0') as pkg:
                    pkg.import_module('nonexistent_module')

    @patch('runtime_dependency_manager.manager.logger')
    def test_package_initialization(self, mock_logger):
        pkg = Package(name='test_package', version_spec='>=1.0', optional=True)
        self.assertEqual(pkg.name, 'test_package')
        self.assertEqual(pkg.version_spec, '>=1.0')
        self.assertTrue(pkg.optional)
        self.assertEqual(pkg.imports, [])

    @patch('runtime_dependency_manager.manager.logger')
    def test_import_statements(self, mock_logger):
        pkg = Package(name='test_package')
        pkg.import_module('test_module')
        pkg.from_module('test_from').import_module('test_import')

        self.assertEqual(pkg.imports, [
            {'type': 'import', 'module': 'test_module'},
            {'type': 'from', 'from': 'test_from', 'module': 'test_import'}
        ])

    @patch('runtime_dependency_manager.manager.logger')
    def test_as_module(self, mock_logger):
        pkg = Package(name='test_package')
        pkg.import_module('test_module').as_module('test_alias')

        self.assertEqual(pkg.imports, [
            {'type': 'import', 'module': 'test_module', 'alias': 'test_alias'}
        ])

    @patch('runtime_dependency_manager.manager.subprocess.check_call', side_effect=subprocess.CalledProcessError(1, 'cmd'))
    @patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock())
    @patch('runtime_dependency_manager.manager.version', side_effect=['1.0.0'])
    @patch('runtime_dependency_manager.manager.logger')
    def test_package_installation_error(self, mock_logger, mock_version, mock_import_module, mock_check_call):
        with self.assertRaises(PackageInstallationError):
            with RuntimeDependencyManager(install_if_missing=True) as mgr:
                with mgr.package('pymongo', '>=3.11.4, <4.0.0') as pkg:
                    pkg.import_module('pymongo')

    @patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock())
    @patch('builtins.globals', return_value={})
    @patch('builtins.exec', MagicMock())
    @patch('runtime_dependency_manager.manager.logger')
    def test_are_imports_available(self, mock_logger, mock_globals, mock_import_module):
        with RuntimeDependencyManager(True) as mgr:
            with mgr.package('test_package') as pkg:
                pkg.import_module('test_module')
        self.assertTrue(mgr._are_imports_available(pkg))

    @patch('runtime_dependency_manager.manager.logger')
    @patch('builtins.globals', return_value={})
    @patch('builtins.exec', MagicMock())
    def test_try_import(self, mock_globals, mock_logger):
        mgr = RuntimeDependencyManager()

        # Test import with alias
        imp = {'type': 'import', 'module': 'test_module', 'alias': 'test_alias'}
        with patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock()):
            self.assertTrue(mgr._try_import(imp))
            exec.assert_any_call(f"import test_module as test_alias", mock_globals.return_value)

        # Test from import with alias
        imp = {'type': 'from', 'from': 'test_from', 'module': 'test_module', 'alias': 'test_alias'}
        with patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock()):
            self.assertTrue(mgr._try_import(imp))
            exec.assert_any_call(f"from test_from import test_module as test_alias", mock_globals.return_value)

    @patch('runtime_dependency_manager.manager.logger')
    @patch('builtins.globals', return_value={})
    @patch('builtins.exec', MagicMock())
    def test_import_module(self, mock_globals, mock_logger):
        mgr = RuntimeDependencyManager()

        # Test import with alias
        imp = {'type': 'import', 'module': 'test_module', 'alias': 'test_alias'}
        with patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock()):
            mgr._import_module(imp)
            self.assertIn('test_alias', mock_globals.return_value)

        # Test from import with alias
        imp = {'type': 'from', 'from': 'test_from', 'module': 'test_module', 'alias': 'test_alias'}
        with patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock()):
            mgr._import_module(imp)
            self.assertIn('test_alias', mock_globals.return_value)

    def test_is_version_satisfying(self):
        mgr = RuntimeDependencyManager()
        self.assertTrue(mgr._is_version_satisfying('1.0.0', None))

if __name__ == '__main__':
    unittest.main()
