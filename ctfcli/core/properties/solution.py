import logging
import re
from pathlib import Path

import click

from ctfcli.core.properties.base import Property, PropertyContext

log = logging.getLogger("ctfcli.core.properties.solution")


class SolutionProperty(Property):
    """A solution document uploaded to CTFd, with markdown images uploaded as
    solution files and MkDocs-style snippet includes inlined."""

    key = "solution"
    op_order = 90

    def create(self, ctx: PropertyContext) -> None:
        if not self.ignored(ctx):
            self.upsert(ctx)

    def sync(self, ctx: PropertyContext) -> None:
        if self.ignored(ctx):
            return

        if not self.resolve_path(ctx):
            self.delete_existing(ctx)
        self.upsert(ctx)

    def _parse_definition(self, ctx: PropertyContext) -> tuple[str, str] | None:
        solution = ctx.challenge.get("solution", None)
        if not solution:
            return None

        if type(solution) == str:
            return solution, "hidden"

        if type(solution) != dict:
            click.secho(
                "The solution field must be a string path or an object with path and state",
                fg="red",
            )
            return None

        solution_path = solution.get("path")
        if type(solution_path) != str or not solution_path:
            click.secho("The solution object must define a non-empty string path field", fg="red")
            return None

        solution_state = solution.get("state", "hidden")
        if type(solution_state) != str or solution_state not in ["hidden", "visible", "solved"]:
            click.secho("The solution state must be one of: hidden, visible, solved", fg="red")
            return None

        return solution_path, solution_state

    def resolve_path(self, ctx: PropertyContext) -> tuple[Path, str] | None:
        parsed_solution = self._parse_definition(ctx)
        if not parsed_solution:
            return None

        solution_path_string, solution_state = parsed_solution
        solution_path = ctx.challenge_directory / solution_path_string
        if not solution_path.is_file():
            click.secho(
                f"Solution file '{solution_path_string}' specified, but not found at {solution_path}",
                fg="red",
            )
            return None

        return solution_path, solution_state

    def delete_existing(self, ctx: PropertyContext) -> None:
        remote_solutions = ctx.api.get("/api/v1/solutions").json()["data"]
        for solution in remote_solutions:
            if solution["challenge_id"] == ctx.challenge_id:
                r = ctx.api.delete(f"/api/v1/solutions/{solution['id']}")
                r.raise_for_status()

    def _get_existing_id(self, ctx: PropertyContext) -> int | None:
        r = ctx.api.get("/api/v1/solutions")
        r.raise_for_status()
        remote_solutions = r.json().get("data") or []
        for solution in remote_solutions:
            if solution["challenge_id"] == ctx.challenge_id:
                return solution["id"]
        return None

    def upsert(self, ctx: PropertyContext) -> None:
        resolved_solution = self.resolve_path(ctx)
        if not resolved_solution:
            return
        solution_path, solution_state = resolved_solution

        solution_id = self._get_existing_id(ctx)
        if solution_id is None:
            solution_payload_create = {"challenge_id": ctx.challenge_id, "state": solution_state, "content": ""}

            r = ctx.api.post("/api/v1/solutions", json=solution_payload_create)
            r.raise_for_status()
            solution_id = r.json()["data"]["id"]
        else:
            # Keep solution state in sync and clear stale content before rebuilding references.
            r = ctx.api.patch(
                f"/api/v1/solutions/{solution_id}",
                json={"state": solution_state, "content": ""},
            )
            r.raise_for_status()

        with solution_path.open("r") as solution_file:
            content = solution_file.read()

            # Find all images in the content (markdown format; ignore html format)
            # Markdown format: ![alt text](image_url)
            # Returns tuples: (full_match, alt_text, image_path)
            markdown_images = re.findall(r"(!\[([^\]]*)\]\(([^\)]+)\))", content)

            # Find all snippet includes (MkDocs style: --8<-- "filename")
            # Returns tuples: (full_match, filename)
            snippet_includes = re.findall(r'(--8<--\s+["\']([^"\']+)["\'])', content)

            for mdx, alt, path in markdown_images:
                local_path = solution_path.parent / path
                file_payload = {
                    "type": "solution",
                    "solution_id": solution_id,
                }

                with local_path.open(mode="rb") as file_handle:
                    # Specifically use data= here to send multipart/form-data
                    r = ctx.api.post("/api/v1/files", files={"file": (local_path.name, file_handle)}, data=file_payload)
                    r.raise_for_status()
                    resp = r.json()
                    server_location = resp["data"][0]["location"]

                content = content.replace(mdx, f"![{alt}](/files/{server_location})")

            # Process snippet includes (--8<-- "filename")
            for full_match, filename in snippet_includes:
                snippet_file_path = solution_path.parent / filename
                if snippet_file_path.exists():
                    with snippet_file_path.open("r") as snippet_file:
                        snippet_content = snippet_file.read()
                        # Replace the --8<-- directive with the actual file content
                        content = content.replace(full_match, snippet_content)
                else:
                    log.warning(f"Snippet file not found: {filename}")

            solution_payload_patch = {"content": content}
            r = ctx.api.patch(f"/api/v1/solutions/{solution_id}", json=solution_payload_patch)
            r.raise_for_status()
