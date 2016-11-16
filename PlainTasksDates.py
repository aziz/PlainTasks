# coding: utf-8
import sublime, sublime_plugin
import json
import re
from datetime import datetime
from datetime import timedelta

ST3 = int(sublime.version()) >= 3000
if ST3:
    from .APlainTasksCommon import PlainTasksBase, get_all_projects_and_separators
    MARK_SOON = sublime.DRAW_NO_FILL
    MARK_INVALID = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE
else:
    from APlainTasksCommon import PlainTasksBase, get_all_projects_and_separators
    MARK_SOON = MARK_INVALID = 0
    sublime_plugin.ViewEventListener = object


try:  # unavailable dependencies shall not break basic functionality
    from dateutil import parser as dateutil_parser
except:
    dateutil_parser = None


def _convert_date(matchstr, now):
    match_obj = re.search(r'''(?mxu)
        (?:\s*
         (?P<yearORmonthORday>\d*(?!:))
         (?P<sep>[-\.])?
         (?P<monthORday>\d*)
         (?P=sep)?
         (?P<day>\d*)
         (?! \d*:)(?# e.g. '23:' == hour, but '1 23:' == day=1, hour=23)
        )?
        \s*
        (?:
         (?P<hour>\d*)
         :
         (?P<minute>\d*)
        )?''', matchstr)
    year  = now.year
    month = now.month
    day   = int(match_obj.group('day') or 0)
    # print(day)
    if day:
        year  = int(match_obj.group('yearORmonthORday'))
        month = int(match_obj.group('monthORday'))
    else:
        day = int(match_obj.group('monthORday') or 0)
        # print(day)
        if day:
            month = int(match_obj.group('yearORmonthORday'))
            if month < now.month:
                year += 1
        else:
            day = int(match_obj.group('yearORmonthORday') or 0)
            # print(day)
            if 0 < day <= now.day:
                # expect next month
                month += 1
                if month == 13:
                    year += 1
                    month = 1
            elif not day:  # @due(0) == today
                day = now.day
            # else would be day>now, i.e. future day in current month
    hour   = match_obj.group('hour')   or now.hour
    minute = match_obj.group('minute') or now.minute
    hour, minute = int(hour), int(minute)
    if year < 100:
        year += 2000

    # print(year, month, day, hour, minute)
    return year, month, day, hour, minute


def convert_date(matchstr, now):
    year = month = day = hour = minute = None
    try:
        year, month, day, hour, minute = _convert_date(matchstr, now)
        date = datetime(year, month, day, hour, minute, 0)
    except ValueError as e:
        return None, (e, year, month, day, hour, minute)
    else:
        return date, None


def increase_date(view, region, text, now, date_format):
    # relative from date of creation if any
    if '++' in text:
        line_content = view.substr(view.line(region))
        created = re.search(r'(?mxu)@created\(([\d\w,\.:\-\/ @]*)\)', line_content)
        if created:
            try:
                now = datetime.strptime(created.group(1), date_format)
            except ValueError as e:
                return sublime.error_message('PlainTasks:\n\n FAILED date convertion: %s' % e)

    match_obj = re.search(r'''(?mxu)
        \s*\+\+?\s*
        (?:
         (?P<number>\d*(?![:.]))\s*
         (?P<days>[Dd]?)
         (?P<weeks>[Ww]?)
         (?! \d*[:.])
        )?
        \s*
        (?:
         (?P<hour>\d*)
         [:.]
         (?P<minute>\d*)
        )?''', text)
    number = int(match_obj.group('number') or 0)
    days   = match_obj.group('days')
    weeks  = match_obj.group('weeks')
    hour   = int(match_obj.group('hour') or 0)
    minute = int(match_obj.group('minute') or 0)
    if not (number or hour or minute) or (not number and (days or weeks)):
        # set 1 if number is ommited, i.e.
        #   @due(+) == @due(+1) == @due(+1d)
        #   @due(+w) == @due(+1w)
        number = 1
    delta = error = None
    amount = number * 7 if weeks else number
    try:
        delta = now + timedelta(days=(amount), hours=hour, minutes=minute)
    except OverflowError as e:
        error = e, amount, hour, minute
    return delta, error


