# coding: utf-8
import sublime, sublime_plugin
import json
import re
import locale
import calendar
import itertools
from datetime import datetime
from datetime import timedelta

NT = sublime.platform() == 'windows'
ST3 = int(sublime.version()) >= 3000
if ST3:
    from .APlainTasksCommon import PlainTasksBase, PlainTasksEnabled, PlainTasksFold
    MARK_SOON = sublime.DRAW_NO_FILL
    MARK_INVALID = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE
else:
    from APlainTasksCommon import PlainTasksBase, PlainTasksEnabled, PlainTasksFold
    MARK_SOON = MARK_INVALID = 0
    sublime_plugin.ViewEventListener = object


try:  # unavailable dependencies shall not break basic functionality
    from dateutil import parser as dateutil_parser
    from dateutil.relativedelta import relativedelta
except:
    dateutil_parser = None


if ST3:
    locale.setlocale(locale.LC_ALL, '')


def is_yearfirst(date_format):
    return date_format.strip('(  )').startswith(('%y', '%Y'))


def is_dayfirst(date_format):
    return date_format.strip('(  )').startswith(('%d'))


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
    except (ValueError, OverflowError) as e:
        return None, (e, year, month, day, hour, minute)
    else:
        return date, None


def increase_date(view, region, text, now, date_format):
    # relative from date of creation if any
    if '++' in text:
        line = view.line(region)
        line_content = view.substr(line)
        created = re.search(r'(?mxu)@created\(([\d\w,\.:\-\/ @]*)\)', line_content)
        if created:
            created_date, error = parse_date(created.group(1),
                                             date_format=date_format,
                                             yearfirst=is_yearfirst(date_format),
                                             dayfirst=is_dayfirst(date_format),
                                             default=now)
            if error:
                ln = (view.rowcol(line.a)[0] + 1)
                print(u'\nPlainTasks:\nError at line %d\n\t%s\ncaused by text:\n\t"%s"\n' % (ln, error, created.group(0)))
                sublime.status_message(u'@created date is invalid at line %d, see console for details' % ln)
            else:
                now = created_date

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
    except (ValueError, OverflowError) as e:
        error = e, amount, hour, minute
    return delta, error


def expand_short_date(view, start, end, now, date_format):
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
        date, error = parse_date(text,
                                 date_format,
                                 yearfirst=is_yearfirst(date_format),
                                 dayfirst=is_dayfirst(date_format),
                                 default=now)

    return date, error, sublime.Region(start, end + 1)


def parse_date(date_string, date_format='(%y-%m-%d %H:%M)', yearfirst=True, dayfirst=False, default=None):
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
    try:
        return datetime.strptime(date_string, date_format), None
    except ValueError as e:
        # print(e)
        pass
    bare_date_string = date_string.strip('( )')
    items = len(bare_date_string.split('-' if '-' in bare_date_string else '.'))
    try:
        if items < 2 and len(bare_date_string) < 3:
            # e.g. @due(1) is always first day of next month,
            # but dateutil consider it 1st day of current month
            raise Exception("Special case of short date: less than 2 numbers")
        if items < 3 and any(s in date_string for s in '-.'):
            # e.g. @due(2-1) is always Fabruary 1st of next year,
            # but dateutil consider it this year
            raise Exception("Special case of short date: less than 3 numbers")
        date = dateutil_parser.parse(bare_date_string,
                                     yearfirst=yearfirst,
                                     dayfirst=dayfirst,
                                     default=default)
        if NT and all((date.year < 1900, '%y' in date_format)):
            return None, ('format %y requires year >= 1900 on Windows', date.year, date.month, date.day, date.hour, date.minute)
    except Exception as e:
        # print(e)
        date, error = convert_date(bare_date_string, default)
    else:
        error = None
    return date, error


