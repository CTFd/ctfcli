# Plugins

`ctfcli` plugins are essentially additions to to the command line interface via dynamic class modifications.

*`ctfcli` is an alpha project! The plugin interface is likely to change!*

## Installing a plugin

`ctfcli` expects plugins to be shared via git repositories. The `ctf plugins install` command will clone a given plugin repository to the plugin directory.

```
❯ ctf plugins install URL
```

## Writing a new plugin

### 1. Locate your plugin directory
```
❯ ctf plugins dir
/Users/user/Library/Application Support/ctfcli/plugins
```

### 2. Create a new module

Create a new Python module with an `__init__.py` file inside of it. Inside of the `__init__.py` file you should specify a load function that takes a single argument (the pre-defined command classes)

```
.
└── plugin
    └── __init__.py
```

```
❯ cat plugin/__init__.py
from types import MethodType


def load(commands):
    pass
```

### 3. Define your plugin

```python
from types import MethodType


def cow(self):
    a_cow = """
^__^
(oo)\_______
(__)\       )\\/\\
    ||----w |
    ||     ||
"""
    print(a_cow)


def load(commands):
    plugins = commands["plugins"]
    plugins.cow = MethodType(cow, plugins)
```

### 4. Run your new command

```
❯ ctf plugins cow
Loading /Users/user/Library/Application Support/ctfcli/plugins/plugin/__init__.py as plugin

^__^
(oo)\_______
(__)\       )\/\
    ||----w |
    ||     ||
```