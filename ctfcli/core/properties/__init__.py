from ctfcli.core.properties.base import NOT_PULLED, Property, PropertyContext
from ctfcli.core.properties.collections import (
    FlagsProperty,
    HintsProperty,
    TagsProperty,
    TopicsProperty,
)
from ctfcli.core.properties.files import FilesProperty
from ctfcli.core.properties.image import ImageProperty
from ctfcli.core.properties.references import (
    ModuleProperty,
    NextProperty,
    RequirementsProperty,
)
from ctfcli.core.properties.scalars import (
    AttemptsProperty,
    AttributionProperty,
    ConnectionInfoProperty,
    DescriptionProperty,
    ExtraProperty,
    LocalProperty,
    LogicProperty,
    NameProperty,
    StateProperty,
    TextProperty,
    TypeProperty,
    ValueProperty,
)
from ctfcli.core.properties.solution import SolutionProperty

# The ordered registry of all challenge.yml properties.
# The order defines the order of keys written by Challenge.save(),
# and should match the order of the documented spec (spec/challenge-example.yml).
PROPERTIES: list[Property] = [
    NameProperty(),
    LocalProperty("author"),
    TextProperty("category"),
    DescriptionProperty(),
    AttributionProperty(),
    ValueProperty(),
    TypeProperty(),
    ExtraProperty(),
    ImageProperty(),
    LocalProperty("protocol"),
    LocalProperty("host"),
    ConnectionInfoProperty(),
    LocalProperty("healthcheck"),
    SolutionProperty(),
    AttemptsProperty(),
    LogicProperty(),
    FlagsProperty(),
    FilesProperty(),
    TopicsProperty(),
    TagsProperty(),
    HintsProperty(),
    RequirementsProperty(),
    NextProperty(),
    ModuleProperty(),
    StateProperty(),
    LocalProperty("version", newline_before=True),
]

_PROPERTIES_BY_KEY: dict[str, Property] = {p.key: p for p in PROPERTIES}


def get_property(key: str) -> Property:
    return _PROPERTIES_BY_KEY[key]


def has_property(key: str) -> bool:
    return key in _PROPERTIES_BY_KEY


# Remote create/sync operations run in a stable, explicit order (op_order) -
# it intentionally differs from the yaml key order: e.g. the solution is
# uploaded last, and payload-only properties don't take part at all
def operation_order() -> list[Property]:
    return sorted(PROPERTIES, key=lambda p: p.op_order)


__all__ = [
    "NOT_PULLED",
    "PROPERTIES",
    "Property",
    "PropertyContext",
    "get_property",
    "has_property",
    "operation_order",
]
