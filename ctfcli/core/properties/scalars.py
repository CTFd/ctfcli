from datetime import datetime, timezone
from typing import Any

from ctfcli.core.exceptions import InvalidChallengeFile
from ctfcli.core.properties.base import NOT_PULLED, Property, PropertyContext


class LocalProperty(Property):
    """A key that only lives in challenge.yml and is never synced with the remote
    (e.g. author, image, healthcheck)."""

    def __init__(self, key: str, newline_before: bool = False):
        self.key = key
        self.newline_before = newline_before


class CopiedProperty(Property):
    """A payload field that is copied verbatim from the remote challenge data
    when pulling."""

    def pull(self, ctx: PropertyContext, remote_data: dict):
        if self.key in remote_data:
            return remote_data[self.key]

        return NOT_PULLED


class NameProperty(CopiedProperty):
    key = "name"

    def create_payload(self, ctx: PropertyContext) -> dict:
        return {"name": ctx.challenge["name"]}


class TextProperty(CopiedProperty):
    """category / description / attribution: sent as an empty string when missing,
    reverted to the remote value when ignored during sync, and blanked when
    ignored during create."""

    def __init__(self, key: str):
        self.key = key

    def create_payload(self, ctx: PropertyContext) -> dict:
        if self.ignored(ctx):
            return {self.key: ""}

        return {self.key: ctx.challenge.get(self.key, "")}

    def sync_payload(self, ctx: PropertyContext) -> dict:
        if self.ignored(ctx):
            return {self.key: ctx.remote_challenge[self.key]}

        return {self.key: ctx.challenge.get(self.key, "")}


class DescriptionProperty(TextProperty):
    def __init__(self):
        super().__init__("description")

    def pull(self, ctx: PropertyContext, remote_data: dict):
        return remote_data["description"].strip().replace("\r\n", "\n").replace("\t", "")


class AttributionProperty(TextProperty):
    def __init__(self):
        super().__init__("attribution")

    def pull(self, ctx: PropertyContext, remote_data: dict):
        attribution = remote_data.get("attribution", "")
        if attribution:
            attribution = attribution.strip().replace("\r\n", "\n").replace("\t", "")

        return attribution


class ValueProperty(CopiedProperty):
    key = "value"

    def create_payload(self, ctx: PropertyContext) -> dict:
        # Some challenge types (e.g., dynamic) override value.
        # We can't send it to CTFd because we don't know the current value
        value = ctx.challenge.get("value", None)
        if value is None:
            return {}

        # if value is an int as string, cast it
        if type(value) == str and value.isdigit():
            value = int(value)

        return {"value": value}

    def sync_payload(self, ctx: PropertyContext) -> dict:
        if self.ignored(ctx):
            return {"value": ctx.remote_challenge["value"]}

        return self.create_payload(ctx)


class TypeProperty(CopiedProperty):
    key = "type"

    def is_default(self, value) -> bool:
        return value == "standard"

    def create_payload(self, ctx: PropertyContext) -> dict:
        return {"type": ctx.challenge.get("type", "standard")}

    def sync_payload(self, ctx: PropertyContext) -> dict:
        if self.ignored(ctx):
            return {"type": ctx.remote_challenge["type"]}

        return self.create_payload(ctx)


class AttemptsProperty(Property):
    key = "attempts"
    newline_before = True

    def is_default(self, value) -> bool:
        return value == 0

    def create_payload(self, ctx: PropertyContext) -> dict:
        if self.ignored(ctx):
            return {}

        return {"max_attempts": ctx.challenge.get("attempts", 0)}

    def pull(self, ctx: PropertyContext, remote_data: dict):
        return remote_data["max_attempts"]


class ConnectionInfoProperty(CopiedProperty):
    key = "connection_info"

    def is_default(self, value) -> bool:
        return value is None

    def create_payload(self, ctx: PropertyContext) -> dict:
        if self.ignored(ctx):
            return {}

        return {"connection_info": ctx.challenge.get("connection_info", None)}


class LogicProperty(CopiedProperty):
    key = "logic"

    def create_payload(self, ctx: PropertyContext) -> dict:
        if self.ignored(ctx) or not ctx.challenge.get("logic"):
            return {}

        return {"logic": ctx.challenge.get("logic") or "any"}