def format_delta(view, delta):
    delta -= timedelta(microseconds=delta.microseconds)
    if view.settings().get('decimal_minutes', False):
        days = delta.days
        delta = u'%s%s%s%s' % (days or '', ' day, ' if days == 1 else '', ' days, ' if days > 1 else '', '%.2f' % (delta.seconds / 3600.0) if delta.seconds else '')
    else:
        delta = str(delta)
    if delta[~7:] == ' 0:00:00' or delta == '0:00:00':  # strip meaningless time
        delta = delta[:~6]
    elif delta[~2:] == ':00':  # strip meaningless seconds
        delta = delta[:~2]
    return delta.strip(' ,')


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
            if ST3:
                self.view.settings().set('plain_tasks_remain_time_phantoms', [])
            return

        past_due, due_soon, misformatted, phantoms = self.group_due_tags(dates_strings, dates_regions)

        scope_past_due = self.view.settings().get('scope_past_due', 'string.other.tag.todo.critical')
        scope_due_soon = self.view.settings().get('scope_due_soon', 'string.other.tag.todo.high')
        scope_misformatted = self.view.settings().get('scope_misformatted', 'string.other.tag.todo.low')
        icon_past_due = self.view.settings().get('icon_past_due', 'circle')
        icon_due_soon = self.view.settings().get('icon_due_soon', 'dot')
        icon_misformatted = self.view.settings().get('icon_misformatted', '')
        self.view.add_regions('past_due', past_due, scope_past_due, icon_past_due)
        self.view.add_regions('due_soon', due_soon, scope_due_soon, icon_due_soon, MARK_SOON)
        self.view.add_regions('misformatted', misformatted, scope_misformatted, icon_misformatted, MARK_INVALID)

        if not ST3:
            return
        if self.view.settings().get('show_remain_due', False):
            self.view.settings().set('plain_tasks_remain_time_phantoms', phantoms)
        else:
            self.view.settings().set('plain_tasks_remain_time_phantoms', [])

    def group_due_tags(self, dates_strings, dates_regions):
        past_due, due_soon, misformatted, phantoms = [], [], [], []
        date_format = self.view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        yearfirst = is_yearfirst(date_format)
        now = datetime.now()
        default = now - timedelta(seconds=now.second, microseconds=now.microsecond)  # for short dates w/o time
        due_soon_threshold = self.view.settings().get('highlight_due_soon', 24) * 60 * 60

        for i, region in enumerate(dates_regions):
            if any(s in self.view.scope_name(region.a) for s in ('completed', 'cancelled')):
                continue
            text = dates_strings[i]
            if '+' in text:
                date, error = increase_date(self.view, region, text, default, date_format)
                # print(date, date_format)
            else:
                date, error = parse_date(text,
                                         date_format=date_format,
                                         yearfirst=yearfirst,
                                         dayfirst=is_dayfirst(date_format),
                                         default=default)
                # print(date, date_format, yearfirst)
            if error:
                # print(error)
                misformatted.append(region)
            else:
                if now >= date:
                    past_due.append(region)
                    phantoms.append((region.a, '-' + format_delta(self.view, default - date)))
                else:
                    phantoms.append((region.a, format_delta(self.view, date - default)))
                    if due_soon_threshold:
                        td = (date - now)
                        # timedelta.total_seconds() is not available in 2.6.x
                        time_left = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10.0**6
                        if time_left < due_soon_threshold:
                            due_soon.append(region)
        return past_due, due_soon, misformatted, phantoms


class PlainTasksHLDue(sublime_plugin.EventListener):
    def on_activated(self, view):
        if not view.score_selector(0, "text.todo") > 0:
            return
        view.run_command('plain_tasks_toggle_highlight_past_due')

    def on_post_save(self, view):
        self.on_activated(view)

    def on_load(self, view):
        self.on_activated(view)


class PlainTasksFoldToDueTags(PlainTasksFold):
    def run(self, edit):
        if not self.view.settings().get('highlight_past_due', True):
            return sublime.message_dialog('highlight_past_due setting must be true')
        self.view.run_command('plain_tasks_toggle_highlight_past_due')
        dues = sorted(self.view.line(r) for r in (self.view.get_regions('past_due') + self.view.get_regions('due_soon')))
        if not dues:
            return sublime.message_dialog('No overdue tasks.\nCongrats!')
        self.exec_folding(self.add_projects_and_notes(dues))


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
                               minutes=int(t['minutes']) or int(t['dminutes']) * 60,
                               seconds=int(t['seconds']))
        return total, eol


