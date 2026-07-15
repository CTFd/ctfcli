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
