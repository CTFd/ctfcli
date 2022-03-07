# Changelog

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
