#!/usr/bin/env python

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

import subprocess
import sys
import types
import unittest
from unittest.mock import call, patch, MagicMock
from importlib.metadata import PackageNotFoundError

from runtime_dependency_manager.manager import (
    RuntimeDependencyManager, 
    DependentPackageNotFoundError, 
    VersionCompatibilityError, 
    Package, 
    ImportFrom, 
    PackageInstallationError
)

# Store a reference to the original getattr
original_getattr = getattr

def custom_getattr(obj, name, default=None):
    if name == 'specific_attribute':
        return 'mocked_value'
    elif name == 'raise_exception':
        raise AttributeError('mocked exception')
    else:
        sys.exit(1)
        return original_getattr(obj, name, default)

class TestRuntimeDependencyManager(unittest.TestCase):

    @patch('runtime_dependency_manager.manager.subprocess.run', return_value=subprocess.CompletedProcess((), 0))
    @patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock())
    @patch('runtime_dependency_manager.manager.version', side_effect=['1.1', '3.11.4', '2.7.2','1.0.1'])
    @patch('runtime_dependency_manager.manager.logger')
    def test_install_missing_packages(self, mock_logger, mock_version, mock_import_module, mock_run):
        mgr = RuntimeDependencyManager(install_if_missing=True)
        mgr.index_url = "https://pypi.org/simple"
        mgr.extra_index_urls = ["https://extra.index.url"]
        mgr.trusted_hosts = ["https://trusted.host"]

        with mgr:
            with mgr.package('test_module_a', '>=1.1') as pkg:
                pkg.from_module('test_module_a').import_modules('test_module_a_sub_1', 'test_module_a_sub_2')

            with mgr.package('test_module_b', '>=3.11.4, <4.0.0') as pkg:
                pkg.import_module('test_module_b')
                pkg.from_module('test_module_c').import_module('test_module_c_sub_1')

            with mgr.package('test_module_d', '==2.7.2') as pkg:
                pkg.import_modules('test_module_d_sub_1', 'test_module_d_sub_2', 'test_module_d_sub_3', 'test_module_d_sub_4')

            with mgr.package('test_module_e', '>1.0.0, <2.0.0', optional=True) as pkg:
                pkg.import_module('test_module_e')
                
        packages = [ f'{pkg.name}{pkg.version_spec or ""}' for pkg in mgr.packages if not pkg.optional]
        
        self.assertEqual(mock_import_module.call_count, 9)

        base_command = [
            sys.executable, '-m', 'pip', 'install', 
            '--index-url', 'https://pypi.org/simple', 
            '--extra-index-url', 'https://extra.index.url', 
            '--trusted-host', 'https://trusted.host'
        ]
        
        mock_run.assert_has_calls([
            call(base_command + [package], capture_output=True, text=True) for package in packages
        ])
        
    @patch('runtime_dependency_manager.manager.subprocess.run', return_value=subprocess.CompletedProcess((), 0))
    @patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock())
    @patch('runtime_dependency_manager.manager.version', side_effect=['1.0.0'])
    @patch('runtime_dependency_manager.manager.logger')
    def test_version_compatibility(self, mock_logger, mock_version, mock_import_module, mock_run):
        with self.assertRaises(VersionCompatibilityError):
            with RuntimeDependencyManager(install_if_missing=True) as mgr:
                with mgr.package('test_module', '>=3.11.4, <4.0.0') as pkg:
                    pkg.import_module('test_module')

    @patch('runtime_dependency_manager.manager.subprocess.run', return_value=subprocess.CompletedProcess((), 1, None, 'No matching distribution'))
    @patch('runtime_dependency_manager.manager.importlib.import_module', side_effect=ImportError)
    @patch('runtime_dependency_manager.manager.version', side_effect=PackageNotFoundError)
    @patch('runtime_dependency_manager.manager.logger')
    def test_package_not_found(self, mock_logger, mock_version, mock_import_module, mock_run):
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

    @patch('runtime_dependency_manager.manager.subprocess.run', return_value=subprocess.CompletedProcess((), 1, None, ''))
    @patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock())
    @patch('runtime_dependency_manager.manager.version', side_effect=['1.0.0'])
    @patch('runtime_dependency_manager.manager.logger')
    def test_package_installation_error(self, mock_logger, mock_version, mock_import_module, mock_run):
        with self.assertRaises(PackageInstallationError):
            with RuntimeDependencyManager(install_if_missing=True) as mgr:
                with mgr.package('test_module', '>=3.11.4, <4.0.0') as pkg:
                    pkg.import_module('test_module')

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
    @patch('runtime_dependency_manager.manager.inspect.currentframe', return_value=MagicMock())
    @patch('builtins.exec', MagicMock())
    def test_import_module(self, mock_currentframe, mock_logger):
        mock_globals = {'__name__': '__main__'}
        mock_currentframe.return_value.f_back.f_globals = mock_globals

        mgr = RuntimeDependencyManager()

        # Test import with alias
        imp = {'type': 'import', 'module': 'test_module', 'alias': 'test_alias'}
        with patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock()):
            mgr._import_module(Package('module'), imp)
            self.assertIn('test_alias', mock_globals)

        # Test from import with alias
        imp = {'type': 'from', 'from': 'test_from', 'module': 'test_module', 'alias': 'test_alias'}
        with patch('runtime_dependency_manager.manager.importlib.import_module', return_value=MagicMock()):
            mgr._import_module(Package('test_from'), imp)
            self.assertIn('test_alias', mock_globals)

    @patch('runtime_dependency_manager.manager.logger')
    @patch('runtime_dependency_manager.manager.inspect.currentframe', return_value=MagicMock())
    @patch('runtime_dependency_manager.manager.importlib.import_module', side_effect=ImportError())
    @patch('builtins.exec', MagicMock())
    def test_import_module_errors(self, mock_im, mock_currentframe, mock_logger):
        mock_globals = {'__name__': '__main__'}
        mock_currentframe.return_value.f_back.f_globals = mock_globals

        mgr = RuntimeDependencyManager()

        # Test failed import with alias
        imp = {'type': 'import', 'module': 'test_module', 'alias': 'test_alias'}
        mgr._import_module(Package('module'), imp)
        self.assertRaises(ImportError)

        # Test failed from import with alias
        imp = {'type': 'from', 'from': 'test_from', 'module': 'test_module', 'alias': 'test_alias'}
        mgr._import_module(Package('test_from'), imp)
        self.assertRaises(ImportError)

        class Dummy:
            pass
        
        test_from = types.ModuleType('test_from')
        with patch('runtime_dependency_manager.manager.importlib.import_module', return_value=test_from):
            # Test failed import with alias
            imp = {'type': 'from', 'from': 'test_from', 'module': 'test_module', 'alias': 'test_alias'}
            mgr._import_module(Package('module'), imp)
            self.assertRaises(AttributeError)
            
    def test_is_version_satisfying(self):
        mgr = RuntimeDependencyManager()
        self.assertTrue(mgr._is_version_satisfying('1.0.0', None))

if __name__ == '__main__':
    unittest.main()
