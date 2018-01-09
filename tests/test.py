# coding: utf8

import sublime
import sys
from unittest import TestCase
from datetime import datetime, timedelta

ST3 = int(sublime.version()) >= 3000

if ST3:
    PlainTasksDates = sys.modules['PlainTasks.PlainTasksDates']
else:
    PlainTasksDates = sys.modules['PlainTasksDates']


class TestDatesFunctions(TestCase):

    def test_convert_date(self):
        default = datetime(2016, 12, 31, 23, 0, 0)
        cases = [
            # now
            ['', default, default],
            ['eh', default, default],
            # error
            ['-1', default, None],
            ['--1', default, None],
            ['99', default, None],
            ['2-29', default, None],
            # future
            ['1-1', default, datetime(2017, 1, 1, 23, 0, 0)],
            ['1 1:', default, datetime(2017, 1, 1, 1, 0, 0)],
            ['23', datetime(2016, 12, 1, 23, 0, 0), datetime(2016, 12, 23, 23, 0, 0)],
        ]
        for (string, now, result) in cases:
            date, error = PlainTasksDates.convert_date(string, now)
            self.assertEqual(date, result)

    def test_parse_date(self):
        default = datetime(2016, 12, 31, 23, 0, 0)
        default_format = '(%y-%m-%d %H:%M)'
        cases = [
            {'string': '', 'result': default, },
            {'string': 'yo', 'result': default, },
            {'string': '3:', 'result': default.replace(hour=3), },
            {'string': '3', 'result': datetime(2017, 1, 3, 23, 0, 0), },
            # error
            {'string': '11111', 'result': None, },
            {'string': '233', 'result': None, },
            # yearfirst
            {'string': '1.1.16', 'result': datetime(2001, 1, 16, 23, 0, 0), },
            # yearfirst not
            {'string': '1.1.16', 'result': datetime(2016, 1, 1, 23, 0, 0), 'date_format': '(%d-%m-%y %H:%M)', },
            # dayfirst
            {'string': '4-1-16', 'result': datetime(2016, 1, 4, 23, 0, 0), 'date_format': '(%d-%m-%y %H:%M)', },
            # dayfirst, but pair is m-d, because dateutil will set 2016, but we expect 2017 (future)
            {'string': '4-1', 'result': datetime(2017, 4, 1, 23, 0, 0), 'date_format': '(%d-%m-%y %H:%M)', },
            # named month
            {'string': '2003-Sep-25', 'result': datetime(2003, 9, 25, 23, 0, 0), 'date_format': '(%d-%m-%y %H:%M)', },
            # ancient
            {'string': '233', 'result': datetime(233, 12, 31, 23, 0, 0), 'date_format': '(%Y-%m-%d %H:%M)', },
        ]
        for c in cases:
            fmt = c.get('date_format', default_format)
            yearfirst = fmt.startswith(('(%y', '(%Y'))
            dayfirst = fmt.startswith('(%d')
            date, error = PlainTasksDates.parse_date(c['string'],
                                                     date_format=fmt,
                                                     yearfirst=yearfirst,
                                                     dayfirst=dayfirst,
                                                     default=c.get('default', default))
            self.assertEqual(date, c['result'])

    def test_increase_date(self):
        class View(object):
            def __init__(self, created=None):
                self.created = created

            def substr(self, *args):
                return self.created or ''

            def line(self, *args):
                class Obj(object): pass
                Obj.a = Obj.b = 0
                return Obj

            def rowcol(self, *args): return 0, 0

        region = None
        default = datetime(2016, 12, 31, 23, 0, 0)
        default_format = '(%y-%m-%d %H:%M)'

        cases = [
            {'string': '+', 'result': datetime(2017, 1, 1, 23, 0), },
            {'string': '+hey', 'result': datetime(2017, 1, 1, 23, 0), },
            {'string': '+33.', 'result': datetime(2017, 1, 2, 8, 0), },
            {'string': '+33.55', 'result': datetime(2017, 1, 2, 8, 55), },
            {'string': '+555', 'result': datetime(2018, 7, 9, 23, 0), },
            {'string': '++', 'result': datetime(2016, 12, 2, 23, 0), 'view': View(created='@created(16.12.1)')},
            {'string': '++4w', 'result': datetime(2016, 12, 29, 23, 0), 'view': View(created='@created(16.12.1)')},
        ]
        for c in cases:
            date, error = PlainTasksDates.increase_date(c.get('view', None), region,
                                                        c['string'],
                                                        c.get('default', default),
                                                        c.get('date_format', default_format))
            self.assertEqual(date, c['result'])

    def test_format_delta(self):
        class View(object):
            def __init__(self, decimal=False):
                self.decimal = decimal

            def settings(self):
                return {'decimal_minutes': self.decimal}

        cases = [
            {'delta': timedelta(hours=1), 'result': '1:00', },
            {'delta': timedelta(hours=1, minutes=8), 'result': '1.13', 'view': View(True)},
            {'delta': timedelta(hours=10), 'result': '10:00', },
            {'delta': timedelta(days=1), 'result': '1 day', },
            {'delta': timedelta(hours=94), 'result': '3 days, 22:00', },
        ]
        for c in cases:
            string = PlainTasksDates.format_delta(c.get('view', View()), c['delta'])
            self.assertEqual(string, c['result'])

    def test_is_yearfirst(self):
        cases = [
            ['(%y-%m-%d %H:%M)', True],
            ['(%Y-%m-%d %H:%M)', True],
            ['(%d-%m-%y %H:%M)', False],
            ['(%b %d %Y %H:%M)', False],
            ['( %y-%m-%d %H:%M )', True],
            ['( %d.%m.%y %H:%M )', False],
        ]
        for (date_format, result) in cases:
            yf = PlainTasksDates.is_yearfirst(date_format)
            self.assertEqual(yf, result)

    def test_is_dayfirst(self):
        cases = [
            ['(%y-%m-%d %H:%M)', False],
            ['(%Y-%m-%d %H:%M)', False],
            ['(%d-%m-%y %H:%M)', True],
            ['(%b %d %Y %H:%M)', False],
            ['( %y-%m-%d %H:%M )', False],
            ['( %d.%m.%y %H:%M )', True],
        ]
        for (date_format, result) in cases:
            df = PlainTasksDates.is_dayfirst(date_format)
            self.assertEqual(df, result)
