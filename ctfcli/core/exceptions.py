from typing import Dict, List

import click


class MissingAPIKey(Exception):
    def __str__(self):
        return (
            "Missing API key. "
            "Please set the API key in your configuration file or set the CTFCLI_ACCESS_TOKEN environment variable."
        )


class MissingInstanceURL(Exception):
    def __str__(self):
        return (
            "Missing CTFd instance URL. "
            "Please set the instance URL in your configuration file or set the CTFCLI_URL environment variable."
        )


class ProjectNotInitialized(Exception):
    pass


class ChallengeException(Exception):
    pass


class InvalidChallengeDefinition(ChallengeException):
    pass


class InvalidChallengeFile(ChallengeException):
    pass


class RemoteChallengeNotFound(ChallengeException):
    pass


class LintException(Exception):
    def __init__(self, *args, issues: Dict[str, List[str]] = None):
        self.issues = issues if issues else {}
        super(LintException, self).__init__(*args)

    def print_summary(self):
        for category, issues in self.issues.items():
            if len(issues) > 0:
                click.secho(f"{category.capitalize()}:", fg="yellow")

                prefix = " - " if category != "hadolint" else ""
                for issue in issues:
                    click.echo(f"{prefix}{issue}")

                if category != "hadolint":
                    click.echo()


class PageException(Exception):
    pass


class InvalidPageFormat(PageException):
    pass


class InvalidPageConfiguration(PageException):
    pass


class IllegalPageOperation(PageException):
    pass


class InstanceConfigException(Exception):
    pass
