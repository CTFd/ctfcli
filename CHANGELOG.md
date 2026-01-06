# Changelog

# 0.1.6 / 2026-01-06

### Added

- Add `sha1sum` to `--ignore` as part of `ctf challenge sync` to allow syncing files when the remote checksum or local checksum is corrupted

### Fixed

- Fix an issue where if deployment returned updated connection info we wouldn't update it in challenge.yml
- Fix an issue where relative paths would not deploy due to a logging error

### Changed

- Challenges without an image will be considered a skipped deploy instead of a failed deploy
- Switch from poetry to uv
- Switch from to ruff

# 0.1.5 / 2025-09-04

### Added

- Support for hint titles
- Support `logic` key for challenges

### Fixed

- Fix issue with resolving relative challenge paths during install

# 0.1.4 / 2025-04-29

### Added

- Added support for `ctf instance` with the `ctf instance config` command which can be used to `get` and `set` configuration on CTFd
- Added `ctf media add`, `ctf media rm`, `ctf media url`
  - Allows ctfcli repos to manage files locally and reference the actual server URLs of media files in Pages
  - Adds concept of replacing placeholders like `{{ media/ctfd.png }}` with the actual URL on the server
- Added the `attribution` field to challenge.yml
- Added the `next` field to challenge.yml
- Added ability to anoymize challenges while specifying prerequisites
- Added specifying CTFd instance URL and access token via envvars: `CTFCLI_URL`, `CTFCLI_ACCESS_TOKEN`

### Fixed

- Fix issue with managing challenges with an empty files section
- Fix issue where images could not be deployed due to being named incorrectly

# 0.1.3 / 2024-08-20

### Added

- Added support for `git subrepo` instead of only `git subtree`
- Added the `--create` switch to `ctf challenge mirror` to create local copies of challenges that exist on a remote CTFd instance

### Fixed

- `ctf challenge {push, pull}` will now push / pull all challenges instead of the challenge in the current working directory.

### Changed

- Use `--load` switch as part of docker build to support alternate build drivers

# 0.1.2 / 2023-02-26

### Added

- Before uploading files to CTFd, ctfcli will check for CTFd's SHA1 hash of the previously uploaded file and skip uploading if it is the same
- Support using remote Docker images instead of having to build and push local images

# 0.1.1 / 2023-12-11

### Added

- Added `ctf challenge mirror` command to pull changes from the remote CTFd instance into the local project

### Fixed

- Properly include challenge.yml when generating a challenge from a template

### Changed

- No longer require a ctfcli project to run all `ctf challenge` (e.g. `new`, `format`, `lint`)

# 0.1.0 / 2023-10-03

### Added

- ctfcli has been separated into two main modules `cli` and `core`. The `core` module now packages logic previously found inside `utils`, wrapped into classes.
- The classes in the `core` module will only print out warnings instead of interrupting the whole process. Everything else will throw exceptions which can be caught and handled however desired
- `cli` and `core` internal modules have type hints
- Improved error messages
- Unit tests have been added for the entire `core` module
- ctfcli will now ask to initialize a new project if one does not exist
- Added `--hidden` to `ctf challenge install` which will deploy the challenge / challenges in a hidden state regardless of their `challenge.yml` value.
- Added `ctf challenge edit <name>` and `ctf challenge edit <name> --dockerfile` to open challenge.yml or Dockerfile for that challenge
- Added aliases under `ctf templates` and `ctf plugins` for `dir` (`path`) and for `view` (`show`)
- Progress bars for `ctf challenge deploy` / `ctf challenge install` / `ctf challenge sync`
- `ctf challenge deploy` will now deploy ALL deployable challenges if a specific challenge is not specified
  - For the SSH and Registry deployments, to facilitate this behaviour the challenge name will be automatically appended. So the host should be for example: `registry://registry.example.com/example-project` and the challenge name will be appended for a full location.
- `ctf challenge deploy` will now also automatically login to the registry with Cloud and Registry deployments.
  - For cloud deployments the instance url must be ctfd assigned (e.g. example.ctfd.io) - this is because to log-in to the registry we require a username like `admin@example.ctfd.io`. The deployment will use the access token as the password.
  - For registry deployment it will look for the `username` and `password` keys inside a `[registry]` section in the project config file.
- ctfcli will read a `LOGLEVEL` environment variable to enable DEBUG logging has been added

### Fixed

- When syncing a challenge to a remote instance, state specified in challenge.yml will now be ignored to prevent accidental challenge leaking
- The CLI will now exit with a 0 if everything went right, and 1 if something went wrong.
  - With `install`/`sync`/`deploy` - exit code will be 1 if ANY of the challenges failed to `install`/`sync`/`deploy`.

### Changed

- Built using poetry and `pyproject.toml`
- `python-fire` has been updated to 0.5.0

### Removed

- Removed the `ctf challenge finalize` command

# 0.0.13 / 2023-07-29

### Added

- Add env variable `CTFCLI_PLUGIN_DIR` to override the default plugin dir for development.
- Add `--directory` argument to `ctfcli challenge add`
  - Can also be called as `ctf challenge add git@github.com:repo.git directory`
  - Useful for grouping challenges into separate directories like: `web/challenge1`.
- `connection_info` specified in challenge.yml will be used instead of details generated by a deploy handler

### Fixed

