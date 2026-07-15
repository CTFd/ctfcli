import click

from ctfcli.core.properties.base import Property, PropertyContext


class CollectionProperty(Property):
    """A list-valued attribute stored in its own CTFd collection
    (flags, topics, tags, hints). Synced by deleting the existing remote items
    and recreating them from challenge.yml."""

    def create(self, ctx: PropertyContext) -> None:
        if ctx.challenge.get(self.key) and not self.ignored(ctx):
            self.create_items(ctx)

    def sync(self, ctx: PropertyContext) -> None:
        if self.ignored(ctx):
            return

        self.delete_existing(ctx)
        if ctx.challenge.get(self.key):
            self.create_items(ctx)

    def delete_existing(self, ctx: PropertyContext) -> None:
        raise NotImplementedError

    def create_items(self, ctx: PropertyContext) -> None:
        raise NotImplementedError


class FlagsProperty(CollectionProperty):
    key = "flags"
    newline_before = True
    op_order = 10

    def delete_existing(self, ctx: PropertyContext) -> None:
        remote_flags = ctx.api.get("/api/v1/flags").json()["data"]
        for flag in remote_flags:
            if flag["challenge_id"] == ctx.challenge_id:
                r = ctx.api.delete(f"/api/v1/flags/{flag['id']}")
                r.raise_for_status()

    def create_items(self, ctx: PropertyContext) -> None:
        for flag in ctx.challenge["flags"]:
            if type(flag) == str:
                flag_payload = {
                    "content": flag,
                    "type": "static",
                    "challenge_id": ctx.challenge_id,
                }
            else:
                flag_payload = {**flag, "challenge_id": ctx.challenge_id}

            r = ctx.api.post("/api/v1/flags", json=flag_payload)
            r.raise_for_status()

    def pull(self, ctx: PropertyContext, remote_data: dict):
        r = ctx.api.get(f"/api/v1/challenges/{ctx.challenge_id}/flags")
        r.raise_for_status()
        flags = r.json()["data"]
        return [
            (
                f["content"]
                if f["type"] == "static" and (f["data"] is None or f["data"] == "")
                else {
                    "content": f["content"].strip().replace("\r\n", "\n"),
                    "type": f["type"],
                    "data": f["data"],
                }
            )
            for f in flags
        ]


class TopicsProperty(CollectionProperty):
    key = "topics"
    newline_before = True
    op_order = 20

    def is_default(self, value) -> bool:
        return value == []

    def delete_existing(self, ctx: PropertyContext) -> None:
        remote_topics = ctx.api.get(f"/api/v1/challenges/{ctx.challenge_id}/topics").json()["data"]
        for topic in remote_topics:
            r = ctx.api.delete(f"/api/v1/topics?type=challenge&target_id={topic['id']}")
            r.raise_for_status()

    def create_items(self, ctx: PropertyContext) -> None:
        for topic in ctx.challenge["topics"]:
            r = ctx.api.post(
                "/api/v1/topics",
                json={
                    "value": topic,
                    "type": "challenge",
                    "challenge_id": ctx.challenge_id,
                },
            )
            r.raise_for_status()

    def pull(self, ctx: PropertyContext, remote_data: dict):
        r = ctx.api.get(f"/api/v1/challenges/{ctx.challenge_id}/topics")
        r.raise_for_status()
        topics = r.json()["data"]
        return [t["value"] for t in topics]


class TagsProperty(CollectionProperty):
    key = "tags"
    newline_before = True
    op_order = 30

    def is_default(self, value) -> bool:
        return value == []

    def delete_existing(self, ctx: PropertyContext) -> None:
        remote_tags = ctx.api.get("/api/v1/tags").json()["data"]
        for tag in remote_tags:
            if tag["challenge_id"] == ctx.challenge_id:
                r = ctx.api.delete(f"/api/v1/tags/{tag['id']}")
                r.raise_for_status()

    def create_items(self, ctx: PropertyContext) -> None:
        for tag in ctx.challenge["tags"]:
            r = ctx.api.post(
                "/api/v1/tags",
                json={"challenge_id": ctx.challenge_id, "value": tag},
            )
            r.raise_for_status()

    def pull(self, ctx: PropertyContext, remote_data: dict):
        r = ctx.api.get(f"/api/v1/challenges/{ctx.challenge_id}/tags")
        r.raise_for_status()
        tags = r.json()["data"]
        return [t["value"] for t in tags]


