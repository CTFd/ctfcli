import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import ANY, MagicMock, call

from ctfcli.core.challenge import Challenge
from ctfcli.core.exceptions import (
    InvalidChallengeFile,
    LintException,
    RemoteChallengeNotFound,
)
from ctfcli.core.image import Image

BASE_DIR = Path(__file__).parent.parent


class TestLocalChallengeLoading(unittest.TestCase):
    def test_determines_challenge_directory(self):
        challenge_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal" / "challenge.yml"
        challenge = Challenge(challenge_path)

        self.assertIsInstance(challenge.challenge_file_path, Path)
        self.assertEqual(challenge.challenge_directory, BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal")

    def test_raises_if_challenge_yml_does_not_exist(self):
        invalid_challenge_path = BASE_DIR / "fixtures" / "challenges" / "nonexistent" / "challenge.yml"

        with self.assertRaises(
            InvalidChallengeFile, msg=f"Challenge file at {invalid_challenge_path} could not be found"
        ):
            Challenge(invalid_challenge_path)

    def test_raises_if_challenge_yml_is_invalid(self):
        empty_challenge_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-invalid" / "challenge-empty.yml"
        with self.assertRaises(InvalidChallengeFile):
            Challenge(empty_challenge_path)

        invalid_challenge_path = (
            BASE_DIR / "fixtures" / "challenges" / "test-challenge-invalid" / "challenge-invalid.yml"
        )  # noqa
        with self.assertRaises(InvalidChallengeFile):
            Challenge(invalid_challenge_path)

    def test_accepts_path_as_string_and_pathlike(self):
        challenge_pathlike = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal" / "challenge.yml"
        Challenge(challenge_pathlike)

        challenge_path = str(challenge_pathlike)
        Challenge(challenge_path)

    def test_load_challenge(self):
        challenge_path = str(BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal" / "challenge.yml")
        challenge = Challenge(challenge_path)

        self.assertEqual(challenge["name"], "Test Challenge")

    def test_creates_image_if_specified(self):
        challenge_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile" / "challenge.yml"
        challenge = Challenge(challenge_path)

        self.assertIsInstance(challenge.image, Image)
        self.assertEqual(challenge.image.name, "test-challenge")
        self.assertFalse(challenge.image.built)

    def test_does_not_create_image_if_not_specified(self):
        challenge_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal" / "challenge.yml"
        challenge = Challenge(challenge_path)

        self.assertIsNone(challenge.image)


class TestRemoteChallengeLoading(unittest.TestCase):
    @mock.patch("ctfcli.core.challenge.API")
    def test_load_installed_challenge(self, mock_api: MagicMock):
        Challenge.load_installed_challenge(1)

        mock_get = mock_api.return_value.get
        mock_get.assert_called_once_with("/api/v1/challenges/1")

    @mock.patch("ctfcli.core.challenge.API")
    def test_load_installed_challenges(self, mock_api: MagicMock):
        Challenge.load_installed_challenges()

        mock_get = mock_api.return_value.get
        mock_get.assert_called_once_with("/api/v1/challenges?view=admin")


class TestSyncChallenge(unittest.TestCase):
    installed_challenges = [
        {
            "id": 1,
            "type": "standard",
            "name": "Test Challenge",
            "value": 100,
            "solves": 0,
            "solved_by_me": False,
            "category": "test",
            "tags": [],
            "files": [
                "/files/e3a267d9cc21ae3051b6d7ea09e5c6cc/old-test.png",
                "/files/37b9992954f1e6e64e46af6600fb2c0b/old-test.pdf",
            ],
            "template": "view.html",
            "script": "view.js",
        },
        {
            "id": 2,
            "type": "standard",
            "name": "Other Test Challenge",
            "value": 150,
            "solves": 0,
            "solved_by_me": False,
            "category": "test",
            "tags": [],
            "template": "view.html",
            "script": "view.js",
        },
        {
            "id": 3,
            "type": "standard",
            "name": "Yet Another Test Challenge",
            "value": 200,
            "solves": 0,
            "solved_by_me": False,
            "category": "test",
            "tags": [],
            "template": "view.html",
            "script": "view.js",
        },
    ]

    minimal_challenge = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal" / "challenge.yml"
    files_challenge = BASE_DIR / "fixtures" / "challenges" / "test-challenge-files" / "challenge.yml"

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_simple_properties(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(
            self.minimal_challenge,
            {
                "state": "visible",
                "connection_info": "https://example.com",
            },
        )

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "connection_info": "https://example.com",
            "max_attempts": 0,
        }

        mock_api: MagicMock = mock_api_constructor.return_value
        challenge.sync()

        # expect GET calls loading existing resources to check if something needs to be deleted
        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/files?type=challenge"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )
        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/1", json=expected_challenge_payload),
                call().raise_for_status(),
                call("/api/v1/challenges/1", json={"state": "visible"}),
                call().raise_for_status(),
            ]
        )

        mock_api.post.assert_not_called()
        mock_api.delete.assert_not_called()

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_attempts(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge, {"attempts": 5})

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 5,
            "connection_info": None,
        }

        mock_api: MagicMock = mock_api_constructor.return_value
        challenge.sync()

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/files?type=challenge"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )
        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/1", json=expected_challenge_payload),
                call().raise_for_status(),
            ]
        )

        mock_api.post.assert_not_called()
        mock_api.delete.assert_not_called()

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_extra_properties(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(
            self.minimal_challenge,
            {
                "type": "application_target",
                "extra": {"application_spec": "application-spec", "application_name": "application-name"},
            },
        )

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "value": 150,
            "state": "hidden",
            "type": "application_target",
            "application_spec": "application-spec",
            "application_name": "application-name",
            "max_attempts": 0,
            "connection_info": None,
        }

        mock_api: MagicMock = mock_api_constructor.return_value
        challenge.sync()

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/files?type=challenge"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )
        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/1", json=expected_challenge_payload),
                call().raise_for_status(),
            ]
        )

        mock_api.post.assert_not_called()
        mock_api.delete.assert_not_called()

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_flags(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(
            self.minimal_challenge,
            {
                "flags": [
                    "flag{test-flag}",
                    {
                        "type": "static",
                        "content": "flag{test-static}",
                        "data": "case_insensitive",
                    },
                    {
                        "type": "regex",
                        "content": "flag{test-regex-.*}",
                        "data": "case_insensitive",
                    },
                ]
            },
        )

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 0,
            "connection_info": None,
        }

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": [
                {"challenge_id": 1, "id": 1, "type": "static", "content": "flag{old-flag}", "data": "", "challenge": 1},
                {
                    "challenge_id": 1,
                    "id": 2,
                    "type": "regex",
                    "content": "flag{.*}",
                    "data": "case_insensitive",
                    "challenge": 1,
                },
            ],
        }

        challenge.sync(ignore=["files"])

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )

        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/1", json=expected_challenge_payload),
                call().raise_for_status(),
            ]
        )

        mock_api.post.assert_has_calls(
            [
                call("/api/v1/flags", json={"content": "flag{test-flag}", "type": "static", "challenge_id": 1}),
                call().raise_for_status(),
                call(
                    "/api/v1/flags",
                    json={
                        "content": "flag{test-static}",
                        "type": "static",
                        "data": "case_insensitive",
                        "challenge_id": 1,
                    },
                ),
                call().raise_for_status(),
                call(
                    "/api/v1/flags",
                    json={
                        "content": "flag{test-regex-.*}",
                        "type": "regex",
                        "data": "case_insensitive",
                        "challenge_id": 1,
                    },
                ),
                call().raise_for_status(),
            ]
        )

        mock_api.delete.assert_has_calls(
            [
                call("/api/v1/flags/1"),
                call().raise_for_status(),
                call("/api/v1/flags/2"),
                call().raise_for_status(),
            ]
        )

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_topics(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge, {"topics": ["new-topic-1", "new-topic-2"]})

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 0,
            "connection_info": None,
        }

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": [
                {"id": 1, "challenge_id": 1, "topic_id": 1, "value": "topic-1"},
                {"id": 2, "challenge_id": 1, "topic_id": 2, "value": "topic-2"},
            ],
        }

        challenge.sync(ignore=["files"])

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )

        mock_api.patch.assert_has_calls(
            [call("/api/v1/challenges/1", json=expected_challenge_payload), call().raise_for_status()]
        )

        mock_api.post.assert_has_calls(
            [
                call("/api/v1/topics", json={"value": "new-topic-1", "type": "challenge", "challenge_id": 1}),
                call().raise_for_status(),
                call("/api/v1/topics", json={"value": "new-topic-2", "type": "challenge", "challenge_id": 1}),
                call().raise_for_status(),
            ]
        )

        mock_api.delete.assert_has_calls(
            [
                call("/api/v1/topics?type=challenge&target_id=1"),
                call().raise_for_status(),
                call("/api/v1/topics?type=challenge&target_id=2"),
                call().raise_for_status(),
            ]
        )

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_tags(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge, {"tags": ["new-tag-1", "new-tag-2"]})

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 0,
            "connection_info": None,
        }

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": [
                {"id": 1, "challenge_id": 1, "tag_id": 1, "value": "tag-1"},
                {"id": 2, "challenge_id": 1, "tag_id": 2, "value": "tag-2"},
            ],
        }

        challenge.sync(ignore=["files"])

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )

        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/1", json=expected_challenge_payload),
                call().raise_for_status(),
            ]
        )

        mock_api.post.assert_has_calls(
            [
                call("/api/v1/tags", json={"value": "new-tag-1", "challenge_id": 1}),
                call().raise_for_status(),
                call("/api/v1/tags", json={"value": "new-tag-2", "challenge_id": 1}),
                call().raise_for_status(),
            ]
        )

        mock_api.delete.assert_has_calls(
            [
                call("/api/v1/tags/1"),
                call().raise_for_status(),
                call("/api/v1/tags/2"),
                call().raise_for_status(),
            ]
        )

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_files(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.files_challenge)

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 0,
            "connection_info": None,
        }

        def mock_get(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/challenges/1":
                mock_response = MagicMock()
                mock_response.json.return_value = {"success": True, "data": self.installed_challenges[0]}
                return mock_response

            if path == "/api/v1/files?type=challenge":
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "success": True,
                    "data": [
                        {"id": 1, "type": "challenge", "location": "e3a267d9cc21ae3051b6d7ea09e5c6cc/old-test.png"},
                        {"id": 2, "type": "challenge", "location": "37b9992954f1e6e64e46af6600fb2c0b/old-test.pdf"},
                    ],
                }
                return mock_response

            return MagicMock()

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.get.side_effect = mock_get

        challenge.sync()

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/files?type=challenge"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )

        mock_api.patch.assert_has_calls(
            [call("/api/v1/challenges/1", json=expected_challenge_payload), call().raise_for_status()]
        )

        mock_api.post.assert_has_calls(
            [
                call("/api/v1/files", files=ANY, data={"challenge_id": 1, "type": "challenge"}),
                call().raise_for_status(),
            ]
        )

        mock_api.delete.assert_has_calls(
            [
                call("/api/v1/files/1"),
                call().raise_for_status(),
                call("/api/v1/files/2"),
                call().raise_for_status(),
            ]
        )

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_exits_if_updated_files_do_not_exist(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge, {"files": ["files/nonexistent.png"]})

        mock_api: MagicMock = mock_api_constructor.return_value

        with self.assertRaises(InvalidChallengeFile) as e:
            challenge.sync()
            self.assertEqual(e.exception.message, "File files/nonexistent.png could not be loaded")

        mock_api.get.assert_not_called()
        mock_api.patch.assert_not_called()
        mock_api.post.assert_not_called()
        mock_api.delete.assert_not_called()

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_hints(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(
            self.minimal_challenge,
            {
                "hints": [
                    "free hint",
                    {
                        "content": "paid hint",
                        "cost": 100,
                    },
                ]
            },
        )

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 0,
            "connection_info": None,
        }

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": [
                {"challenge_id": 1, "id": 1, "content": "old free hint", "cost": 0, "challenge": 1},
                {"challenge_id": 1, "id": 2, "content": "old paid hint", "cost": 50, "challenge": 1},
            ],
        }

        challenge.sync(ignore=["files"])

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )

        mock_api.patch.assert_has_calls(
            [call("/api/v1/challenges/1", json=expected_challenge_payload), call().raise_for_status()]
        )

        mock_api.post.assert_has_calls(
            [
                call("/api/v1/hints", json={"content": "free hint", "cost": 0, "challenge_id": 1}),
                call().raise_for_status(),
                call("/api/v1/hints", json={"content": "paid hint", "cost": 100, "challenge_id": 1}),
                call().raise_for_status(),
            ]
        )

        mock_api.delete.assert_has_calls(
            [
                call("/api/v1/hints/1"),
                call().raise_for_status(),
                call("/api/v1/hints/2"),
                call().raise_for_status(),
            ]
        )

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_requirements(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge, {"requirements": ["Other Test Challenge", 3]})

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 0,
            "connection_info": None,
        }

        mock_api: MagicMock = mock_api_constructor.return_value

        challenge.sync()

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
            ]
        )

        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/1", json=expected_challenge_payload),
                call().raise_for_status(),
                # challenge 2 retrieved by name, and challenge 3 retrieved by id
                call("/api/v1/challenges/1", json={"requirements": {"prerequisites": [2, 3]}}),
                call().raise_for_status(),
            ]
        )

        mock_api.post.assert_not_called()
        mock_api.delete.assert_not_called()

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.click.secho")
    @mock.patch("ctfcli.core.challenge.API")
    def test_challenge_cannot_require_itself(
        self, mock_api_constructor: MagicMock, mock_secho: MagicMock, *args, **kwargs
    ):
        challenge = Challenge(self.minimal_challenge, {"requirements": ["Test Challenge", 2]})

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 0,
            "connection_info": None,
        }

        def mock_get(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/challenges/1":
                mock_response = MagicMock()
                mock_response.json.return_value = {"success": True, "data": self.installed_challenges[0]}
                return mock_response

            return MagicMock()

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.get.side_effect = mock_get

        challenge.sync()

        mock_secho.assert_called_once_with(
            "Challenge cannot require itself. Skipping invalid requirement.", fg="yellow"
        )

        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/1", json=expected_challenge_payload),
                call().raise_for_status(),
                call("/api/v1/challenges/1", json={"requirements": {"prerequisites": [2]}}),
                call().raise_for_status(),
            ],
            any_order=True,
        )

        # test invalid requirement has not been set
        self.assertNotIn(
            call("/api/v1/challenges/1", json={"requirements": {"prerequisites": [1, 2]}}),
            mock_api.patch.call_args_list,
        )

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
            ]
        )
        mock_api.post.assert_not_called()
        mock_api.delete.assert_not_called()

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_defaults_to_standard_challenge_type(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge)
        del challenge["type"]

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 0,
            "connection_info": None,
        }

        mock_api: MagicMock = mock_api_constructor.return_value

        challenge.sync()

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/files?type=challenge"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )
        mock_api.patch.assert_has_calls(
            [call("/api/v1/challenges/1", json=expected_challenge_payload), call().raise_for_status()]
        )

        mock_api.post.assert_not_called()
        mock_api.delete.assert_not_called()

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_defaults_to_visible_state(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge)
        del challenge["state"]

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "max_attempts": 0,
            "connection_info": None,
            # initial patch should set the state to hidden for the duration of the update
            "state": "hidden",
        }

        mock_api: MagicMock = mock_api_constructor.return_value

        challenge.sync()

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/files?type=challenge"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )
        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/1", json=expected_challenge_payload),
                call().raise_for_status(),
                # this tests the real assigned state
                call("/api/v1/challenges/1", json={"state": "visible"}),
                call().raise_for_status(),
            ]
        )

        mock_api.post.assert_not_called()
        mock_api.delete.assert_not_called()

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_does_not_update_dynamic_value(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(
            self.minimal_challenge,
            {
                "value": None,
                "type": "dynamic",
            },
        )

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "dynamic",
            "state": "hidden",
            "max_attempts": 0,
            "connection_info": None,
        }

        mock_api: MagicMock = mock_api_constructor.return_value

        challenge.sync()

        mock_api.patch.assert_has_calls(
            [call("/api/v1/challenges/1", json=expected_challenge_payload), call().raise_for_status()]
        )

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=[])
    @mock.patch("ctfcli.core.challenge.API")
    def test_exits_if_challenges_do_not_exist(self, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge)

        with self.assertRaises(RemoteChallengeNotFound) as e:
            challenge.sync()
            self.assertEqual(e.exception.message, "Could not load any remote challenges")

    @mock.patch(
        "ctfcli.core.challenge.Challenge.load_installed_challenges",
        return_value=[{"id": 1337, "name": "Dummy Challenge"}],
    )
    @mock.patch("ctfcli.core.challenge.API")
    def test_exits_if_challenge_does_not_exist(self, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge)
        with self.assertRaises(RemoteChallengeNotFound) as e:
            challenge.sync()
            self.assertEqual(e.exception.message, "Could not load remote challenge with name 'Test Challenge'")

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_updates_multiple_attributes_at_once(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(
            self.files_challenge,
            {
                "state": "visible",
                "attempts": 5,
                "connection_info": "https://example.com",
                "flags": ["flag{test-flag}"],
                # files are defined in the test challenge.yml, but they are provided here too for clarity
                "files": ["files/test.png", "files/test.pdf"],
                "topics": ["new-topic-1"],
                "tags": ["new-tag-1"],
                "hints": ["free hint"],
                "requirements": [2],
            },
        )

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "New Test",
            "description": "New Test Description",
            "type": "standard",
            "value": 150,
            "state": "hidden",
            "max_attempts": 5,
            "connection_info": "https://example.com",
        }

        mock_api: MagicMock = mock_api_constructor.return_value

        challenge.sync()

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/challenges/1"),
                call("/api/v1/flags"),
                call("/api/v1/challenges/1/topics"),
                call("/api/v1/tags"),
                call("/api/v1/files?type=challenge"),
                call("/api/v1/hints"),
            ],
            any_order=True,
        )

        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/1", json=expected_challenge_payload),
                call().raise_for_status(),
                call("/api/v1/challenges/1", json={"requirements": {"prerequisites": [2]}}),
                call().raise_for_status(),
                call("/api/v1/challenges/1", json={"state": "visible"}),
                call().raise_for_status(),
            ]
        )

        mock_api.post.assert_has_calls(
            [
                call("/api/v1/flags", json={"content": "flag{test-flag}", "type": "static", "challenge_id": 1}),
                call().raise_for_status(),
                call("/api/v1/topics", json={"value": "new-topic-1", "type": "challenge", "challenge_id": 1}),
                call().raise_for_status(),
                call("/api/v1/tags", json={"challenge_id": 1, "value": "new-tag-1"}),
                call().raise_for_status(),
                call("/api/v1/files", files=ANY, data={"challenge_id": 1, "type": "challenge"}),
                call().raise_for_status(),
                call("/api/v1/hints", json={"content": "free hint", "cost": 0, "challenge_id": 1}),
                call().raise_for_status(),
            ]
        )

        mock_api.delete.assert_not_called()

    def test_does_not_update_ignored_attributes(self):
        properties = [
            # fmt: off
            # simple types
            "category", "description", "type", "value", "attempts", "connection_info", "state",
            # complex types
            "extra", "flags", "topics", "tags", "files", "hints", "requirements",
            # fmt: on
        ]

        remote_installed_challenge = {
            "name": "Test Challenge",
            "category": "Old Category",
            "description": "Old Description",
            "type": "some-custom-type",
            "value": 100,
            "state": "visible",
            "max_attempts": 0,
            "connection_info": None,
        }

        for p in properties:
            with (
                mock.patch("ctfcli.core.challenge.API") as mock_api_constructor,
                mock.patch(
                    "ctfcli.core.challenge.Challenge.load_installed_challenge", return_value=remote_installed_challenge
                ) as mock_load_installed_challenge,
                mock.patch(
                    "ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=self.installed_challenges
                ) as mock_load_installed_challenges,
            ):
                challenge = Challenge(
                    self.minimal_challenge,
                    {
                        "state": "visible",
                    },
                )

                expected_challenge_payload = {
                    "name": "Test Challenge",
                    "category": "New Test",
                    "description": "New Test Description",
                    "type": "standard",
                    "value": 150,
                    "state": "hidden",
                    "max_attempts": 0,
                    "connection_info": None,
                }

                # expect the payload to modify values with new ones from challenge.yml
                # except the ignored property
                match p:
                    # expect these to be in the payload, with the values as on the remote (unchanged):
                    case "value":
                        expected_challenge_payload["value"] = remote_installed_challenge["value"]
                        challenge["value"] = 200

                    case "category" | "description" | "type":
                        expected_challenge_payload[p] = remote_installed_challenge[p]
                        challenge[p] = "new-value"

                    # expect these are just not modified (not included in the payload or not modified with requests):
                    # in case of attempts and connection_info we have to explicitly delete them from the payload
                    # as they are  expected to be present in their default value with all other requests
                    case "attempts":
                        challenge["attempts"] = 5
                        del expected_challenge_payload["max_attempts"]

                    case "connection_info":
                        challenge["connection_info"] = "https://example.com"
                        del expected_challenge_payload["connection_info"]

                    case "state":
                        challenge[p] = "new-value"

                    case "extra":
                        challenge["extra"] = {"new-value": "new-value"}

                    case "flags" | "topics" | "tags" | "files" | "hints" | "requirements":
                        challenge[p] = ["new-value"]

                challenge.sync(ignore=[p])

                mock_api: MagicMock = mock_api_constructor.return_value
                mock_load_installed_challenge.assert_has_calls([call(1)])
                mock_load_installed_challenges.assert_called_once_with()
                mock_api.patch.assert_has_calls(
                    [
                        call("/api/v1/challenges/1", json=expected_challenge_payload),
                        call().raise_for_status(),
                        call("/api/v1/challenges/1", json={"state": "visible"}),
                        call().raise_for_status(),
                    ]
                )
                mock_api.post.assert_not_called()
                mock_api.delete.assert_not_called()


