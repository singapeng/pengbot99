import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from pengbot99 import explain_cmd, formatters


class EventExplanationTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self.schedule = self.root / 'events.csv'
        self.holder = SimpleNamespace(name='default')
        self.env = {'CONFIG_PATH': str(self.root), 'EVENT_SCHEDULE_FILE': 'events.csv'}
        self.now = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)

    def explainer(self, auto_switch=True):
        return explain_cmd.Explainer(self.holder, self.env, auto_switch)

    def test_current_schedule_without_file_or_in_manual_mode(self):
        for auto_switch in (True, False):
            with self.subTest(auto_switch=auto_switch):
                explainer = self.explainer(auto_switch)
                self.assertIn('Current Schedule', explainer.topics)
                self.assertNotIn('Current And Upcoming Events', explainer.topics)
                self.assertIn('Grand Prix Weekend Event', explainer.explain_current_schedule(self.now))
                self.assertNotIn('until', explainer.explain_current_schedule(self.now))
                self.assertIn('not available', explainer.explain('Current And Upcoming Events'))
                self.schedule.write_text('2026-10-05,meteor\n')

    def test_explain_returns_both_event_options(self):
        self.schedule.write_text('2026-10-05,meteor\n')
        explainer = self.explainer()
        self.assertIn('currently active schedule is **Default Schedule',
                      explainer.explain('Current Schedule'))
        self.assertIn('**Currently Active**: Default Schedule',
                      explainer.explain('Current And Upcoming Events'))

    def test_current_uses_controller_even_if_file_disagrees(self):
        self.schedule.write_text('2026-10-01,meteor\n2026-10-05,default\n')
        self.holder.name = 'mini_world_tour'
        explainer = self.explainer()
        result = explainer.explain_current_schedule(self.now)
        self.assertIn("currently active schedule is **<:WTMini:1462608159913934881> "
                      "Mini World Tour Week**", result)
        self.assertIn('seven-race <:WTMini:1462608159913934881> World Tour', result)
        self.assertIn('<t:1791158400:F>', result)  # Oct 5 00:00 UTC
        self.assertEqual(explainer.explain_upcoming_events(self.now),
                         'Current and Expected Game Events:\n\n'
                         '**Currently Active**: <:WTMini:1462608159913934881> Mini World Tour Week\n'
                         '<t:1791158400:F>   Default Schedule: Grand Prix Weekend Event')

    def test_future_changes_sorted_and_same_profile_does_not_end_event(self):
        self.schedule.write_text('2026-10-07,machine_shuffle\n'
                                 '2026-10-05,default\n'
                                 '2026-10-03,queen\n'
                                 '2026-10-06,default\n')
        explainer = self.explainer()
        self.assertIn('Current And Upcoming Events', explainer.topics)
        self.assertIn('<t:1791331200:F>', explainer.explain_current_schedule(self.now))
        self.assertEqual(explainer.explain_upcoming_events(self.now),
                         'Current and Expected Game Events:\n\n'
                         '**Currently Active**: Default Schedule: Grand Prix Weekend Event\n'
                         '<t:1791331200:F>   <:MPMini:1195076264294363187> '
                         'Machine Shuffle Mini-Prix Weekend Event')

    def test_same_day_last_entry_wins_and_file_reloads(self):
        self.schedule.write_text('2026-10-05,queen\n2026-10-05,meteor\n')
        explainer = self.explainer()
        self.assertEqual(explainer.explain_upcoming_events(self.now),
                         'Current and Expected Game Events:\n\n'
                         '**Currently Active**: Default Schedule: Grand Prix Weekend Event\n'
                         '<t:1791158400:F>   Meteor Festival/Lightning Festival')
        self.schedule.write_text('2026-10-05,default\n')
        self.assertEqual(explainer.explain_upcoming_events(self.now),
                         'Current and Expected Game Events:\n\n'
                         '**Currently Active**: Default Schedule: Grand Prix Weekend Event')
        self.assertNotIn('until', explainer.explain_current_schedule(self.now))
        self.assertIn('No upcoming schedule change is listed.',
                      explainer.explain_current_schedule(self.now))

    def test_ten_event_lines_plus_header_and_last_profile_has_no_end(self):
        self.schedule.write_text(''.join(
            '2026-10-{0:02d},{1}\n'.format(day, 'meteor' if day % 2 else 'queen')
            for day in range(5, 20)))
        explainer = self.explainer()
        lines = explainer.explain_upcoming_events(self.now).splitlines()
        self.assertEqual(len(lines), 12)
        self.assertEqual(lines[1], '')
        self.assertIn('**Currently Active**', lines[2])
        self.holder.name = 'meteor'
        after_last = datetime(2026, 10, 20, tzinfo=timezone.utc)
        self.assertNotIn('until', explainer.explain_current_schedule(after_last))


    def test_league_profiles_have_distinct_emoji_and_prix_explanations(self):
        explainer = self.explainer(auto_switch=False)
        for name in ('knight', 'queen', 'king', 'ace'):
            with self.subTest(name=name):
                self.holder.name = name
                result = explainer.explain_current_schedule(self.now)
                icons = (formatters.event_custom_emoji[name] + ' ' +
                         formatters.event_custom_emoji['m' + name])
                self.assertIn(icons + ' ' + name.title() + ' Leagues Weekend Event', result)
                self.assertIn(formatters.format_event_name(name), result)
                self.assertIn(formatters.format_event_name('m' + name), result)
                self.assertIn(formatters.format_event_name('miniprix'), result)
                self.assertIn(formatters.format_event_name('classicprix'), result)

    def test_secret_and_world_tour_titles_in_schedule_summary(self):
        self.schedule.write_text('2026-10-05,secret\n2026-10-06,mini_world_tour\n')
        result = self.explainer().explain_upcoming_events(self.now)
        self.assertIn(formatters.event_custom_emoji['glitchgp'] +
                      ' Secret League Weekend Event', result)
        self.assertIn(formatters.event_custom_emoji['worldtour'] +
                      ' Mini World Tour Week', result)
        self.holder.name = 'secret'
        current = self.explainer(auto_switch=False).explain_current_schedule(self.now)
        self.assertIn(formatters.format_event_name('glitchgp'), current)
        self.assertIn(formatters.format_event_name('miniprix'), current)

    def test_miniprix_names_in_other_profile_explanations_have_emojis(self):
        explainer = self.explainer(auto_switch=False)
        for name in ('default', 'machine_shuffle', 'team_battle',
                     'mini_world_tour', 'festival_world_tour'):
            with self.subTest(name=name):
                self.holder.name = name
                result = explainer.explain_current_schedule(self.now)
                self.assertIn(formatters.format_event_name('miniprix'), result)
                self.assertIn(formatters.format_event_name('classicprix'), result)
        self.holder.name = 'machine_shuffle'
        self.assertIn('<:MPMini:1195076264294363187> Machine Shuffle Mini-Prix',
                      explainer.explain_current_schedule(self.now))


if __name__ == '__main__':
    unittest.main()