def expand_short_date(view, start, end, now, date_format):
    date_format = date_format.strip('()')

    while view.substr(start) != '(':
        start -= 1
    while view.substr(end) != ')':
        end += 1
    region = sublime.Region(start + 1, end)
    text = view.substr(region)
    # print(text)

    if '+' in text:
        date, error = increase_date(view, region, text, now, date_format)
    else:
        date, error = convert_date(text, now)

    return date, error, sublime.Region(start, end + 1)


def parse_date(date_string, date_format='(%y-%m-%d %H:%M)', yearfirst=True, default=None):
    '''
    Attempt to convert arbitrary string to datetime object
    date_string
        Unicode
    date_format
        Unicode
    yearfirst
        boolin
    default
        datetime object (now)
    '''
    bare_date_string = date_string.strip('( )')
    expanded_date, error = convert_date(bare_date_string, default)
    if dateutil_parser:
        try:
            date = dateutil_parser.parse(expanded_date.strftime(date_format).strip('( )') if expanded_date else bare_date_string,
                                     yearfirst=yearfirst,
                                     default=default)
        except Exception as e:
            error = e
    else:
        date = expanded_date
    return date, error


def format_delta(view, delta):
    if view.settings().get('decimal_minutes', False):
        days = delta.days
        delta = u'%s%s%s%.2f' % (days or '', ' day, ' if days == 1 else '', ' days, ' if days > 1 else '', delta.seconds/3600.0)
    else:
        delta = str(delta)
    if delta[~6:] == '0:00:00':  # strip meaningless time
        delta = delta[:~6]
    elif delta[~2:] == ':00':  # strip meaningless seconds
        delta = delta[:~2]
    return delta