- Bump PyYAML version to 6.0.1

# 0.0.12 / 2023-06-25

### Added

- Add cloud deploy for hosted CTFd instances
- Add the `protocol` field in the challenge.yml spec
- Further define what other deployment methods should provide & return
- Add the ability to add HTTP cookies to ctfcli requests via the config file

### Fixed

- Allow ignoring category during challenge sync

# 0.0.11 / 2022-11-09

### Added

- Added a restart policy and container name to services deployed via ssh
- Added `--yaml-path` to `ctf challenge add` to specify a specific `challenge.yml` path that will be added to the .ctf config

### Fixed

- Fixed issue in `ctf templates list` where not all templates would be listed
- Bumped version of dependencies to support Python 3.11
  - Bumped `cookiecutter` to 2.1.1
  - Bumped `requests` to 2.28.1
  - Bumped `colorama` to 0.4.6

# 0.0.10 / 2022-03-07

### Added

- Add support for pages in event repos
  - Add the `ctf pages install` command that looks for markdown and html files with frontmatter in a special pages folder
- Add `healthcheck` key in `challenge.yml` to specify a healthcheck script
  - Add `ctf challenge healthcheck [challenge_name]`
- Add `ssl_verify` in the `.ctf/config` file to support SSL verification disabling. `ssl_verify` can be `true` or `false` or a string (specifying the trusted SSL certificates)
- Adds a `--no-git` option to `ctf init` to skip git repo creation in event folder

### Changed

- Allow empty string in CTFd URL and CTFd access token values for `ctf init`
- `ctf init` will not attempt to create git repos when the event folder is in a git repo already
- `ctf init <folder>` can now be used to create the event folder instead of creating the folder beforehand

### Fixed

- Fix issue in `ctf challenge add` where challenges weren't being added to `.ctf/config`
- Fix issue where plugins couldnt be installed if only pip3 was available

# 0.0.9 / 2021-08-06

### Added

- `ctf challenge add/update/restore` will now use git subtrees when working with git repos instead of direct cloning
- `ctf challenge push [challenge]` can now be used to push local changes to the upstream challenge repo
- Added challenge topics from CTFd 3.4 to the challenge.yml spec
- Added challenge topics from CTFd 3.4 to the challenge `sync` and `install` commands
- Added challenge connection_info from CTFd 3.4 to the challenge.yml spec
- Added challenge connection_info from CTFd 3.4 to the challenge `sync` and `install` commands

# 0.0.8 / 2021-06-21

### Added

- Added an `extra` field in challenge specification to support different CTFd challenge types
  - This adds support for dynamic value challenges in CTFd > 3.3.0 (Must have commit [df27d0e7a9e336b86165d41920aa176db4ff0e06](https://github.com/CTFd/CTFd/commit/df27d0e7a9e336b86165d41920aa176db4ff0e06)).
- Improved `ctf challenge lint` to catch some common mistakes in a challenge
- Added an `--ignore` flag to `ctf challenge install` and `ctf challenge sync` to disable installation of certain challenge properties (e.g. flags, tags, hints, etc).
  - Usage: `ctf challenge install challenge.yml --ignore=flags,tags`
  - Usage: `ctf challenge install --ignore=flags,tags`
  - Usage: `ctf challenge sync challenge.yml --ignore=flags,tags`
  - Usage: `ctf challenge sync --ignore=flags,tags`
- Automatic releases from Github to PyPI

### Fixed

- Fix web challenge template for serve.sh
- Changed all Alpine images in Dockerfiles to use Debian
- Add examples or more complicated flag creation examples to challenge specification

# 0.0.7 / 2021-04-15

### Added

- Added the following commands:
  ```
  ctf templates install [repo]
  ctf templates uninstall [folder]
  ctf templates dir
  ctf templates list
  ctf challenge templates
  ```
- Modified `ctf challenge new` to accept and search through installed third-party templates
- Added a parameter to `ctf challenge update` to allow updating a single challenge
- Added a login system for the default web template
- Added a blank challenge template

### Fixed

- Moved challenge template writeups into their own dedicated folder
- Fixed an issue when using CTFd in a subdirectory

# 0.0.6 / 2020-10-07

### Fixed

- Properly default the challenge state to visible during sync

# 0.0.5 / 2020-10-07

### Added

- Added `state` parameter to control whether a challenge is visible or not
- Make the `ctf challenge restore` command be able to take arguments to only restore one challenge
- Add an `ctf challenge update` command to get the latest version of challenges

### Fixed

- Fix the sync and install commands to properly install challenge files relative to the `challenge.yml` path
- Update dependencies in the web challenge template

# 0.0.4 / 2020-06-07

### Added

- `ctfcli` will now load all challenges regardless of visibility when using an
  admin token. Requires CTFd v2.5.0

# 0.0.3 / 2020-04-09

### Fixed

- `ctf init` now saves the CTFd `access_token` properly

# 0.0.2 / 2020-04-02

### Added

- Initial release of ctfcli
- `ctf init` commands
- `ctf challenge` commands
- `ctf config` commands
- `ctf plugins` commands
- README and basic example on plugins

### Changed

- Nothing

### Removed

- Removed initial stub release from source control

# 0.0.1 / 2020-01-01

### Added

- Initial stub release of ctfcli

### Changed

- Nothing

### Removed

- Nothing
