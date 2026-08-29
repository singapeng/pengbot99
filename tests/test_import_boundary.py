# Python imports
import subprocess
import sys
import unittest

# Modules that compute the schedule, plus the assembly that turns the content
# dumps into managers. They are consumed by the Discord bot, but also by
# callers that have no Discord client and no business installing one.
SCHEDULE_MODULES = (
    "pengbot99.schedule",
    "pengbot99.miniprix",
    "pengbot99.events",
    "pengbot99.managers",
)


class TestDiscordImportBoundary(unittest.TestCase):
    """ The schedule modules must not pull in a Discord client library.

        py-cord is an optional dependency (the `bot` extra), so a consumer that
        installs pengbot99 on its own must still be able to import them. The
        assertion is on sys.modules rather than on what is installed, so that
        it stays meaningful in a development environment where py-cord is
        present.

        The check runs in a subprocess because sys.modules is process-wide: an
        in-process assertion would pass or fail depending on what the rest of
        the test session happened to import first.
    """

    def assert_import_is_discord_free(self, module_name):
        code = (
            "import importlib, sys\n"
            f"importlib.import_module({module_name!r})\n"
            "leaked = sorted(m for m in sys.modules if m.split('.')[0] == 'discord')\n"
            "print(','.join(leaked))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"importing {module_name} failed:\n{result.stderr}",
        )
        leaked = result.stdout.strip()
        self.assertEqual(
            leaked,
            "",
            f"{module_name} pulled a Discord library into sys.modules: {leaked}",
        )

    def test_schedule_modules_do_not_import_discord(self):
        for module_name in SCHEDULE_MODULES:
            with self.subTest(module=module_name):
                self.assert_import_is_discord_free(module_name)
