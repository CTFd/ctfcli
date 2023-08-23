from typing import Dict, List

import click


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