class PlainTasksCalculateTimeForTask(PlainTasksEnabled):
    def run(self, edit, started_matches, toggle_matches, now, eol, tag='lasted'):
        '''
        started_matches
            list of Unicode objects
        toggle_matches
            list of Unicode objects
        now
            Unicode object, moment of completion or cancellation of a task
        eol
            int as str (abs. point of end of task line without line break)
        tag
            Unicode object (lasted for complete, wasted for cancelled)
        '''
        if not started_matches:
            return

        date_format = self.view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        start = datetime.strptime(started_matches[0], date_format)
        end = datetime.strptime(now, date_format)

        toggle_times = [datetime.strptime(toggle, date_format) for toggle in toggle_matches]
        all_times = [start] + toggle_times + [end]
        pairs = zip(all_times[::2], all_times[1::2])
        deltas = [pair[1] - pair[0] for pair in pairs]

        delta = format_delta(self.view, sum(deltas, timedelta()))

        tag = ' @%s(%s)' % (tag, delta.rstrip(', ') if delta else ('a bit' if '%H' in date_format else 'less than day'))
        eol = int(eol)
        if self.view.substr(sublime.Region(eol - 2, eol)) == '  ':
            eol -= 2  # keep double whitespace at eol
        self.view.insert(edit, eol, tag)


class PlainTasksReCalculateTimeForTasks(PlainTasksEnabled):
    def run(self, edit):
        started = r'^\s*[^\b]*?\s*@started(\([\d\w,\.:\-\/ @]*\)).*$'
        toggle = r'@toggle(\([\d\w,\.:\-\/ @]*\))'
        calculated = r'([ \t]@[lw]asted\([\d\w,\.:\-\/ @]*\))'
        done = r'^\s*[^\b]*?\s*@(done|cancell?ed)[ \t]*(\([\d\w,\.:\-\/ @]*\)).*$'

        date_format = self.view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        default_now = datetime.now().strftime(date_format)

        regions = itertools.chain(*(reversed(self.view.lines(region)) for region in reversed(list(self.view.sel()))))
        for line in regions:
            current_scope = self.view.scope_name(line.a)
            if not any(s in current_scope for s in ('completed', 'cancelled')):
                continue

            line_contents = self.view.substr(line)

            done_match = re.match(done, line_contents, re.U)
            now = done_match.group(2) if done_match else default_now

            started_matches = re.findall(started, line_contents, re.U)
            toggle_matches = re.findall(toggle, line_contents, re.U)
            calc_matches = re.findall(calculated, line_contents, re.U)

            for match in calc_matches:
                line_contents = line_contents.replace(match, '')

            self.view.replace(edit, line, line_contents)
            self.view.run_command(
                'plain_tasks_calculate_time_for_task', {
                    'started_matches': started_matches,
                    'toggle_matches': toggle_matches,
                    'now': now,
                    'eol': line.begin() + len(line_contents),
                    'tag': 'lasted' if 'completed' in current_scope else 'wasted'}
            )


class PlainTaskInsertDate(PlainTasksBase):
    def runCommand(self, edit, region=None, date=None):
        if region:
            y, m, d, H, M = date
            region = sublime.Region(*region)
            self.view.replace(edit, region, datetime(y, m, d, H, M, 0).strftime(self.date_format) + ' ')
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(self.view.line(region).b))
            return

        for s in reversed(list(self.view.sel())):
            self.view.insert(edit, s.b, datetime.now().strftime(self.date_format))


class PlainTasksReplaceShortDate(PlainTasksBase):
    def runCommand(self, edit):
        s = self.view.sel()[0]
        date, error, region = expand_short_date(self.view, s.a, s.b, datetime.now(), self.date_format)

        if not date:
            sublime.error_message(
                'PlainTasks:\n\n'
                '{0}:\n days:\t{1}\n hours:\t{2}\n minutes:\t{3}\n'.format(*error) if len(error) == 4 else
                '{0}:\n year:\t{1}\n month:\t{2}\n day:\t{3}\n HH:\t{4}\n MM:\t{5}\n'.format(*error))
            return

        date = date.strftime(self.date_format)
        self.view.replace(edit, region, date)
        offset = region.a + len(date)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(offset, offset))


class PlainTasksViewEventListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return settings.get('syntax') in ('Packages/PlainTasks/PlainTasks.sublime-syntax', 'Packages/PlainTasks/PlainTasks.tmLanguage')


class PlainTasksPreviewShortDate(PlainTasksViewEventListener):
    def __init__(self, view):
        self.view = view
        self.phantoms = sublime.PhantomSet(view, 'plain_tasks_preview_short_date')

    def on_selection_modified_async(self):
        self.phantoms.update([])  # https://github.com/SublimeTextIssues/Core/issues/1497
        s = self.view.sel()[0]
        if not (s.empty() and 'meta.tag.todo' in self.view.scope_name(s.a)):
            return

        rgn = self.view.extract_scope(s.a)
        text = self.view.substr(rgn)
        match = re.match(r'@due\(([^@\n]*)\)[\s$]*', text)
        # print(s, rgn, text)

        if not match:
            return
        # print(match.group(1))
        preview_offset = self.view.settings().get('due_preview_offset', 0)
        remain_format = self.view.settings().get('due_remain_format', '{time} remaining')
        overdue_format = self.view.settings().get('due_overdue_format', '{time} overdue')


        date_format = self.view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        start = rgn.a + 5  # within parenthesis
        now = datetime.now().replace(second=0, microsecond=0)
        date, error, region = expand_short_date(self.view, start, start, now, date_format)

        upd = []
        if not error:
            if now >= date:
                delta = '-' + format_delta(self.view, now - date)
            else:
                delta = format_delta(self.view, date - now)
            content = (overdue_format if '-' in delta else remain_format).format(time=delta.lstrip('-') or 'a little bit')
            if content:
                if self.view.settings().get('show_remain_due', False):
                    # replace existing remain/overdue phantom
                    phantoms = self.view.settings().get('plain_tasks_remain_time_phantoms', [])
                    for index, (point, _) in enumerate(phantoms):
                        if point == region.a - 4:
                            phantoms[index] = [point, str(delta)]
                            self.view.settings().set('plain_tasks_remain_time_phantoms', phantoms)
                            break
                else:
                    upd.append(sublime.Phantom(
                        sublime.Region(region.a - 4),
                        content,
                        sublime.LAYOUT_BELOW))
            date = date.strftime(date_format).strip('()')
        if date == match.group(1).strip():
            self.phantoms.update(upd)
            return

        upd.append(sublime.Phantom(
            sublime.Region(region.b - preview_offset),
            date or (
            '{0}:<br> days:\t{1}<br> hours:\t{2}<br> minutes:\t{3}<br>'.format(*error) if len(error) == 4 else
            '{0}:<br> year:\t{1}<br> month:\t{2}<br> day:\t{3}<br> HH:\t{4}<br> MM:\t{5}<br>'.format(*error)),
            sublime.LAYOUT_INLINE))
        self.phantoms.update(upd)


class PlainTasksChooseDate(sublime_plugin.ViewEventListener):
    def __init__(self, view):
        self.view = view

    @classmethod
    def is_applicable(cls, settings):
        return settings.get('show_calendar_on_tags')

    def on_selection_modified_async(self):
        s = self.view.sel()[0]
        if not (s.empty() and any('meta.tag.todo ' in self.view.scope_name(n) for n in (s.a, s.a - 1))):
            return
        self.view.run_command('plain_tasks_calendar', {'point': s.a})


