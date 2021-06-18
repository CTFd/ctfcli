import getpass
from collections import namedtuple
from pathlib import Path

import yaml

Prompt = namedtuple("Prompt", ["text", "type", "default", "required", "multiple"])


CHALLENGE_SPEC_DOCS = {
    "name": Prompt(
        text="Challenge name or identifier",
        type=None,
        default=None,
        required=True,
        multiple=False,
    ),
    "author": Prompt(
        text="Your name or handle",
        type=None,
        default=getpass.getuser(),
        required=True,
        multiple=False,
    ),
    "category": Prompt(
        text="Challenge category",
        type=None,
        default=None,
        required=True,
        multiple=False,
    ),
    "description": Prompt(
        text="Challenge description shown to the user",
        type=None,
        default=None,
        required=True,
        multiple=False,
    ),
    "value": Prompt(
        text="How many points your challenge should be worth",
        type=int,
        default=None,
        required=True,
        multiple=False,
    ),
    "version": Prompt(
        text="What version of the challenge specification was used",
        type=None,
        default="0.1",
        required=False,
        multiple=False,
    ),
    "image": Prompt(
        text="Docker image used to deploy challenge",
        type=None,
        default=None,
        required=False,
        multiple=False,
    ),
    "type": Prompt(
        text="Type of challenge",
        type=None,
        default="standard",
        required=True,
        multiple=False,
    ),
    "attempts": Prompt(
        text="How many attempts should the player have",
        type=int,
        default=None,
        required=False,
        multiple=False,
    ),
    "flags": Prompt(
        text="Flags that mark the challenge as solved",
        type=None,
        default=None,
        required=False,
        multiple=True,
    ),
    "tags": Prompt(
        text="Tag that denotes a challenge topic",
        type=None,
        default=None,
        required=False,
        multiple=True,
    ),
    "files": Prompt(
        text="Files to be shared with the user",
        type=None,
        default=None,
        required=False,
        multiple=True,
    ),
    "hints": Prompt(
        text="Hints to be shared with the user",
        type=None,
        default=None,
        required=False,
        multiple=True,
    ),
    "requirements": Prompt(
        text="Challenge dependencies that must be solved before this one can be attempted",
        type=None,
        default=None,
        required=False,
        multiple=True,
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