class TestCreateChallenge(unittest.TestCase):
    installed_challenges = [
        {
            "id": 1,
            "type": "standard",
            "name": "Test Challenge",
            "value": 150,
            "solves": 0,
            "solved_by_me": False,
            "category": "test",
            "tags": [],
            "template": "view.html",
            "script": "view.js",
        },
        {
            "id": 2,
            "type": "standard",
            "name": "Other Test Challenge",
            "value": 200,
            "solves": 0,
            "solved_by_me": False,
            "category": "test",
            "tags": [],
            "template": "view.html",
            "script": "view.js",
        },
    ]

    minimal_challenge = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal" / "challenge.yml"
    full_challenge = BASE_DIR / "fixtures" / "challenges" / "test-challenge-full" / "challenge.yml"

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_creates_standard_challenge(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.full_challenge)

        expected_challenge_payload = {
            "name": "Test Challenge",
            "category": "Test",
            "description": "Test Description",
            "value": 150,
            "max_attempts": 5,
            "type": "standard",
            "connection_info": "https://example.com",
            "extra_property": "extra_property_value",
            "state": "hidden",
        }

        def mock_post(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/challenges":
                mock_response = MagicMock()
                mock_response.json.return_value = {"success": True, "data": {"id": 3}}
                return mock_response

            return MagicMock()

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.post.side_effect = mock_post

        challenge.create()

        mock_api.get.assert_not_called()
        mock_api.post.assert_has_calls(
            [
                call("/api/v1/challenges", json=expected_challenge_payload),
                # flags
                call("/api/v1/flags", json={"type": "static", "content": "flag{test-flag}", "challenge_id": 3}),
                call(
                    "/api/v1/flags",
                    json={
                        "type": "static",
                        "content": "flag{test-static}",
                        "data": "case_insensitive",
                        "challenge_id": 3,
                    },
                ),
                call(
                    "/api/v1/flags",
                    json={
                        "type": "regex",
                        "content": "flag{test-regex-.*}",
                        "data": "case_insensitive",
                        "challenge_id": 3,
                    },
                ),
                # topics
                call("/api/v1/topics", json={"value": "topic-1", "type": "challenge", "challenge_id": 3}),
                call("/api/v1/topics", json={"value": "topic-2", "type": "challenge", "challenge_id": 3}),
                # tags
                call("/api/v1/tags", json={"challenge_id": 3, "value": "tag-1"}),
                call("/api/v1/tags", json={"challenge_id": 3, "value": "tag-2"}),
                # files
                call("/api/v1/files", files=ANY, data={"challenge_id": 3, "type": "challenge"}),
                # hints
                call("/api/v1/hints", json={"content": "free hint", "cost": 0, "challenge_id": 3}),
                call("/api/v1/hints", json={"content": "paid hint", "cost": 100, "challenge_id": 3}),
            ]
        )

        mock_api.patch.assert_has_calls(
            [
                call("/api/v1/challenges/3", json={"requirements": {"prerequisites": [1, 2]}}),
                call().raise_for_status(),
                call("/api/v1/challenges/3", json={"state": "visible"}),
                call().raise_for_status(),
            ]
        )

        mock_api.delete.assert_not_called()

    @mock.patch("ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=installed_challenges)
    @mock.patch("ctfcli.core.challenge.API")
    def test_exits_if_files_do_not_exist(self, mock_api_constructor: MagicMock, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge, {"files": ["files/nonexistent.png"]})
        mock_api: MagicMock = mock_api_constructor.return_value

        with self.assertRaises(InvalidChallengeFile) as e:
            challenge.create()
            self.assertEqual(e.exception.message, "File files/nonexistent.png could not be loaded")

        mock_api.get.assert_not_called()
        mock_api.patch.assert_not_called()
        mock_api.post.assert_not_called()
        mock_api.delete.assert_not_called()

    def test_does_not_set_ignored_attributes(self):
        # fmt:off
        properties = [
            "value", "category", "description", "attempts", "connection_info", "state",  # simple types
            "extra", "flags", "topics", "tags", "files", "hints", "requirements"  # complex types
        ]
        # fmt:on

        for p in properties:
            with (
                mock.patch("ctfcli.core.challenge.API") as mock_api_constructor,
                mock.patch("ctfcli.core.challenge.click.secho") as mock_secho,
                mock.patch(
                    "ctfcli.core.challenge.Challenge.load_installed_challenges", return_value=self.installed_challenges
                ),
            ):
                challenge = Challenge(self.minimal_challenge, {"state": "visible"})

                expected_challenge_payload = {
                    "name": "Test Challenge",
                    "category": "New Test",
                    "description": "New Test Description",
                    "type": "standard",
                    "value": 150,
                    "state": "hidden",
                    "max_attempts": 0,
                    "connection_info": None,
                }

                # add a property that should be defined but ignored
                match p:
                    # expect a warning, and to disobey the ignore directive
                    case "value":
                        challenge["value"] = 200
                        expected_challenge_payload["value"] = 200

                    # expect a warning, and to disobey the ignore directive
                    case "type":
                        challenge["type"] = "custom-type"
                        expected_challenge_payload[p] = "custom-type"

                    # expect these to be in the payload, with the defaults or empty:
                    case "category" | "description":
                        challenge[p] = "new-value"
                        expected_challenge_payload[p] = ""

                    # expect these are just not modified (not included in the payload or not modified with requests):
                    case "attempts":
                        challenge["attempts"] = 5
                        del expected_challenge_payload["max_attempts"]

                    case "connection_info":
                        challenge["connection_info"] = "https://example.com"
                        del expected_challenge_payload["connection_info"]

                    case "state":
                        challenge[p] = "new-value"

                    case "extra":
                        challenge["extra"] = {"new-value": "new-value"}

                    case "flags" | "topics" | "tags" | "files" | "hints" | "requirements":
                        challenge[p] = ["new-value"]

                def mock_post(*args, **kwargs):
                    path = args[0]

                    if path == "/api/v1/challenges":
                        mock_response = MagicMock()
                        mock_response.json.return_value = {"success": True, "data": {"id": 3}}
                        return mock_response

                    return MagicMock()

                mock_api: MagicMock = mock_api_constructor.return_value
                mock_api.post.side_effect = mock_post

                challenge.create(ignore=[p])

                if p == "value" or p == "type":
                    mock_secho.assert_called_once_with(
                        f"Attribute '{p}' cannot be ignored when creating a challenge", fg="yellow"
                    )

                # if the state is ignored, expect to default to visible and un-hide the challenge
                mock_api.patch.assert_has_calls(
                    [call("/api/v1/challenges/3", json={"state": "visible"}), call().raise_for_status()]
                )
                mock_api.post.assert_called_once_with("/api/v1/challenges", json=expected_challenge_payload)
                mock_api.get.assert_not_called()
                mock_api.delete.assert_not_called()


class TestLintChallenge(unittest.TestCase):
    minimal_challenge = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal" / "challenge.yml"
    files_challenge = BASE_DIR / "fixtures" / "challenges" / "test-challenge-files" / "challenge.yml"
    dockerfile_challenge = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile" / "challenge.yml"
    invalid_dockerfile_challenge = (
        BASE_DIR / "fixtures" / "challenges" / "test-challenge-invalid-dockerfile" / "challenge.yml"
    )

    def test_validates_required_fields(self):
        required_fields = ["name", "author", "category", "description", "value"]
        for field in required_fields:
            challenge = Challenge(self.minimal_challenge)
            del challenge[field]

            with self.assertRaises(LintException) as e:
                challenge.lint()

            expected_lint_issues = {
                "fields": [f"challenge.yml is missing required field: {field}"],
                "dockerfile": [],
                "hadolint": [],
                "files": [],
            }
            self.assertDictEqual(expected_lint_issues, e.exception.issues)

    def test_validates_challenge_yml_points_to_dockerfile(self):
        challenge = Challenge(self.minimal_challenge, {"image": "."})

        with self.assertRaises(LintException) as e:
            challenge.lint()

        expected_lint_issues = {
            "fields": [],
            "dockerfile": ["Dockerfile specified in 'image' field but no Dockerfile found"],
            "hadolint": [],
            "files": [],
        }
        self.assertDictEqual(expected_lint_issues, e.exception.issues)

    def test_validates_challenge_yml_does_not_point_to_dockerfile(self):
        challenge = Challenge(self.dockerfile_challenge)
        del challenge["image"]

        with self.assertRaises(LintException) as e:
            challenge.lint()

        expected_lint_issues = {
            "fields": [],
            "dockerfile": ["Dockerfile exists but image field does not point to it"],
            "hadolint": [],
            "files": [],
        }
        self.assertDictEqual(expected_lint_issues, e.exception.issues)

    @mock.patch("ctfcli.core.challenge.click.secho")
    def test_validates_dockerfile_exposes_port(self, mock_secho: MagicMock):
        challenge = Challenge(self.invalid_dockerfile_challenge)

        with self.assertRaises(LintException) as e:
            challenge.lint(skip_hadolint=True)

        expected_lint_issues = {
            "fields": [],
            "dockerfile": ["Dockerfile is missing EXPOSE"],
            "hadolint": [],
            "files": [],
        }

        mock_secho.assert_called_once_with("Skipping Hadolint", fg="yellow")
        self.assertDictEqual(expected_lint_issues, e.exception.issues)

    @mock.patch("ctfcli.core.challenge.subprocess.run")
    def test_runs_hadolint(self, mock_run: MagicMock):
        class RunResult:
            def __init__(self, return_code):
                self.returncode = return_code
                self.stdout = b"-:1 DL3006 warning: Always tag the version of an image explicitly"

        mock_run.return_value = RunResult(1)
        challenge = Challenge(self.dockerfile_challenge)

        with self.assertRaises(LintException) as e:
            challenge.lint()

        mock_run.assert_called_once_with(
            ["docker", "run", "--rm", "-i", "hadolint/hadolint"], stdout=-1, stderr=-1, input=ANY
        )

        expected_lint_issues = {
            "fields": [],
            "dockerfile": [],
            "hadolint": ["-:1 DL3006 warning: Always tag the version of an image explicitly"],
            "files": [],
        }
        self.assertDictEqual(expected_lint_issues, e.exception.issues)

    @mock.patch("ctfcli.core.challenge.subprocess.run")
    @mock.patch("ctfcli.core.challenge.click.secho")
    def test_allows_for_skipping_hadolint(self, mock_secho: MagicMock, mock_run: MagicMock, *args, **kwargs):
        challenge = Challenge(self.dockerfile_challenge)
        result = challenge.lint(skip_hadolint=True)

        mock_secho.assert_called_once_with("Skipping Hadolint", fg="yellow")
        mock_run.assert_not_called()
        self.assertTrue(result)

    @mock.patch("ctfcli.core.challenge.click.secho")
    def test_validates_files_exist(self, *args, **kwargs):
        challenge = Challenge(self.minimal_challenge, {"files": ["files/nonexistent.pdf"]})

        with self.assertRaises(LintException) as e:
            challenge.lint(skip_hadolint=True)

        expected_file_path = (challenge.challenge_directory / "files" / "nonexistent.pdf").absolute()
        expected_lint_issues = {
            "fields": [],
            "dockerfile": [],
            "hadolint": [],
            "files": [f"Challenge file 'files/nonexistent.pdf' specified, but not found at {expected_file_path}"],
        }

        self.assertDictEqual(expected_lint_issues, e.exception.issues)

    @mock.patch("ctfcli.core.challenge.click.secho")
    def test_looks_for_flags_in_dist_files(self, *args, **kwargs):
        challenge = Challenge(self.files_challenge, {"files": ["files/flag.txt"]})

        with self.assertRaises(LintException) as e:
            challenge.lint(skip_hadolint=True)

        expected_lint_issues = {
            "fields": [],
            "dockerfile": [],
            "hadolint": [],
            "files": ["Potential flag found in distributed file 'files/flag.txt':\n Whoopsie: flag{test-flag}"],
        }

        self.assertDictEqual(expected_lint_issues, e.exception.issues)