class PlainTasksEnabled(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.score_selector(0, "text.todo") > 0


class PlainTasksToggleHighlightPastDue(PlainTasksEnabled):
    def run(self, edit):
        highlight_on = self.view.settings().get('highlight_past_due', True)
        self.view.erase_regions('past_due')
        self.view.erase_regions('due_soon')
        self.view.erase_regions('misformatted')
        if not highlight_on:
            return

        pattern = r'@due(\([^@\n]*\))'
        dates_strings = []
        dates_regions = self.view.find_all(pattern, 0, '\\1', dates_strings)
        if not dates_regions:
            return

        past_due, due_soon, misformatted = self.group_due_tags(dates_strings, dates_regions)

        scope_past_due = self.view.settings().get('scope_past_due', 'string.other.tag.todo.critical')
        scope_due_soon = self.view.settings().get('scope_due_soon', 'string.other.tag.todo.high')
        scope_misformatted = self.view.settings().get('scope_misformatted', 'string.other.tag.todo.low')
        self.view.add_regions('past_due', past_due, scope_past_due, 'circle')
        self.view.add_regions('due_soon', due_soon, scope_due_soon, 'dot', MARK_SOON)
        self.view.add_regions('misformatted', misformatted, scope_misformatted, '', MARK_INVALID)

    def group_due_tags(self, dates_strings, dates_regions):
        past_due, due_soon, misformatted = [], [], []
        date_format = self.view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        yearfirst = date_format.startswith(('(%y', '(%Y'))
        now = datetime.now()
        default = now - timedelta(seconds=1)  # for short dates w/o time
        due_soon_threshold = self.view.settings().get('highlight_due_soon', 24) * 60 * 60

        for i, region in enumerate(dates_regions):
            if any(s in self.view.scope_name(region.a) for s in ('completed', 'cancelled')):
                continue
            text = dates_strings[i]
            if '+' in text:
                date, error = increase_date(self.view, region, text, default, date_format)
            else:
                date, error = parse_date(text, date_format=date_format, yearfirst=yearfirst, default=default)
                # print(date, date_format, yearfirst)
            if error:
                # print(error)
                misformatted.append(region)
            else:
                if now >= date:
                    past_due.append(region)
                else:
                    if due_soon_threshold:
                        td = (date - now)
                        # timedelta.total_seconds() is not available in 2.6.x
                        time_left = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10.0**6
                        if time_left < due_soon_threshold:
                            due_soon.append(region)
        return past_due, due_soon, misformatted


class PlainTasksHLDue(sublime_plugin.EventListener):
    def on_activated(self, view):
        if not view.score_selector(0, "text.todo") > 0:
            return
        view.run_command('plain_tasks_toggle_highlight_past_due')

    def on_post_save(self, view):
        self.on_activated(view)

    def on_load(self, view):
        self.on_activated(view)


class PlainTasksFoldToDueTags(PlainTasksEnabled):
    def run(self, edit):
        if not self.view.settings().get('highlight_past_due', True):
            return sublime.message_dialog('highlight_past_due setting must be true')
        self.view.run_command('plain_tasks_toggle_highlight_past_due')
        dues = sorted(self.view.line(r) for r in (self.view.get_regions('past_due') + self.view.get_regions('due_soon')))
        if not dues:
            return sublime.message_dialog('No overdue tasks.\nCongrats!')

        dues = self.add_projects_and_notes(dues)

        self.view.unfold(sublime.Region(0, self.view.size()))
        for i, d in enumerate(dues):
            if not i:  # beginning of document
                self.folding(0, d.a - 1)
            else:  # all regions within
                self.folding(dues[i-1].b + 1, d.a - 1)
        if d:  # ending of document
            self.folding(d.b + 1, self.view.size())

    def folding(self, start, end):
        r = sublime.Region(start, end)
        if r.a < r.b:
            self.view.fold(r)

    def add_projects_and_notes(self, dues):
        '''Context is important, if due task has note and belongs to projects, make em visible'''
        def add_note(region):
            # refactor: method in ArchiveCommand
            next_line_begins = region.end() + 1
            while self.view.scope_name(next_line_begins) == 'text.todo notes.todo ':
                note = self.view.line(next_line_begins)
                if note not in dues:
                    dues.append(note)
                next_line_begins = self.view.line(next_line_begins).end() + 1

        projects = [r for r in get_all_projects_and_separators(self.view) if r.a < dues[~0].a]
        for d in reversed(dues):
            add_note(d)
            for p in reversed(projects):
                # refactor: different implementation in ArchiveCommand
                project_block = self.view.indented_region(p.end() + 1)
                due_block     = self.view.indented_region(d.begin())
                if all((p not in dues, project_block.contains(due_block))):
                    dues.append(p)
                    add_note(p)
                if self.view.indented_region(p.begin()).empty():
                    break
        dues.sort()
        return dues


class PlainTasksCalculateTotalTimeForProject(PlainTasksEnabled):
    def run(self, edit, start):
        line = self.view.line(int(start))
        total, eol = self.calc_total_time_for_project(line)
        if total:
            self.view.insert(edit, eol, ' @total(%s)' % format_delta(self.view, total).rstrip(', '))

    def calc_total_time_for_project(self, line):
        pattern = r'(?<=\s)@(lasted|wasted|total)\([ \t]*(?:(\d+)[ \t]*days?,?)?[ \t]*((?:(\d+)\:(\d+)\:?(\d+)?)|(?:(\d+)\.(\d+)))?[ \t]*\)'
        format = '{"days": "\\2", "hours": "\\4", "minutes": "\\5", "seconds": "\\6", "dhours": "\\7", "dminutes": "\\8"}'
        lasted_strings = []
        lasted_regions = self.view.find_all(pattern, 0, format, lasted_strings)
        if not lasted_regions:
            return 0, 0

        eol = line.end()
        project_block = self.view.indented_region(eol + 1)
        total = timedelta()
        for i, region in enumerate(lasted_regions):
            if not all((region > line, region.b <= project_block.b)):
                continue
            t = json.loads(lasted_strings[i].replace('""', '"0"'))
            total += timedelta(days=int(t['days']),
                               hours=int(t['hours']) or int(t['dhours']),
                               minutes=int(t['minutes']) or int(t['dminutes'])*60,
                               seconds=int(t['seconds']))
        return total, eol


class PlainTasksCalculateTimeForTask(PlainTasksEnabled):
    def run(self, edit, started_matches, toggle_matches, done_line_end, eol, tag='lasted'):
        if not started_matches:
            return

        date_format = self.view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        start = datetime.strptime(started_matches[0], date_format)
        end = datetime.strptime(done_line_end.replace('@done', '').replace('@cancelled', '').strip(), date_format)

        toggle_times = [datetime.strptime(toggle, date_format) for toggle in toggle_matches]
        all_times = [start] + toggle_times + [end]
        pairs = zip(all_times[::2], all_times[1::2])
        deltas = [pair[1] - pair[0] for pair in pairs]

        delta = format_delta(self.view, sum(deltas, timedelta()))

        tag = ' @%s(%s)' % (tag, delta.rstrip(', ') if delta else ('a bit' if '%H' in date_format else 'less than day'))
        self.view.insert(edit, int(eol), tag)


class PlainTaskInsertDate(PlainTasksBase):
    def runCommand(self, edit):
        for s in reversed(list(self.view.sel())):
            self.view.insert(edit, s.b, datetime.now().strftime(self.date_format))


class PlainTasksReplaceShortDate(PlainTasksBase):
    def runCommand(self, edit):
        s = self.view.sel()[0]
        date, error, region = expand_short_date(self.view, s.a, s.b, datetime.now(), self.date_format)

        if not date:
            sublime.error_message('PlainTasks:\n\n'
                '{0}:\n days:\t{1}\n hours:\t{2}\n minutes:\t{3}\n'.format(*error) if len(error) == 4 else
                '{0}:\n year:\t{1}\n month:\t{2}\n day:\t{3}\n HH:\t{4}\n MM:\t{5}\n'.format(*error))
            return

        date = date.strftime(self.date_format)
        self.view.replace(edit, region, date)
        offset = region.a + len(date) + 1
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(offset, offset))