class PlainTasksCalendar(sublime_plugin.TextCommand):
    def is_visible(self):
        return ST3

    def run(self, edit, point=None):
        point = point or self.view.sel()[0].a
        self.region, tag = self.extract_tag(point)
        content = self.generate_calendar()
        self.view.show_popup(content, sublime.COOPERATE_WITH_AUTO_COMPLETE, self.region.a, 555, 555, self.action)

    def extract_tag(self, point):
        '''point is cursor
        Return tuple of two elements
        Region
            which will be replaced with chosen date, it may be parentheses belong to tag, or end of tag, or point
        Unicode
            tag under cursor (i.e. point)
        '''
        start = end = point
        tag_pattern = r'(?<=\s)(\@[^\(\) ,\.]+)([\w\d\.\(\)\-!? :\+]*)'
        line = self.view.line(point)
        matches = re.finditer(tag_pattern, self.view.substr(line))
        for match in matches:
            m_start = line.a + match.start(1)
            m_end   = line.a + match.end(2)
            if m_start <= point <= m_end:
                start = line.a + match.start(2)
                end   = m_end
                break
        else:
            match = None
        tag = match.group(0) if match else ''
        return sublime.Region(start, end), tag

    def generate_calendar(self, date=None):
        date = date or datetime.now()
        y, m, d, H, M = date.year, date.month, date.day, date.hour, date.minute

        content = ('<style> #today {{color: var(--background); background-color: var(--foreground)}}</style>'
                   '<br> <center><big>{prev_month} {next_month} {month}'
                   '    {prev_year} {next_year} {year}</big></center><br><br>'
                   '{table}<br> {time}<br><br><hr>'
                   '<br> Click day to insert date '
                   '<br> into view, click month or '
                   '<br> time to switch the picker <br><br>'
                   )

        locale.setlocale(locale.LC_ALL, '')  # to get native month name
        month = '<a href="month:{0}-{1}-{2}-{3}-{4}">{5}</a>'.format(y, m, d, H, M, date.strftime('%B'))
        prev_month = '<a href="prev_month:{0}-{1}-{2}-{3}-{4}">←</a>'.format(y, m, d, H, M)
        next_month = '<a href="next_month:{0}-{1}-{2}-{3}-{4}">→</a>'.format(y, m, d, H, M)
        prev_year = '<a href="prev_year:{0}-{1}-{2}-{3}-{4}">←</a>'.format(y, m, d, H, M)
        next_year = '<a href="next_year:{0}-{1}-{2}-{3}-{4}">→</a>'.format(y, m, d, H, M)
        year = '<a href="year:{0}-{1}-{2}-{3}-{4}">{0}</a>'.format(y, m, d, H, M)

        table = ''
        for week in calendar.Calendar().monthdayscalendar(y, m):
            row = ['']
            for day in week:
                link = '<a href="day:{0}-{1}-{2}-{3}-{4}"{5}>{2}</a>'.format(y, m, day, H, M, ' id="today"' if d == day else '')
                cell = ('  %s' % link if day < 10 else ' %s' % link) if day else '   '
                row.append(cell)
            table += ' '.join(row + ['<br><br>'])

        time = '<a href="time:{0}-{1}-{2}-{3}-{4}">{5}</a>'.format(y, m, d, H, M, date.strftime('%H:%M'))
        return content.format(
            prev_month=prev_month, next_month=next_month, month=month,
            prev_year=prev_year, next_year=next_year, year=year,
            time=time, table=table)

    def action(self, payload):
        msg, stamp = payload.split(':')

        def insert(stamp):
            self.view.hide_popup()
            y, m, d, H, M = (int(i) for i in stamp.split('-'))
            self.view.run_command('plain_task_insert_date', {'region': (self.region.a, self.region.b), 'date': (y, m, d, H, M)})
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(self.region.b + 1))

        def generate_months(stamp):
            y, m, d, H, M = (int(i) for i in stamp.split('-'))
            months = ['<br>{5}<a href="year:{0}-{1}-{2}-{3}-{4}">{0}</a><br><br>'.format(y, m, d, H, M, ' ' * 8)]
            for i in range(1, 13):
                months.append('{6}<a href="calendar:{0}-{1}-{2}-{3}-{4}">{5}</a> '.format(y, i, d, H, M, datetime(y, i, 1, H, M, 0).strftime('%b'), '•' if i == m else ' '))
                if i in (4, 8, 12):
                    months.append('<br><br>')
            self.view.update_popup(''.join(months))

        def generate_years(stamp):
            y, m, d, H, M = (int(i) for i in stamp.split('-'))
            years = ['<br>']
            for i in range(y - 6, y + 6):
                years.append('{5}<a href="month:{0}-{1}-{2}-{3}-{4}">{0}</a> '.format(i, m, d, H, M, '•' if i == y else ' '))
                if i in (y - 3, y + 1, y + 5):
                    years.append('<br><br>')
            self.view.update_popup(''.join(years))

        def generate_time(stamp):
            y, m, d, H, M = (int(i) for i in stamp.split('-'))
            hours = ['<br> Hours:<br><br>']
            for i in range(24):
                hours.append('{6}{5}<a href="time:{0}-{1}-{2}-{3}-{4}">{3}</a> '.format(y, m, d, i, M, '•' if i == H else ' ', ' ' if i < 10 else ''))
                if i in (7, 15, 23):
                    hours.append('<br><br>')
            minutes = ['<br> Minutes:<br><br>']
            for i in range(60):
                minutes.append('{6}{5}<a href="time:{0}-{1}-{2}-{3}-{4}">{4}</a> '.format(y, m, d, H, i, '•' if i == M else ' ', ' ' if i < 10 else ''))
                if i in (9, 19, 29, 39, 49, 59):
                    minutes.append('<br><br>')
            confirm = ['<br> <a href="calendar:{0}-{1}-{2}-{3}-{4}">Confirm: {5}</a> <br><br>'.format(y, m, d, H, M, datetime(y, m, d, H, M, 0).strftime('%H:%M'))]
            self.view.update_popup(''.join(hours + minutes + confirm))

        def calendar(stamp):
            y, m, d, H, M = (int(i) for i in stamp.split('-'))
            if m == 2 and d > 28:
                d = 28
            elif d == 31 and m in (4, 6, 9, 11):
                d = 30
            self.view.update_popup(self.generate_calendar(date=datetime(y, m, d, H, M, 0)))

        def shift(stamp, month=0, year=0):
            y, m, d, H, M = (int(i) for i in stamp.split('-'))
            date = datetime(y, m, d, H, M, 0) + relativedelta(months=month, years=year)
            self.view.update_popup(self.generate_calendar(date))

        case = {
            'day': insert,
            'month': generate_months,
            'year': generate_years,
            'time': generate_time,
            'calendar': calendar,
            'prev_month': lambda s=stamp: shift(s, month=-1),
            'next_month': lambda s=stamp: shift(s, month=1),
            'prev_year': lambda s=stamp: shift(s, year=-1),
            'next_year': lambda s=stamp: shift(s, year=1)
        }
        self.view.update_popup('Loading...')
        case[msg](stamp)


