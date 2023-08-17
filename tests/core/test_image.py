import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, call

from ctfcli.core.image import Image

BASE_DIR = Path(__file__).parent.parent


class TestImage(unittest.TestCase):
    def test_assigns_attributes(self):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)

        self.assertEqual(image.name, "test-challenge")
        self.assertEqual(image.build_path, build_path)
        self.assertFalse(image.built)

    def test_accepts_path_as_string_and_pathlike(self):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertEqual(image.build_path, build_path)

        build_path_string = str(build_path)
        image = Image("test-challenge", build_path_string)
        self.assertEqual(image.build_path, build_path)

    @mock.patch("ctfcli.core.image.subprocess.call", return_value=0)
    def test_build(self, mock_call: MagicMock):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        image_name = image.build()

        self.assertTrue(image.built)
        self.assertEqual(image_name, "test-challenge")
        mock_call.assert_called_once_with(["docker", "build", "-t", "test-challenge", "."], cwd=build_path.absolute())

    @mock.patch("ctfcli.core.image.subprocess.call", return_value=1)
    def test_build_returns_none_if_failed(self, mock_call: MagicMock):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        image_name = image.build()

        self.assertFalse(image.built)
        self.assertIsNone(image_name)
        mock_call.assert_called_once_with(["docker", "build", "-t", "test-challenge", "."], cwd=build_path.absolute())

    @mock.patch("ctfcli.core.image.subprocess.call", return_value=0)
    def test_push_built_image(self, mock_call: MagicMock):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        image_name = image.build()
        image_location = image.push("registry.ctfd.io/example-project/test-challenge")

        self.assertEqual("test-challenge", image_name)
        self.assertEqual("registry.ctfd.io/example-project/test-challenge", image_location)
        self.assertTrue(image.built)

        mock_call.assert_has_calls(
            [
                call(
                    [
                        "docker",
                        "tag",
                        "test-challenge",
                        "registry.ctfd.io/example-project/test-challenge",
                    ]
                ),
                call(
                    [
                        "docker",
                        "push",
                        "registry.ctfd.io/example-project/test-challenge",
                    ]
                ),
            ]
        )

    # mock successful build but failed push
    @mock.patch("ctfcli.core.image.subprocess.call", side_effect=[0, 1, 1])
    def test_push_returns_none_if_failed(self, mock_call: MagicMock):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        image_name = image.build()
        image_location = image.push("registry.ctfd.io/example-project/test-challenge")

        self.assertEqual("test-challenge", image_name)
        self.assertIsNone(image_location)
        self.assertTrue(image.built)

        mock_call.assert_has_calls(
            [
                call(
                    [
                        "docker",
                        "tag",
                        "test-challenge",
                        "registry.ctfd.io/example-project/test-challenge",
                    ]
                ),
                call(
                    [
                        "docker",
                        "push",
                        "registry.ctfd.io/example-project/test-challenge",
                    ]
                ),
            ]
        )

    @mock.patch("ctfcli.core.image.subprocess.call", return_value=0)
    def test_builds_image_before_push(self, mock_call: MagicMock):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        image_location = image.push("registry.ctfd.io/example-project/test-challenge")
        self.assertEqual("registry.ctfd.io/example-project/test-challenge", image_location)
        self.assertTrue(image.built)

        mock_call.assert_has_calls(
            [
                call(
                    ["docker", "build", "-t", "test-challenge", "."],
                    cwd=build_path.absolute(),
                ),
                call(
                    [
                        "docker",
                        "tag",
                        "test-challenge",
                        "registry.ctfd.io/example-project/test-challenge",
                    ]
                ),
                call(
                    [
                        "docker",
                        "push",
                        "registry.ctfd.io/example-project/test-challenge",
                    ]
                ),
            ]
        )

    @mock.patch("ctfcli.core.image.subprocess.call", return_value=0)
    def test_export_built_image(self, mock_call: MagicMock):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        image.build()

        mock_named_temporary_file = MagicMock()
        mock_named_temporary_file.name = "/tmp/test-challenge.docker.tar"

        with mock.patch(
            "ctfcli.core.image.tempfile.NamedTemporaryFile",
            return_value=mock_named_temporary_file,
        ):
            export_path = image.export()

        self.assertTrue(image.built)
        self.assertEqual(export_path, "/tmp/test-challenge.docker.tar")
        mock_call.assert_has_calls(
            [
                call(
                    [
                        "docker",
                        "save",
                        "--output",
                        "/tmp/test-challenge.docker.tar",
                        "test-challenge",
                    ]
                )
            ]
        )

    @mock.patch("ctfcli.core.image.subprocess.call", return_value=0)
    def test_builds_image_before_export(self, mock_call: MagicMock):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        mock_named_temporary_file = MagicMock()
        mock_named_temporary_file.name = "/tmp/test-challenge.docker.tar"

        with mock.patch(
            "ctfcli.core.image.tempfile.NamedTemporaryFile",
            return_value=mock_named_temporary_file,
        ):
            export_path = image.export()

        self.assertTrue(image.built)
        self.assertEqual(export_path, "/tmp/test-challenge.docker.tar")
        mock_call.assert_has_calls(
            [
                call(
                    ["docker", "build", "-t", "test-challenge", "."],
                    cwd=build_path.absolute(),
                ),
                call(
                    [
                        "docker",
                        "save",
                        "--output",
                        "/tmp/test-challenge.docker.tar",
                        "test-challenge",
                    ]
                ),
            ]
        )

    @mock.patch("ctfcli.core.image.subprocess.call")
    @mock.patch("ctfcli.core.image.subprocess.check_output", return_value='{"80/tcp":{}}')
    def test_get_exposed_port(self, mock_check_output: MagicMock, *args, **kwargs):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        exposed_port = image.get_exposed_port()
        self.assertEqual("80", exposed_port)
        mock_check_output.assert_has_calls(
            [
                call(
                    [
                        "docker",
                        "inspect",
                        "--format={{json .Config.ExposedPorts}}",
                        "test-challenge",
                    ]
                )
            ]
        )

    @mock.patch("ctfcli.core.image.subprocess.call")
    @mock.patch(
        "ctfcli.core.image.subprocess.check_output",
        return_value='{"80/tcp":{},"8000/tcp":{}}',
    )
    def test_get_exposed_port_returns_first_port_if_multiple_exposed(
        self, mock_check_output: MagicMock, *args, **kwargs
    ):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        exposed_port = image.get_exposed_port()
        self.assertEqual("80", exposed_port)
        mock_check_output.assert_has_calls(
            [
                call(
                    [
                        "docker",
                        "inspect",
                        "--format={{json .Config.ExposedPorts}}",
                        "test-challenge",
                    ]
                )
            ]
        )

    @mock.patch("ctfcli.core.image.subprocess.call")
    @mock.patch("ctfcli.core.image.subprocess.check_output", return_value="null")
    def test_get_exposed_port_returns_none_if_no_ports_exposed(self, mock_check_output: MagicMock, *args, **kwargs):
        build_path = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
        image = Image("test-challenge", build_path)
        self.assertFalse(image.built)

        exposed_port = image.get_exposed_port()
        self.assertIsNone(exposed_port)
        mock_check_output.assert_has_calls(
            [
                call(
                    [
                        "docker",
                        "inspect",
                        "--format={{json .Config.ExposedPorts}}",
                        "test-challenge",
                    ]
                )
            ]
        )