class PlainTasksPreviewShortDate(sublime_plugin.ViewEventListener):
    def __init__(self, view):
        self.view = view
        self.phantoms = sublime.PhantomSet(view, 'plain_tasks_preview_short_date')

    @classmethod
    def is_applicable(cls, settings):
        return settings.get('syntax') == 'Packages/PlainTasks/PlainTasks.tmLanguage'

    def on_selection_modified_async(self):
        self.phantoms.update([])  # https://github.com/SublimeTextIssues/Core/issues/1497
        s = self.view.sel()[0]
        if not (s.empty() and 'meta.tag.todo' in self.view.scope_name(s.a)):
            return

        rgn = self.view.extract_scope(s.a)
        text = self.view.substr(rgn)
        match = re.match(r'@due(\([^@\n]*\))[\s$]*', text)
        # print(s, rgn, text)

        if not match:
            return
        # print(match.group(1))

        date_format = self.view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        date, error, region = expand_short_date(self.view, s.a, s.b, datetime.now(), date_format)

        if date == match.group(1).strip():
            return

        self.phantoms.update([sublime.Phantom(
            sublime.Region(region.b - 1),
            date.strftime(date_format).strip('()') if date else
            '{0}:<br> days:\t{1}<br> hours:\t{2}<br> minutes:\t{3}<br>'.format(*error) if len(error) == 4 else
            '{0}:<br> year:\t{1}<br> month:\t{2}<br> day:\t{3}<br> HH:\t{4}<br> MM:\t{5}<br>'.format(*error),
            sublime.LAYOUT_INLINE)])