class ExtraProperty(Property):
    key = "extra"
    newline_before = True

    def create_payload(self, ctx: PropertyContext) -> dict:
        if self.ignored(ctx):
            return {}

        return {**ctx.challenge.get("extra", {})}

    def pull(self, ctx: PropertyContext, remote_data: dict):
        extra = {key: remote_data[key] for key in ["initial", "decay", "minimum"] if key in remote_data}
        if not extra:
            return NOT_PULLED

        return extra


class ScheduledAtProperty(Property):
    """A timed release: a visible challenge stays hidden from players until this
    moment passes. Always carries an explicit timezone offset - ctfcli never
    assumes one, because guessing would silently release at the wrong time."""

    key = "scheduled_at"
    newline_before = True

    def is_default(self, value) -> bool:
        return value is None

    @staticmethod
    def _datetime_from_iso(value: str) -> datetime:
        # datetime.fromisoformat only accepts a 'Z' suffix on Python 3.11+,
        # so translate it to an explicit offset for the versions that don't
        if value.endswith(("Z", "z")):
            value = value[:-1] + "+00:00"

        return datetime.fromisoformat(value)

    @classmethod
    def parse(cls, value: Any, challenge_file_path=None) -> "datetime | None":
        # Never assume a timezone for scheduled_at: always expect an explicit offset
        if value is None:
            return None

        if isinstance(value, datetime):
            # PyYAML parses unquoted ISO timestamps directly into datetime objects
            parsed = value
        elif isinstance(value, str):
            if not value.strip():
                return None
            try:
                parsed = cls._datetime_from_iso(value)
            except ValueError as e:
                raise InvalidChallengeFile(
                    f"Challenge file at {challenge_file_path} has an invalid 'scheduled_at' value "
                    f"'{value}': expected an ISO 8601 datetime"
                ) from e
        else:
            raise InvalidChallengeFile(
                f"Challenge file at {challenge_file_path} has an invalid 'scheduled_at' value: "
                "expected an ISO 8601 datetime string"
            )

        if parsed.tzinfo is None:
            raise InvalidChallengeFile(
                f"Challenge file at {challenge_file_path} 'scheduled_at' value '{value}' is missing a "
                "timezone. ctfcli does not assume timezones - specify an explicit offset "
                "(e.g. 2026-06-15T12:00:00+00:00 for UTC)"
            )

        return parsed

    @classmethod
    def normalize(cls, value: Any) -> "str | None":
        # CTFd stores and returns scheduled_at as a naive UTC datetime.
        # Make the timezone explicit (UTC) on the challenge
        if not value:
            return None

        parsed = value if isinstance(value, datetime) else cls._datetime_from_iso(value)
        parsed = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)

        return parsed.isoformat()

    def create_payload(self, ctx: PropertyContext) -> dict:
        if self.ignored(ctx):
            return {}

        # parse validates the timezone is explicit and raises otherwise
        parsed = self.parse(ctx.challenge.get("scheduled_at"), ctx.challenge.challenge_file_path)
        return {"scheduled_at": parsed.isoformat() if parsed else None}

    def pull(self, ctx: PropertyContext, remote_data: dict):
        return self.normalize(remote_data.get("scheduled_at"))

    # Compare two scheduled_at values by the instant they represent, so that
    # equivalent times written with different offsets compare as equal
    def matches(self, ctx: PropertyContext, local, remote) -> bool:
        path = ctx.challenge.challenge_file_path
        local_parsed = self.parse(local, path)
        remote_parsed = self.parse(remote, path)

        if local_parsed is None or remote_parsed is None:
            return local_parsed == remote_parsed

        return local_parsed.astimezone(timezone.utc) == remote_parsed.astimezone(timezone.utc)

    # Check that scheduled_at, if present, carries an explicit timezone
    def lint(self, challenge, issues: dict) -> None:
        if challenge.get("scheduled_at") is None:
            return

        try:
            self.parse(challenge["scheduled_at"], challenge.challenge_file_path)
        except InvalidChallengeFile as e:
            issues["fields"].append(str(e))


class StateProperty(CopiedProperty):
    key = "state"
    newline_before = True

    def is_default(self, value) -> bool:
        return value == "visible"

    def create_payload(self, ctx: PropertyContext) -> dict:
        # Hide the challenge for the duration of the sync / creation.
        # Restoring the visibility afterwards is handled by the orchestration
        # in Challenge.create / Challenge.sync
        return {"state": "hidden"}
