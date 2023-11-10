# ctfcli

*ctfcli is a tool to manage Capture The Flag events and challenges.*

`ctfcli` provides challenge specifications and templates to make it easier to generate challenges of different categories. It also provides an integration with the [CTFd](https://github.com/CTFd/CTFd/) REST API to allow for command line uploading of challenges and integration with CI/CD build systems.

`ctfcli` features tab completion, a REPL interface (thanks to [Python-Fire](https://github.com/google/python-fire)) and plugin support for custom commands.

*WIP: ctfcli is an alpha project and changes will happen. Be sure to pin versions and read the CHANGELOG when updating.*

# Installation and Usage

ctfcli can be installed with [`pipx`](https://github.com/pypa/pipx) as an executable command:

`pipx install ctfcli`

Alternatively, you can always install it with `pip` as a python module:

`pip install ctfcli`

To install the development version of ctfcli directly from the repository you can use:

`pip install git+https://github.com/CTFd/ctfcli.git`

## 1. Create an Event

Ctfcli turns the current folder into a CTF event git repo. 
It asks for the base url of the CTFd instance you're working with and an access token.

```
❯ ctf init
Please enter CTFd instance URL: https://demo.ctfd.io
Please enter CTFd Admin Access Token: d41d8cd98f00b204e9800998ecf8427e
Do you want to continue with https://demo.ctfd.io and d41d8cd98f00b204e9800998ecf8427e [Y/n]: y
Initialized empty Git repository in /Users/user/Downloads/event/.git/
```

This will create the `.ctf` folder with the `config` file that will specify the URL, access token, and keep a record of
all the challenges dedicated for this event.

## 2. Add challenges

Events are made up of challenges.
Challenges can be made from a subdirectory or pulled from another repository.
GIT-enabled challenges are pulled into the event repo, and a reference is kept in the `.ctf/config` file.

```
❯ ctf challenge add [REPO | FOLDER]
```

##### Local folder:
```
❯ ctf challenge add crypto/stuff
```

##### GIT repository:
```
❯ ctf challenge add https://github.com/challenge.git
Cloning into 'challenge'...
[...]
```

##### GIT repository to a specific subfolder:
```
❯ ctf challenge add https://github.com/challenge.git crypto
Cloning into 'crypto/challenge'...
[...]
```

## 3. Install challenges

Installing a challenge will create the challenge in your CTFd instance using the API.

```
❯ ctf challenge install [challenge]
```

```
❯ ctf challenge install buffer_overflow
Found buffer_overflow/challenge.yml
Loaded buffer_overflow
Installing buffer_overflow
Success!
```

## 4. Sync challenges

Syncing a challenge will update the challenge in your CTFd instance using the API. 
Any changes made in the `challenge.yml` file will be reflected in your instance.

```
❯ ctf challenge sync [challenge]
```

```
❯ ctf challenge sync buffer_overflow
Found buffer_overflow/challenge.yml
Loaded buffer_overflow
Syncing buffer_overflow
Success!
```

## 5. Deploy services

Deploying a challenge will automatically create the challenge service (by default in your CTFd instance).
You can also use a different deployment handler to deploy the service via SSH to your own server, 
or a separate docker registry.

The challenge will also be automatically installed or synced.
Obtained connection info will be added to your `challenge.yml` file.
```
❯ ctf challenge deploy [challenge]
```

```
❯ ctf challenge deploy web-1
Deploying challenge service 'web-1' (web-1/challenge.yml) with CloudDeploymentHandler ...
Challenge service deployed at: https://web-1-example-instance.chals.io
Updating challenge 'web-1'
Success!
```

## 6. Verify challenges

Verifying a challenge will check if the local version of the challenge is the same as one installed in your CTFd instance.

```
❯ ctf challenge verify [challenge]
```

```
❯ ctf challenge verify buffer_overflow
Verifying challenges  [------------------------------------]    0%
Verifying challenges  [####################################]  100%
Success! All challenges verified!
Challenges in sync:
 - buffer_overflow
```

## 7. Mirror changes

Mirroring a challenge is the reverse operation to syncing.
It will update the local version of the challenge with details of the one installed in your CTFd instance.
It will also issue a warning if you have any remote challenges that are not tracked locally.

```
❯ ctf challenge mirror [challenge]
```

```
❯ ctf challenge verify buffer_overflow
Mirorring challenges  [------------------------------------]    0%
Mirorring challenges  [####################################]  100%
Success! All challenges mirrored!
```

## Operations on all challenges

You can perform operations on all challenges defined in your config by simply skipping the challenge parameter.

- `ctf challenge install`
- `ctf challenge sync`
- `ctf challenge deploy`
- `ctf challenge verify`
- `ctf challenge mirror`

# Challenge Templates

`ctfcli` contains pre-made challenge templates to make it faster to create CTF challenges with safe defaults.

```
ctf challenge new
                ├── binary
                ├── crypto
                ├── programming
                └── web
```

```
❯ ctf challenge new binary
/Users/user/.virtualenvs/ctfcli/lib/python3.7/site-packages/ctfcli-0.0.1-py3.7.egg/ctfcli/templates/binary/default
name [Hello]: buffer_overflow

❯ ls -1 buffer_overflow
Makefile
README.md
WRITEUP.md
challenge.yml
dist/
src/
```

**Contributions welcome on improving the challenge templates to make CTF challenges better for everyone!**

# Challenge Specification

`ctfcli` provides a [challenge specification](ctfcli/spec/challenge-example.yml) (`challenge.yml`) that outlines the major details of a challenge.

Every challenge generated by or processed by `ctfcli` should have a `challenge.yml` file.

The specification format has already been tested and used with CTFd in production events but comments, suggestions, and PRs are welcome on the format of `challenge.yml`.

# Plugins

`ctfcli` plugins are essentially additions to the command line interface via dynamic class modifications. See the [plugin documentation page](docs/plugins.md) for a simple example.

*`ctfcli` is an alpha project! The plugin interface is likely to change!*
