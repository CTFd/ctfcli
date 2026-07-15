import subprocess

import click

from ctfcli.core.exceptions import LintException
from ctfcli.utils.tools import strings


def lint_challenge(challenge, skip_hadolint: bool = False, flag_format: str = "flag{") -> bool:
    issues = {"fields": [], "dockerfile": [], "hadolint": [], "files": []}

    # Check if required fields are present
    for field in [
        "name",
        "author",
        "category",
        "description",
        "attribution",
        "value",
    ]:
        # value is allowed to be none if the challenge type is dynamic
        if field == "value" and challenge.get("type") == "dynamic":
            continue

        if challenge.get(field) is None:
            issues["fields"].append(f"challenge.yml is missing required field: {field}")

    # Check that the image field and Dockerfile match
    if (challenge.challenge_directory / "Dockerfile").is_file() and challenge.get("image", "") != ".":
        issues["dockerfile"].append("Dockerfile exists but image field does not point to it")

    # Check that Dockerfile exists and is EXPOSE'ing a port
    if challenge.get("image") == ".":
        dockerfile_path = challenge.challenge_directory / "Dockerfile"
        has_dockerfile = dockerfile_path.is_file()

        if not has_dockerfile:
            issues["dockerfile"].append("Dockerfile specified in 'image' field but no Dockerfile found")

        if has_dockerfile:
            with open(dockerfile_path) as dockerfile:
                dockerfile_source = dockerfile.read()

                if "EXPOSE" not in dockerfile_source:
                    issues["dockerfile"].append("Dockerfile is missing EXPOSE")

                if not skip_hadolint:
                    # Check Dockerfile with hadolint
                    hadolint = subprocess.run(
                        ["docker", "run", "--rm", "-i", "hadolint/hadolint"],
                        capture_output=True,
                        input=dockerfile_source.encode(),
                    )

                    if hadolint.returncode != 0:
                        issues["hadolint"].append(hadolint.stdout.decode())

                else:
                    click.secho("Skipping Hadolint", fg="yellow")

    # Check that all files exist
    files = challenge.get("files") or []
    for challenge_file in files:
        challenge_file_path = challenge.challenge_directory / challenge_file

        if challenge_file_path.is_file() is False:
            issues["files"].append(
                f"Challenge file '{challenge_file}' specified, but not found at {challenge_file_path}"
            )

    # Check that the optional solution file exists
    solution = challenge.get("solution", None)
    if solution:
        solution_file = None
        solution_state = "hidden"

        if type(solution) == str:
            solution_file = solution
        elif type(solution) == dict:
            solution_file = solution.get("path")
            solution_state = solution.get("state", "hidden")

            if type(solution_state) != str or solution_state not in ["hidden", "visible", "solved"]:
                issues["fields"].append("The solution state must be one of: hidden, visible, solved")

        else:
            issues["fields"].append("The solution field must be a string path or an object with path and state")

        if type(solution_file) != str or not solution_file:
            issues["fields"].append("The solution object must define a non-empty string path field")
        else:
            solution_file_path = challenge.challenge_directory / solution_file
            if solution_file_path.is_file() is False:
                issues["files"].append(
                    f"Solution file '{solution_file}' specified, but not found at {solution_file_path}"
                )

    # Check that files don't have a flag in them
    for challenge_file in files:
        challenge_file_path = challenge.challenge_directory / challenge_file

        if not challenge_file_path.exists():
            # The check for files present is above; this is only to look for flags in files that we do have
            continue

        for s in strings(challenge_file_path):
            if flag_format in s:
                s = s.strip()
                issues["files"].append(f"Potential flag found in distributed file '{challenge_file}':\n {s}")

    if any(messages for messages in issues.values() if len(messages) > 0):
        raise LintException(issues=issues)

    return True
