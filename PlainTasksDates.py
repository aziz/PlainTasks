# coding: utf-8
import sublime, sublime_plugin
from datetime import datetime, timedelta

ST3 = int(sublime.version()) >= 3000
if ST3:
    MARK_SOON = sublime.DRAW_NO_FILL
    MARK_INVALID = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE
else:
    MARK_SOON = MARK_INVALID = 0


class PlainTasksToggleHighlightPastDue(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.score_selector(0, "text.todo") > 0

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
