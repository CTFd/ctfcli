from typing import Any

# Sentinel returned by Property.pull for properties that are not part of the
# normalized remote challenge (e.g. files, or keys that only exist locally)
NOT_PULLED = object()


class PropertyContext:
    """Shared state for a single create / sync / mirror / verify run.

    Wraps the Challenge instance and caches remote lookups, so that multiple
    properties do not re-fetch the same resources during one run.
    """

    def __init__(
        self,
        challenge,
        ignore: tuple[str] = (),
        remote_challenge: dict | None = None,
        options: dict | None = None,
    ):
        self.challenge = challenge
        self.ignore = ignore
        self.remote_challenge = remote_challenge
        # run-specific options (e.g. the files directory name during mirror)
        self.options = options or {}
        self._installed_challenges = None

    @property
    def api(self):
        return self.challenge.api

    @property
    def challenge_id(self):
        return self.challenge.challenge_id

    @property
    def challenge_directory(self):
        return self.challenge.challenge_directory

    def installed_challenges(self) -> list:
        if self._installed_challenges is None:
            self._installed_challenges = self.challenge.load_installed_challenges()

        return self._installed_challenges


class Property:
    """A single challenge.yml attribute and its full lifecycle.

    The ordered registry of Property instances (ctfcli.core.properties.PROPERTIES)
    defines the challenge.yml spec: Challenge.save() writes keys in registry order,
    and create/sync/mirror/verify are loops over the registry. Adding a new
    challenge attribute means adding one Property subclass and one registry entry.
    """

    # the challenge.yml key this property is responsible for
    key: str = ""

    # whether Challenge.save() should put a blank line before this key
    newline_before = False

    # relative position of this property's remote operations during create/sync;
    # properties that only contribute to the initial payload keep the default 0
    op_order = 0

    def ignored(self, ctx: PropertyContext) -> bool:
        return self.key in ctx.ignore

    # whether the value is the implicit default, which save() omits and
    # verify() accepts when the key is not present in challenge.yml
    def is_default(self, value: Any) -> bool:
        return False

    # contribution to the initial challenge POST payload
    def create_payload(self, ctx: PropertyContext) -> dict:
        return {}

    # contribution to the initial challenge PATCH payload
    def sync_payload(self, ctx: PropertyContext) -> dict:
        return self.create_payload(ctx)

    # remote operations to run after the challenge has been created
    def create(self, ctx: PropertyContext) -> None:
        pass

    # remote operations to run after the challenge has been patched
    def sync(self, ctx: PropertyContext) -> None:
        pass

    # normalized challenge.yml value built from remote challenge data,
    # or NOT_PULLED when the property is not part of the normalized challenge
    def pull(self, ctx: PropertyContext, remote_data: dict) -> Any:
        return NOT_PULLED

    # whether a local value is equivalent to a pulled remote value
    def matches(self, ctx: PropertyContext, local: Any, remote: Any) -> bool:
        return local == remote

    # whole-run verification hook for properties that are not part of the
    # normalized challenge and cannot be compared with pull() / matches()
    # (e.g. files). Returns True when the property is in sync with the remote.
    def verify(self, ctx: PropertyContext) -> bool:
        return True

    # hook to amend the normalized challenge during mirror, for properties that
    # are not part of the normalized challenge and require side effects instead
    # (e.g. files, which have to be downloaded and written to disk)
    def mirror(self, ctx: PropertyContext, normalized: dict) -> None:
        pass