class PlainTasksRemain(PlainTasksViewEventListener):
    def __init__(self, view):
        self.view = view
        self.phantom_set = sublime.PhantomSet(view, 'plain_tasks_remain_time')
        self.view.settings().add_on_change('plain_tasks_remain_time_phantoms', self.check_setting)
        self.phantoms = self.view.settings().get('plain_tasks_remain_time_phantoms', [])

    def check_setting(self):
        '''add_on_change is issued on change of any setting in settings object'''
        new_value = self.view.settings().get('plain_tasks_remain_time_phantoms', [])
        if self.phantoms == new_value:
            return
        self.phantoms = new_value
        self.update()

    def update(self):
        self.phantoms = self.view.settings().get('plain_tasks_remain_time_phantoms', [])
        if not self.phantoms:
            self.phantom_set.update([])
            return
        remain_format = self.view.settings().get('due_remain_format', '{time} remaining')
        overdue_format = self.view.settings().get('due_overdue_format', '{time} overdue')

        upd = []
        for point, content in self.phantoms:
            upd.append(sublime.Phantom(
                sublime.Region(point),
                (overdue_format if '-' in content else remain_format).format(time=content.lstrip('-') or 'a little bit'),
                sublime.LAYOUT_BELOW))
        self.phantom_set.update(upd)


def plugin_unloaded():
    for window in sublime.windows():
        for view in window.views():
            view.settings().clear_on_change('plain_tasks_remain_time_phantoms')