class HintsProperty(CollectionProperty):
    key = "hints"
    newline_before = True
    op_order = 50

    def is_default(self, value) -> bool:
        return value == []

    def delete_existing(self, ctx: PropertyContext) -> None:
        remote_hints = ctx.api.get("/api/v1/hints").json()["data"]
        for hint in remote_hints:
            if hint["challenge_id"] == ctx.challenge_id:
                r = ctx.api.delete(f"/api/v1/hints/{hint['id']}")
                r.raise_for_status()

    def create_items(self, ctx: PropertyContext) -> None:
        key_to_id = {}
        target_hints = {}

        # Pass 1: create all hints; hints with requirements get blank content initially
        # to prevent content from being exposed before prerequisites are enforced
        for idx, hint in enumerate(ctx.challenge["hints"]):
            if type(hint) == str:
                hint_payload = {
                    "content": hint,
                    "title": "",
                    "cost": 0,
                    "challenge_id": ctx.challenge_id,
                }
                key = None
            else:
                has_requirements = bool(hint.get("requirements"))
                hint_payload = {
                    "content": "" if has_requirements else hint["content"],
                    "title": hint.get("title", ""),
                    "cost": hint.get("cost", 0),
                    "challenge_id": ctx.challenge_id,
                }
                key = hint.get("key")

            r = ctx.api.post("/api/v1/hints", json=hint_payload)
            r.raise_for_status()

            # Store IDs for processing later
            target_hints[idx] = r.json()["data"]["id"]
            if key is not None:
                key_to_id[key] = r.json()["data"]["id"]

        # Pass 2: set requirements
        for idx, hint in enumerate(ctx.challenge["hints"]):
            if type(hint) == str:
                continue

            requirements = hint.get("requirements", [])
            if not requirements:
                continue

            prerequisite_ids = []
            for req_key in requirements:
                if req_key in key_to_id:
                    preq_hint_id = key_to_id[req_key]
                    prerequisite_ids.append(preq_hint_id)
                else:
                    click.secho(
                        f'Hint key "{req_key}" not found. Skipping invalid hint requirement.',
                        fg="yellow",
                    )

            hint_id = target_hints[idx]

            # Pass 3: fill in real content
            if prerequisite_ids:
                r = ctx.api.patch(
                    f"/api/v1/hints/{hint_id}",
                    json={"requirements": {"prerequisites": prerequisite_ids}},
                )
                r.raise_for_status()

            # Now safe to set the real content
            r = ctx.api.patch(
                f"/api/v1/hints/{hint_id}",
                json={"content": hint["content"]},
            )
            r.raise_for_status()

    def pull(self, ctx: PropertyContext, remote_data: dict):
        r = ctx.api.get(f"/api/v1/challenges/{ctx.challenge_id}/hints")
        r.raise_for_status()
        hints = r.json()["data"]

        # Determine which hints are part of a requirements chain:
        # either they have prerequisites themselves, or are referenced as a prerequisite
        referenced_ids = set()
        for h in hints:
            for pid in (h.get("requirements") or {}).get("prerequisites", []):
                referenced_ids.add(pid)
        hints_with_requirements = {h["id"] for h in hints if (h.get("requirements") or {}).get("prerequisites")}
        needs_key = referenced_ids | hints_with_requirements

        id_to_key = {h["id"]: f"hint-{h['id']}" for h in hints}
        normalized_hints = []
        for h in hints:
            prerequisites = (h.get("requirements") or {}).get("prerequisites", [])
            has_requirements = bool(prerequisites)
            has_cost = h["cost"] > 0
            has_title = bool(h.get("title", ""))
            in_requirements_chain = h["id"] in needs_key

            if not has_cost and not has_requirements and not has_title and not in_requirements_chain:
                normalized_hints.append(h["content"])
            else:
                hint_dict = {"content": h["content"]}
                if in_requirements_chain:
                    hint_dict["key"] = id_to_key[h["id"]]
                if has_title:
                    hint_dict["title"] = h["title"]
                if has_cost:
                    hint_dict["cost"] = h["cost"]
                if has_requirements:
                    hint_dict["requirements"] = [id_to_key[pid] for pid in prerequisites if pid in id_to_key]
                normalized_hints.append(hint_dict)

        return normalized_hints
