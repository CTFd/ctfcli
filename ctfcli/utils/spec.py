import yaml

from collections import namedtuple
from pathlib import Path
import getpass


Prompt = namedtuple("Prompt", ["text", "type", "default"])


CHALLENGE_SPEC_DOCS = {
    "name": Prompt(text="Name of your challenge", type=None, default=None),
    "author": Prompt(text="Your name or handle", type=None, default=getpass.getuser()),
    "category": Prompt(text="The category of your challenge", type=None, default=None),
    "description": Prompt(
        text="The challenge description shown to the user", type=None, default=None
    ),
    "value": Prompt(
        text="How many points your challenge should be worth", type=int, default=None
    ),
    "version": Prompt(
        text="What version of the challenge specification was used",
        type=None,
        default=None,
    ),
    "image": Prompt(
        text="Docker image used to deploy challenge", type=None, default=None
    ),
    "type": Prompt(text="Challenge type", type=None, default="standard"),
    "attempts": Prompt(
        text="How many attempts a player should have", type=None, default=None
    ),
    "flags": Prompt(
        text="What inputs are the flags for your challenge", type=None, default=None
    ),
    "tags": Prompt(text="Challenge topics", type=None, default=None),
    "files": Prompt(
        text="What files should be shared with the user", type=None, default=None
    ),
    "hints": Prompt(
        text="Hints are used to give players a way to buy or have suggestions",
        type=None,
        default=None,
    ),
    "requirements": Prompt(
        text="Other challenges that must be solved before being able to work on this challenge.",
        type=None,
        default=None,
    ),
}


def blank_challenge_spec():
    pwd = Path(__file__)
    spec = pwd.parent.parent / "spec" / "challenge-example.yml"
    with open(spec) as f:
        blank = yaml.safe_load(f)

    for k in blank:
        if k != "version":
            blank[k] = None

    return blank
