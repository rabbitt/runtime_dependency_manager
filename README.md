# runtime_dependency_manager

`runtime_dependency_manager` is a simple Python module for managing dependencies at runtime. It is designed for small scripts that do not use a `requirements.txt` file. This module allows you to define and install dependencies directly within your script, making it ideal for quick scripts and prototypes.

## Installation

You can install `runtime_dependency_manager` using pip:

```bash
pip install runtime_dependency_manager
```
## Usage

Here's an example of how to use `runtime_dependency_manager` in your script:

```python
from runtime_dependency_manager import RuntimeDependencyManager

with RuntimeDependencyManager(install_if_missing=True) as mgr:
    mgr.index_url = "https://pypi.org/simple"

    with mgr.package('IPy', '>=1.1') as pkg:
        pkg.from_module('IPy').import_modules('IP', 'IPSet')

    with mgr.package('pymongo', '>=3.11.4, <4.0.0') as pkg:
        pkg.import_module('pymongo')
        pkg.from_module('bson').import_module('ObjectId')

    with mgr.package('paramiko', '==2.7.2') as pkg:
        pkg.import_modules('SSHClient', 'AutoAddPolicy', 'SSHConfig', 'SSHException')

    with mgr.package('pyyaml', '>=5.4.1, <6.0.0', optional=True) as pkg:
        pkg.import_module('yaml')
```

## API

### RuntimeDependencyManager

#### `RuntimeDependencyManager(install_if_missing=False, index_url=None, extra_index_urls=None, trusted_hosts=None)`

- **install_if_missing**: Whether to install missing packages automatically.
- **index_url**: The base URL of the Python Package Index.
- **extra_index_urls**: Additional URLs of package indexes.
- **trusted_hosts**: List of trusted hosts.

#### Methods

- **`package(name, version_spec=None, optional=False)`**: Adds a package to the dependency list.

### Package

#### Methods

- **`import_module(module_name)`**: Adds an import statement for the specified module.
- **`import_modules(*modules)`**: Adds import statements for multiple modules.
- **`from_module(from_name)`**: Creates an ImportFrom object for importing specific items from a module.
- **`as_module(alias)`**: Specifies an alias for the imported module.

### ImportFrom

#### Methods

- **`import_module(module_name)`**: Adds an import statement for importing a specific item from a module.
- **`import_modules(*modules)`**: Adds import statements for importing multiple items from a module.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

If you would like to contribute, please fork the repository and make changes as you'd like. Pull requests are warmly welcome.

1. Fork the project.
2. Create a feature branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -am 'Add some feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## Acknowledgments

- The Python community for the `packaging` module.
- Anyone who has contributed to this project.
