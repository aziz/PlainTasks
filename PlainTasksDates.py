# coding: utf-8
import sublime, sublime_plugin
import json
from datetime import datetime
from datetime import timedelta

ST3 = int(sublime.version()) >= 3000
if ST3:
    from .PlainTasks import get_all_projects_and_separators
    MARK_SOON = sublime.DRAW_NO_FILL
    MARK_INVALID = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE
else:
    from PlainTasks import get_all_projects_and_separators
    MARK_SOON = MARK_INVALID = 0


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

        past_due, due_soon, misformatted = [], [], []

        date_format = self.view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        pattern = r'@due(\([^@\n]*\))'
        dates_strings = []
        dates_regions = self.view.find_all(pattern, 0, '\\1', dates_strings)
        if not dates_regions:
            return

        now = datetime.now()
        due_soon_threshold = self.view.settings().get('highlight_due_soon', 24) * 60 * 60

        for i, region in enumerate(dates_regions):
            if any(s in self.view.scope_name(region.a) for s in ('completed', 'cancelled')):
                continue
            try:
                date = datetime.strptime(dates_strings[i], date_format)
            except:
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

        scope_past_due = self.view.settings().get('scope_past_due', 'string.other.tag.todo.critical')
        scope_due_soon = self.view.settings().get('scope_due_soon', 'string.other.tag.todo.high')
        scope_misformatted = self.view.settings().get('scope_misformatted', 'string.other.tag.todo.low')
        self.view.add_regions('past_due', past_due, scope_past_due, 'circle')
        self.view.add_regions('due_soon', due_soon, scope_due_soon, 'dot', MARK_SOON)
        self.view.add_regions('misformatted', misformatted, scope_misformatted, '', MARK_INVALID)


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


class CalculateTotalTimeForProject(PlainTasksEnabled):
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


class CalculateTimeForTask(PlainTasksEnabled):
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
