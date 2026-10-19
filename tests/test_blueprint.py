"""Exercise the actual blueprint templates and branches with synthetic calendars."""
from datetime import datetime, timedelta
from pathlib import Path
import re
import unittest
from zoneinfo import ZoneInfo

import yaml
from jinja2.nativetypes import NativeEnvironment


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor('!input', lambda loader, node: ('input', loader.construct_scalar(node)))
BLUEPRINT = yaml.load((Path(__file__).parents[1] / 'blueprints/automation/zenbi_subject_reminder.yaml').read_text(), Loader)
ZONE = ZoneInfo('Europe/Copenhagen')
A, B = 'calendar.synthetic_freja', 'calendar.synthetic_oscar'


def defaults(fields):
    out = {}
    for key, field in fields.items():
        if 'input' in field:
            out.update(defaults(field['input']))
        else:
            out[key] = field['default']
    return out


class Run:
    def __init__(self, inputs, events, unavailable=(), now=None):
        self.inputs = {**defaults(BLUEPRINT['blueprint']['input']), **inputs}
        self.events, self.unavailable = events, unavailable
        self.calls, self.queries = [], []
        self.now = now or datetime(2026, 10, 19, 18, tzinfo=ZONE)
        self.env = NativeEnvironment()
        self.env.filters['regex_replace'] = lambda value, pattern, repl: re.sub(pattern, repl, value)
        self.env.filters['as_local'] = lambda value: value.astimezone(ZONE)
        self.env.globals.update(
            timedelta=timedelta,
            today_at=lambda value: self.now.replace(hour=0,minute=0,second=0,microsecond=0),
            as_datetime=datetime.fromisoformat,
            state_attr=lambda entity, field: {A:'Zenbi Testskole Freja Kalender', B:'Zenbi Testskole Oscar Kalender'}.get(entity),
            device_id=lambda entity: 'school',
            device_attr=lambda dev, field: 'Zenbi Testskole' if field == 'name' else None,
        )
        self.vars = {}

    def render(self, value):
        if isinstance(value, tuple) and value[0] == 'input':
            return self.inputs[value[1]]
        if isinstance(value, str) and ('{{' in value or '{%' in value):
            return self.env.from_string(value).render(**self.vars)
        if isinstance(value, dict):
            return {key:self.render(item) for key,item in value.items()}
        if isinstance(value, list):
            return [self.render(item) for item in value]
        return value

    def variables(self, values):
        for key, value in values.items():
            self.vars[key] = self.render(value)

    def steps(self, actions):
        for action in actions:
            if 'variables' in action:
                self.variables(action['variables'])
            elif 'if' in action:
                if all(self.render(condition['value_template']) for condition in action['if']):
                    self.steps(action['then'])
            elif 'stop' in action:
                raise ValueError(action['stop'])
            elif 'repeat' in action:
                for item in self.render(action['repeat']['for_each']):
                    self.vars['repeat'] = {'item':item}
                    self.steps(action['repeat']['sequence'])
            elif action['action'] == 'calendar.get_events':
                entity = self.render(action['target']['entity_id'])
                self.queries.append((entity, self.render(action['data'])))
                if entity in self.unavailable:
                    self.assert_continue(action)
                else:
                    self.vars[action['response_variable']] = {entity:{'events':self.events.get(entity,[])}}
            elif action['action'] == 'zenbi.send_reminder':
                self.calls.append(self.render(action['data']))
            else:
                raise AssertionError('Unknown blueprint action')

    @staticmethod
    def assert_continue(action):
        assert action.get('continue_on_error') is True

    def execute(self):
        self.variables(BLUEPRINT['variables'])
        self.steps(BLUEPRINT['actions'])
        return self


def lesson(subject='2A idræt', time='08:00:00'):
    return {'summary':subject,'start':f'2026-10-20T{time}+02:00','end':'2026-10-20T10:00:00+02:00'}


class BlueprintTest(unittest.TestCase):
    def test_two_children_two_phones_and_duplicate_periods(self):
        run = Run({'child_calendars':[A,A,B], 'notification_devices':['phone-a','phone-b','phone-a']},
                  {A:[lesson(),lesson(time='08:45:00')],B:[lesson('0A IDRAET')]}).execute()
        self.assertEqual(len(run.calls), 2)
        self.assertEqual(run.calls[0]['device_ids'], ['phone-a','phone-b'])
        self.assertEqual(run.calls[0]['title'], 'Freja har idræt i morgen')
        self.assertEqual(run.calls[1]['title'], 'Oscar har idræt i morgen')
        self.assertIn('08:00', run.calls[0]['message'])
        self.assertEqual(len(run.queries), 2)

    def test_first_child_without_subject_does_not_stop_second(self):
        run = Run({'child_calendars':[A,B], 'notification_devices':['phone-a']},
                  {A:[lesson('matematik')],B:[lesson()]}).execute()
        self.assertEqual([c['title'] for c in run.calls], ['Oscar har idræt i morgen'])

    def test_failed_calendar_does_not_reuse_previous_child_events(self):
        run = Run({'child_calendars':[A,B], 'notification_devices':['phone-a']},
                  {A:[lesson()]}, unavailable=[B]).execute()
        self.assertEqual([c['title'] for c in run.calls], ['Freja har idræt i morgen'])

    def test_legacy_single_values_and_names_still_work(self):
        run = Run({'child_calendar':A,'notification_device':'phone-a','child_name':'Barnet'}, {A:[lesson()]}).execute()
        self.assertEqual(run.calls[0]['title'], 'Barnet har idræt i morgen')
        self.assertEqual(run.calls[0]['device_ids'], ['phone-a'])

    def test_new_choices_replace_legacy_recipients_and_calendars(self):
        run = Run({'child_calendars':[B], 'notification_devices':['phone-b'],
                   'child_calendar':A,'notification_device':'phone-a'}, {A:[lesson()],B:[lesson()]}).execute()
        self.assertEqual([entity for entity,_ in run.queries], [B])
        self.assertEqual(run.calls[0]['device_ids'], ['phone-b'])

    def test_missing_configuration_has_explanation(self):
        with self.assertRaisesRegex(ValueError, 'mindst én'):
            Run({}, {}).execute()

    def test_no_matching_subject_and_all_day(self):
        run = Run({'child_calendars':[A], 'notification_devices':['phone-a'], 'subject':'musik'}, {A:[lesson()]}).execute()
        self.assertEqual(run.calls, [])
        run = Run({'child_calendars':[A], 'notification_devices':['phone-a']},
                  {A:[{'summary':'Idræt','start':'2026-10-20','end':'2026-10-21'}]}).execute()
        self.assertNotIn('kl.', run.calls[0]['message'])

    def test_tomorrow_in_local_timezone_across_dst(self):
        run = Run({'child_calendars':[A], 'notification_devices':['phone-a']}, {},
                  now=datetime(2026,10,24,18,tzinfo=ZONE)).execute()
        dates = run.queries[0][1]
        start = datetime.fromisoformat(dates['start_date_time'])
        end = datetime.fromisoformat(dates['end_date_time'])
        self.assertEqual((end-start).total_seconds(), 25*3600)
