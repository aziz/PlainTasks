#!/usr/bin/python
# -*- coding: utf-8 -*-

import os,io
import re
import sublime
import sublime_plugin
import webbrowser
import itertools
from datetime import datetime
from datetime import timedelta
if int(sublime.version()) < 3000:
    import locale


class PlainTasksBase(sublime_plugin.TextCommand):
    def run(self, edit):
        self.taskpaper_compatible = self.view.settings().get('taskpaper_compatible', False)
        if self.taskpaper_compatible:
            self.open_tasks_bullet = self.done_tasks_bullet = self.canc_tasks_bullet = '-'
            self.before_date_space = ''
        else:
            self.open_tasks_bullet = self.view.settings().get('open_tasks_bullet', u'☐')
            self.done_tasks_bullet = self.view.settings().get('done_tasks_bullet', u'✔')
            self.canc_tasks_bullet = self.view.settings().get('cancelled_tasks_bullet', u'✘')
            self.before_date_space = ' '
        translate_tabs_to_spaces = self.view.settings().get('translate_tabs_to_spaces', False)
        self.before_tasks_bullet_spaces = ' ' * self.view.settings().get('before_tasks_bullet_margin', 1) if not self.taskpaper_compatible and translate_tabs_to_spaces else '\t'
        self.tasks_bullet_space = self.view.settings().get('tasks_bullet_space', ' ' if self.taskpaper_compatible or translate_tabs_to_spaces else '\t')
        self.date_format = self.view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        if self.view.settings().get('done_tag', True) or self.taskpaper_compatible:
            self.done_tag = "@done"
            self.canc_tag = "@cancelled"
        else:
            self.done_tag = ""
            self.canc_tag = ""
        if int(sublime.version()) < 3000:
            self.sys_enc = locale.getpreferredencoding()
        self.project_postfix = self.view.settings().get('project_tag', True)
        self.archive_name = self.view.settings().get('archive_name', 'Archive:')
        self.archive_org_default_filemask = "{dir}{sep}{base}_archive{ext}"
        self.archive_org_filemask = self.view.settings().get(
                'archive_org_filemask', self.archive_org_default_filemask)
        self.runCommand(edit)


class PlainTasksNewCommand(PlainTasksBase):
    def runCommand(self, edit):
        # list for ST3 support;
        # reversed because with multiple selections regions would be messed up after first iteration
        regions = itertools.chain(*(reversed(self.view.lines(region)) for region in reversed(list(self.view.sel()))))
        header_to_task = self.view.settings().get('header_to_task', False)
        for line in regions:
            line_contents  = self.view.substr(line).rstrip()
            not_empty_line = re.match('^(\s*)(\S.+)$', self.view.substr(line))
            empty_line     = re.match('^(\s+)$', self.view.substr(line))
            current_scope  = self.view.scope_name(line.a)
            if 'item' in current_scope:
                grps = not_empty_line.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.open_tasks_bullet + self.tasks_bullet_space
            elif 'header' in current_scope and line_contents and not header_to_task:
                grps = not_empty_line.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.before_tasks_bullet_spaces + self.open_tasks_bullet + self.tasks_bullet_space
            elif 'separator' in current_scope:
                grps = not_empty_line.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.before_tasks_bullet_spaces + self.open_tasks_bullet + self.tasks_bullet_space
            elif not ('header' and 'separator') in current_scope or header_to_task:
                if not_empty_line:
                    grps = not_empty_line.groups()
                    line_contents = (grps[0] if len(grps[0]) > 0 else self.before_tasks_bullet_spaces) + self.open_tasks_bullet + self.tasks_bullet_space + grps[1]
                elif empty_line: # only whitespaces
                    grps = empty_line.groups()
                    line_contents = grps[0] + self.open_tasks_bullet + self.tasks_bullet_space
                else: # completely empty, no whitespaces
                    line_contents = self.before_tasks_bullet_spaces + self.open_tasks_bullet + self.tasks_bullet_space
            else:
                print('oops, need to improve PlainTasksNewCommand')
            self.view.replace(edit, line, line_contents)

        # convert each selection to single cursor, ready to type
        new_selections = []
        for sel in list(self.view.sel()):
            eol = self.view.line(sel).b
            new_selections.append(sublime.Region(eol, eol))
        self.view.sel().clear()
        for sel in new_selections:
            self.view.sel().add(sel)

        PlainTasksStatsStatus.set_stats(self.view)


class PlainTasksCompleteCommand(PlainTasksBase):
    def runCommand(self, edit):
        original = [r for r in self.view.sel()]
        try:
            done_line_end = ' %s%s%s' % (self.done_tag, self.before_date_space, datetime.now().strftime(self.date_format).decode(self.sys_enc))
        except:
            done_line_end = ' %s%s%s' % (self.done_tag, self.before_date_space, datetime.now().strftime(self.date_format))
        offset = len(done_line_end)
        rom = r'^(\s*)(\[\s\]|.)(\s*.*)$'
        rdm = r'''
            (?x)^(\s*)(\[x\]|.)                           # 0,1 indent & bullet
            (\s*[^\b]*?(?:[^\@]|(?<!\s)\@|\@(?=\s))*?\s*) #   2 very task
            (?=
              ((?:\s@done|@project|$).*)              # 3 ending either w/ done or w/o it & no date
              |                                       #   or
              (?:(\([^()]*\))\s*([^@]*|@project.*))?$ # 4 date & possible project tag after
            )
            '''  # rcm is the same, except bullet & ending
        rcm = r'^(\s*)(\[\-\]|.)(\s*[^\b]*?(?:[^\@]|(?<!\s)\@|\@(?=\s))*?\s*)(?=((?:\s@cancelled|@project|$).*)|(?:(\([^()]*\))\s*([^@]*|@project.*))?$)'
        started = r'^\s*[^\b]*?\s*@started(\([\d\w,\.:\-\/ @]*\)).*$'
        toggle = r'@toggle(\([\d\w,\.:\-\/ @]*\))'

        regions = itertools.chain(*(reversed(self.view.lines(region)) for region in reversed(list(self.view.sel()))))
        for line in regions:
            line_contents = self.view.substr(line)
            open_matches = re.match(rom, line_contents, re.U)
            done_matches = re.match(rdm, line_contents, re.U)
            canc_matches = re.match(rcm, line_contents, re.U)
            started_matches = re.match(started, line_contents, re.U)
            toggle_matches = re.findall(toggle, line_contents, re.U)

            current_scope = self.view.scope_name(line.a)
            if 'pending' in current_scope:
                grps = open_matches.groups()
                eol = self.view.insert(edit, line.end(), done_line_end)
                replacement = u'%s%s%s' % (grps[0], self.done_tasks_bullet, grps[2])
                self.view.replace(edit, line, replacement)
                if started_matches:
                    eol -= len(grps[1]) - len(self.done_tasks_bullet)
                    self.calc_end_start_time(self, edit, line, started_matches.group(1), toggle_matches, done_line_end, eol)
            elif 'header' in current_scope:
                eol = self.view.insert(edit, line.end(), done_line_end)
                if started_matches:
                    self.calc_end_start_time(self, edit, line, started_matches.group(1), toggle_matches, done_line_end, eol)
                indent = re.match('^(\s*)\S', line_contents, re.U)
                self.view.insert(edit, line.begin() + len(indent.group(1)), '%s ' % self.done_tasks_bullet)
            elif 'completed' in current_scope:
                grps = done_matches.groups()
                parentheses = self.check_parentheses(self.date_format, grps[4] or '')
                replacement = u'%s%s%s%s' % (grps[0], self.open_tasks_bullet, grps[2], parentheses)
                self.view.replace(edit, line, replacement)
                offset = -offset
            elif 'cancelled' in current_scope:
                grps = canc_matches.groups()
                self.view.insert(edit, line.end(), done_line_end)
                parentheses = self.check_parentheses(self.date_format, grps[4] or '')
                replacement = u'%s%s%s%s' % (grps[0], self.done_tasks_bullet, grps[2], parentheses)
                self.view.replace(edit, line, replacement)
                offset = -offset
        self.view.sel().clear()
        for ind, pt in enumerate(original):
            ofs = ind * offset
            new_pt = sublime.Region(pt.a + ofs, pt.b + ofs)
            self.view.sel().add(new_pt)

        PlainTasksStatsStatus.set_stats(self.view)

    @staticmethod
    def calc_end_start_time(self, edit, line, started_matches, toggle_matches, done_line_end, eol, tag='lasted'):
        start = datetime.strptime(started_matches, self.date_format)
        end = datetime.strptime(done_line_end.replace('@done', '').replace('@cancelled', '').strip(), self.date_format)

        toggle_times = [datetime.strptime(toggle,self.date_format) for toggle in toggle_matches]
        all_times = [start] + toggle_times + [end]
        pairs = zip(all_times[::2], all_times[1::2])
        deltas = [pair[1] - pair[0] for pair in pairs]

        delta = str(sum(deltas, timedelta()))
        if delta[~6:] == '0:00:00': # strip meaningless time
            delta = delta[:~6]
        elif delta[~2:] == ':00': # strip meaningless seconds
            delta = delta[:~2]

        tag = ' @%s(%s)' % (tag, delta.rstrip(', ') if delta else ('a bit' if '%H' in self.date_format else 'less than day'))
        self.view.insert(edit, line.end() + eol, tag)

    @staticmethod
    def check_parentheses(date_format, regex_group, is_date=False):
        if is_date:
            try:
                parentheses = regex_group if datetime.strptime(regex_group.strip(), date_format) else ''
            except ValueError:
                parentheses = ''
        else:
            try:
                parentheses = '' if datetime.strptime(regex_group.strip(), date_format) else regex_group
            except ValueError:
                parentheses = regex_group
        return parentheses


class PlainTasksCancelCommand(PlainTasksBase):
    def runCommand(self, edit):
        original = [r for r in self.view.sel()]
        try:
            canc_line_end = ' %s%s%s' % (self.canc_tag,self.before_date_space, datetime.now().strftime(self.date_format).decode(self.sys_enc))
        except:
            canc_line_end = ' %s%s%s' % (self.canc_tag,self.before_date_space, datetime.now().strftime(self.date_format))
        offset = len(canc_line_end)
        rom = r'^(\s*)(\[\s\]|.)(\s*.*)$'
        rdm = r'^(\s*)(\[x\]|.)(\s*[^\b]*?(?:[^\@]|(?<!\s)\@|\@(?=\s))*?\s*)(?=((?:\s@done|@project|$).*)|(?:(\([^()]*\))\s*([^@]*|@project.*))?$)'
        rcm = r'^(\s*)(\[\-\]|.)(\s*[^\b]*?(?:[^\@]|(?<!\s)\@|\@(?=\s))*?\s*)(?=((?:\s@cancelled|@project|$).*)|(?:(\([^()]*\))\s*([^@]*|@project.*))?$)'
        started = '^\s*[^\b]*?\s*@started(\([\d\w,\.:\-\/ @]*\)).*$'
        toggle = r'@toggle(\([\d\w,\.:\-\/ @]*\))'
        regions = itertools.chain(*(reversed(self.view.lines(region)) for region in reversed(list(self.view.sel()))))
        for line in regions:
            line_contents = self.view.substr(line)
            open_matches = re.match(rom, line_contents, re.U)
            done_matches = re.match(rdm, line_contents, re.U)
            canc_matches = re.match(rcm, line_contents, re.U)
            started_matches = re.match(started, line_contents, re.U)
            toggle_matches = re.findall(toggle,line_contents, re.U)

            current_scope = self.view.scope_name(line.a)
            if 'pending' in current_scope:
                grps = open_matches.groups()
                eol = self.view.insert(edit, line.end(), canc_line_end)
                replacement = u'%s%s%s' % (grps[0], self.canc_tasks_bullet, grps[2])
                self.view.replace(edit, line, replacement)
                if started_matches:
                    eol -= len(grps[1]) - len(self.canc_tasks_bullet)
                    PlainTasksCompleteCommand.calc_end_start_time(self, edit, line, started_matches.group(1), toggle_matches, canc_line_end, eol, tag='wasted')
            elif 'header' in current_scope:
                eol = self.view.insert(edit, line.end(), canc_line_end)
                if started_matches:
                    PlainTasksCompleteCommand.calc_end_start_time(self, edit, line, started_matches.group(1), toggle_matches, canc_line_end, eol, tag='wasted')
                indent = re.match('^(\s*)\S', line_contents, re.U)
                self.view.insert(edit, line.begin() + len(indent.group(1)), '%s ' % self.canc_tasks_bullet)
            elif 'completed' in current_scope:
                sublime.status_message('You cannot cancel what have been done, can you?')
                # grps = done_matches.groups()
                # parentheses = PlainTasksCompleteCommand.check_parentheses(self.date_format, grps[4] or '')
                # replacement = u'%s%s%s%s' % (grps[0], self.canc_tasks_bullet, grps[2], parentheses)
                # self.view.replace(edit, line, replacement)
                # offset = -offset
            elif 'cancelled' in current_scope:
                grps = canc_matches.groups()
                parentheses = PlainTasksCompleteCommand.check_parentheses(self.date_format, grps[4] or '')
                replacement = u'%s%s%s%s' % (grps[0], self.open_tasks_bullet, grps[2], parentheses)
                self.view.replace(edit, line, replacement)
                offset = -offset
        self.view.sel().clear()
        for ind, pt in enumerate(original):
            ofs = ind * offset
            new_pt = sublime.Region(pt.a + ofs, pt.b + ofs)
            self.view.sel().add(new_pt)

        PlainTasksStatsStatus.set_stats(self.view)


class PlainTasksArchiveCommand(PlainTasksBase):
    def runCommand(self, edit):
        rds = 'meta.item.todo.completed'
        rcs = 'meta.item.todo.cancelled'

        # finding archive section
        archive_pos = self.view.find(self.archive_name, 0, sublime.LITERAL)

        done_tasks = [i for i in self.view.find_by_selector(rds) if i.a < (archive_pos.a if archive_pos and archive_pos.a > 0  else self.view.size())]
        for i in done_tasks:
            self.get_task_note(i, done_tasks)

        canc_tasks = [i for i in self.view.find_by_selector(rcs) if i.a < (archive_pos.a if archive_pos and archive_pos.a > 0 else self.view.size())]
        for i in canc_tasks:
            self.get_task_note(i, canc_tasks)

        all_tasks = done_tasks + canc_tasks
        all_tasks.sort()

        if all_tasks:
            if archive_pos and archive_pos.a > 0:
                line = self.view.full_line(archive_pos).end()
            else:
                create_archive = u'\n\n＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿\n' + self.archive_name + '\n'
                self.view.insert(edit, self.view.size(), create_archive)
                line = self.view.size()

            # because tmLanguage need \n to make background full width of window
            # multiline headers are possible, thus we have to split em to be sure that
            # one header == one line
            projects = itertools.chain(*[self.view.lines(r) for r in self.view.find_by_selector('keyword.control.header.todo')])
            projects = sorted(list(projects) +
                              self.view.find_by_selector('meta.punctuation.separator.todo'))

            # adding tasks to archive section
            for task in all_tasks:
                match_task = re.match('^\s*(\[[x-]\]|.)(\s+.*$)', self.view.substr(task), re.U)
                current_scope = self.view.scope_name(task.a)
                if rds in current_scope or rcs in current_scope:
                    pr = self.get_task_project(task, projects)
                    if self.project_postfix:
                        eol = (self.before_tasks_bullet_spaces + self.view.substr(task).lstrip() +
                               (' @project(' if pr else '') + pr + (')' if pr else '') +
                               '\n')
                    else:
                        eol = (self.before_tasks_bullet_spaces +
                               match_task.group(1) + # bullet
                               (self.tasks_bullet_space if pr else '') + pr + (':' if pr else '') +
                               match_task.group(2) + # very task
                               '\n')
                else:
                    eol = self.before_tasks_bullet_spaces * 2 + self.view.substr(task).lstrip() + '\n'
                line += self.view.insert(edit, line, eol)

            # remove moved tasks (starting from the last one otherwise it screw up regions after the first delete)
            for task in reversed(all_tasks):
                self.view.erase(edit, self.view.full_line(task))
            self.view.run_command('plain_tasks_sort_by_date')

    def get_task_project(self, task, projects):
        index = -1
        for ind, pr in enumerate(projects):
            if task < pr:
                if ind > 0:
                    index = ind-1
                break
        #if there is no projects for task - return empty string
        if index == -1:
            return ''

        prog = re.compile('^\n*(\s*)(.+):(?=\s|$)\s*(\@[^\s]+(\(.*?\))?\s*)*')
        hierarhProject = ''

        if index >= 0:
            depth = re.match(r"\s*", self.view.substr(self.view.line(task))).group()
            while index >= 0:
                strProject = self.view.substr(projects[index])
                if prog.match(strProject):
                    spaces = prog.match(strProject).group(1)
                    if len(spaces) < len(depth):
                        hierarhProject = prog.match(strProject).group(2) + ((" / " + hierarhProject) if hierarhProject else '')
                        depth = spaces
                        if len(depth) == 0:
                            break
                else:
                    sep = re.compile('(^\s*)---.{3,5}---+$')
                    spaces = sep.match(strProject).group(1)
                    if len(spaces) < len(depth):
                        depth = spaces
                        if len(depth) == 0:
                            break
                index -= 1
        if not hierarhProject:
            return ''
        else:
            return hierarhProject

    def get_task_note(self, task, tasks):
        note_line = task.end() + 1
        while self.view.scope_name(note_line) == 'text.todo notes.todo ':
            note = self.view.line(note_line)
            if note not in tasks:
                tasks.append(note)
            note_line = self.view.line(note_line).end() + 1


class PlainTasksNewTaskDocCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.settings().add_on_change('color_scheme', lambda: self.set_proper_scheme(view))
        view.set_syntax_file('Packages/PlainTasks/PlainTasks.tmLanguage')

    def set_proper_scheme(self, view):
        # Since we cannot create file with syntax, there is moment when view has no settings,
        # but it is activated, so some plugins (e.g. Color Highlighter) set wrong color scheme
        view.settings().set('color_scheme', sublime.load_settings('PlainTasks.sublime-settings').get('color_scheme'))


class PlainTasksOpenUrlCommand(sublime_plugin.TextCommand):
    #It is horrible regex but it works perfectly
    URL_REGEX = r"""(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))
        +(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""

    def run(self, edit):
        s = self.view.sel()[0]
        # expand selection to possible URL
        start = s.a
        end = s.b

        # expand selection to nearest stopSymbols
        view_size = self.view.size()
        stopSymbols = ['\t', ' ', '\"', '\'', '>', '<', ',']
        # move the selection back to the start of the url
        while (start > 0
                and not self.view.substr(start - 1) in stopSymbols
                and self.view.classify(start) & sublime.CLASS_LINE_START == 0):
            start -= 1

        # move end of selection forward to the end of the url
        while (end < view_size
                and not self.view.substr(end) in stopSymbols
                and self.view.classify(end) & sublime.CLASS_LINE_END == 0):
            end += 1

        # grab the URL
        url = self.view.substr(sublime.Region(start, end))
        # optional select URL
        self.view.sel().add(sublime.Region(start, end))

        exp = re.search(self.URL_REGEX, url, re.X)
        if exp and exp.group(0):
            strUrl = exp.group(0)
            if strUrl.find("://") == -1:
                strUrl = "http://" + strUrl
            webbrowser.open_new_tab(strUrl)
        else:
            sublime.status_message("Looks like there is nothing to open")


class PlainTasksOpenLinkCommand(sublime_plugin.TextCommand):
    LINK_PATTERN = re.compile(
        r'''(?ixu)\.[\\/]
            (?P<fn>
            (?:[a-z]\:[\\/])?      # special case for Windows full path
            (?:[^\\/:">]+[\\/]?)+) # the very path (single filename/relative/full)
            (?=[\\/:">])           # stop matching path
                                   # options:
            (>(?P<sym>\w+))?(\:(?P<line>\d+))?(\:(?P<col>\d+))?(\"(?P<text>[^\n]*)\")?
        ''')

    def _format_res(self, res):
        return [res[0], "line: %d column: %d" % (int(res[1]), int(res[2]))]

    def _on_panel_selection(self, selection):
        if selection >= 0:
            res = self._current_res[selection]
            win = sublime.active_window()
            self.opened_file = win.open_file('%s:%s:%s' % res, sublime.ENCODED_POSITION)

    def show_panel_or_open(self, fn, sym, line, col, text):
        win = sublime.active_window()
        self._current_res = list()
        if sym:
            for name, _, pos in win.lookup_symbol_in_index(sym):
                if name.endswith(fn):
                    line, col = pos
                    self._current_res.append((name, line, col))
        else:
            fn = fn.replace('/', os.sep)
            all_folders = win.folders() + [os.path.dirname(v.file_name()) for v in win.views() if v.file_name()]
            for folder in set(all_folders):
                for root, _, filenames in os.walk(folder):
                    filenames = [os.path.join(root, f) for f in filenames]
                    for name in filenames:
                        if name.lower().endswith(fn.lower()):
                            self._current_res.append((name, line or 0, col or 0))
            if os.path.isfile(fn): # check for full path
                self._current_res.append((fn, line or 0, col or 0))
            self._current_res = list(set(self._current_res))
        if len(self._current_res) == 1:
            self._on_panel_selection(0)
        else:
            entries = [self._format_res(res) for res in self._current_res]
            win.show_quick_panel(entries, self._on_panel_selection)

    def run(self, edit):
        point = self.view.sel()[0].begin()
        line = self.view.substr(self.view.line(point))
        match = self.LINK_PATTERN.search(line)
        if match:
            fn, sym, line, col, text = match.group('fn', 'sym', 'line', 'col', 'text')
            self.show_panel_or_open(fn, sym, line, col, text)
            if text:
                sublime.set_timeout(lambda: self.find_text(self.opened_file, text, line), 300)

    def find_text(self, view, text, line):
        result = view.find(text, view.sel()[0].a if line else 0, sublime.LITERAL)
        view.sel().clear()
        view.sel().add(result.a)
        view.set_viewport_position(view.text_to_layout(view.size()), False)
        view.show_at_center(result)


class PlainTasksSortByDate(PlainTasksBase):
    def runCommand(self, edit):
        archive_pos = self.view.find(self.archive_name, 0, sublime.LITERAL)
        if archive_pos:
            have_date = '(^\s*[^\n]*?\s\@(?:done|cancelled)\s*(\([\d\w,\.:\-\/ ]*\))[^\n]*$)'
            tasks_prefixed_date = []
            tasks = self.view.find_all(have_date, archive_pos.b-1, "\\2\\1", tasks_prefixed_date)
            notes = []
            for ind, task in enumerate(tasks):
                note_line = task.end() + 1
                while self.view.scope_name(note_line) == 'text.todo notes.todo ':
                    note = self.view.line(note_line)
                    notes.append(note)
                    tasks_prefixed_date[ind] += '\n' + self.view.substr(note)
                    note_line = note.end() + 1
            to_remove = tasks+notes
            to_remove.sort()
            for i in reversed(to_remove):
                self.view.erase(edit, self.view.full_line(i))
            tasks_prefixed_date.sort(reverse=self.view.settings().get('new_on_top', True))
            eol = archive_pos.end()
            for a in tasks_prefixed_date:
                eol += self.view.insert(edit, eol, '\n' + re.sub('^\([\d\w,\.:\-\/ ]*\)([^\b]*$)', '\\1', a))
        else:
            sublime.status_message("Nothing to sort")


class PlainTaskInsertDate(PlainTasksBase):
    def runCommand(self, edit):
        for s in reversed(list(self.view.sel())):
            self.view.insert(edit, s.b, datetime.now().strftime(self.date_format))


class PlainTasksReplaceShortDate(PlainTasksBase):
    def runCommand(self, edit):
        self.date_format = self.date_format.strip('()')
        now = datetime.now()

        s = self.view.sel()[0]
        start, end = s.a, s.b
        while self.view.substr(start) != '(':
            start -= 1
        while self.view.substr(end) != ')':
            end += 1
        self.rgn = sublime.Region(start + 1, end)
        matchstr = self.view.substr(self.rgn)
        # print(matchstr)

        if '+' in matchstr:
            date = self.increase_date(matchstr, now)
        else:
            date = self.convert_date(matchstr, now)

        self.view.replace(edit, self.rgn, date)
        offset = start + len(date) + 2
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(offset, offset))

    def increase_date(self, matchstr, now):
        # relative from date of creation if any
        if '++' in matchstr:
            line_content = self.view.substr(self.view.line(self.rgn))
            created = re.search(r'(?mxu)@created\(([\d\w,\.:\-\/ @]*)\)', line_content)
            if created:
                try:
                    now = datetime.strptime(created.group(1), self.date_format)
                except ValueError as e:
                    return sublime.error_message('PlainTasks:\n\n FAILED date convertion: %s' % e)

        match_obj = re.search(r'''(?mxu)
            \s*\+\+?\s*
            (?P<number>\d*)\s*
            (?P<days>[Dd])?
            (?P<weeks>[Ww])?
            ''', matchstr)
        number = int(match_obj.group('number') or 0)
        days   = match_obj.group('days')
        weeks  = match_obj.group('weeks')
        if not number:
            # set 1 if number is ommited, i.e.
            #   @due(+) == @due(+1) == @due(+1d)
            #   @due(+w) == @due(+1w)
            number = 1
        delta = now + timedelta(days=(number*7 if weeks else number))
        return delta.strftime(self.date_format)

    def convert_date(self, matchstr, now):
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
                else: # @due(0) == today
                    day = now.day
        hour   = match_obj.group('hour')   or now.hour
        minute = match_obj.group('minute') or now.minute
        hour, minute = int(hour), int(minute)
        if year < 100:
            year += 2000

        # print(year, month, day, hour, minute)
        try:
            date = datetime(year, month, day, hour, minute, 0).strftime(self.date_format)
        except ValueError as e:
            return sublime.error_message('PlainTasks:\n\n'
                '%s:\n year:\t%d\n month:\t%d\n day:\t%d\n HH:\t%d\n MM:\t%d\n' %
                (e, year, month, day, hour, minute))
        else:
            return date


class PlainTasksConvertToHtml(PlainTasksBase):
    def is_enabled(self):
        return self.view.score_selector(0, "text.todo") > 0

    def runCommand(self, edit):
        import cgi
        all_lines_regions = self.view.split_by_newlines(sublime.Region(0, self.view.size()))
        html_doc = []
        patterns = {'HEADER'    : 'text.todo keyword.control.header.todo ',
                    'EMPTY'     : 'text.todo ',
                    'NOTE'      : 'text.todo notes.todo ',
                    'OPEN'      : 'text.todo meta.item.todo.pending ',
                    'DONE'      : 'text.todo meta.item.todo.completed ',
                    'CANCELLED' : 'text.todo meta.item.todo.cancelled ',
                    'SEPARATOR' : 'text.todo meta.punctuation.separator.todo ',
                    'ARCHIVE'   : 'text.todo meta.punctuation.archive.todo '
                    }
        for r in all_lines_regions:
            i = self.view.scope_name(r.a)

            if patterns['HEADER'] in i:
                ht = '<span class="header">%s</span>' % cgi.escape(self.view.substr(r))

            elif i == patterns['EMPTY']:
                # these are empty lines (i.e. linebreaks, but span can be {display:none})
                ht = '<span class="empty-line">%s</span>' % self.view.substr(r)

            elif patterns['NOTE'] in i:
                scopes = self.extracting_scopes(self, r, i)
                note = '<span class="note">'
                for s in scopes:
                    sn = self.view.scope_name(s.a)
                    if 'italic' in sn:
                        note += '<i>%s</i>' % cgi.escape(self.view.substr(s).strip('_*'))
                    elif 'bold' in sn:
                        note += '<b>%s</b>' % cgi.escape(self.view.substr(s).strip('_*'))
                    else:
                        note += cgi.escape(self.view.substr(s))
                ht = note + '</span>'

            elif patterns['OPEN'] in i:
                scopes = self.extracting_scopes(self, r)
                indent = self.view.substr(sublime.Region(r.a, scopes[0].a)) if r.a != scopes[0].a else ''
                pending = '<span class="open">%s' % indent
                for s in scopes:
                    sn = self.view.scope_name(s.a)
                    if 'bullet' in sn:
                        pending += '<span class="bullet-pending">%s</span>' % self.view.substr(s)
                    elif 'meta.tag' in sn:
                        pending += '<span class="tag">%s</span>' % cgi.escape(self.view.substr(s))
                    elif 'tag.todo.today' in sn:
                        pending += '<span class="tag-today">%s</span>' % self.view.substr(s)
                    else:
                        pending += cgi.escape(self.view.substr(s))
                ht = pending + '</span>'

            elif patterns['DONE'] in i:
                scopes = self.extracting_scopes(self, r)
                indent = self.view.substr(sublime.Region(r.a, scopes[0].a)) if r.a != scopes[0].a else ''
                done = '<span class="done">%s' % indent
                for s in scopes:
                    sn = self.view.scope_name(s.a)
                    if 'bullet' in sn:
                        done += '<span class="bullet-done">%s</span>' % self.view.substr(s)
                    elif 'tag.todo.completed' in sn:
                        done += '<span class="tag-done">%s</span>' % cgi.escape(self.view.substr(s))
                    else:
                        done += cgi.escape(self.view.substr(s))
                ht = done + '</span>'

            elif patterns['CANCELLED'] in i:
                scopes = self.extracting_scopes(self, r)
                indent = self.view.substr(sublime.Region(r.a, scopes[0].a)) if r.a != scopes[0].a else ''
                cancelled = '<span class="cancelled">%s' % indent
                for s in scopes:
                    sn = self.view.scope_name(s.a)
                    if 'bullet' in sn:
                        cancelled += '<span class="bullet-cancelled">%s</span>' % self.view.substr(s)
                    elif 'tag.todo.cancelled' in sn:
                        cancelled += '<span class="tag-cancelled">%s</span>' % cgi.escape(self.view.substr(s))
                    else:
                        cancelled += cgi.escape(self.view.substr(s))
                ht = cancelled + '</span>'

            elif patterns['SEPARATOR'] in i:
                ht = '<span class="sep">%s</span>' % cgi.escape(self.view.substr(r))

            elif patterns['ARCHIVE'] in i:
                ht = '<span class="sep-archive">%s</span>' % cgi.escape(self.view.substr(r))

            else:
                sublime.error_message('Hey! you are not supposed to see this message.\n'
                                      'Please, report an issue in PlainTasks repository on GitHub.')
            html_doc.append(ht)

        # create file
        import tempfile
        tmp_html = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        with io.open('%s/PlainTasks/templates/template.html' % sublime.packages_path(), 'r', encoding='utf8') as template:
            title = os.path.basename(self.view.file_name()) if self.view.file_name() else 'Export'
            for line in template:
                line = line.replace('$title', title).replace('$content', '\n'.join(html_doc))
                tmp_html.write(line.encode('utf-8'))
        tmp_html.close()
        webbrowser.open_new_tab("file://%s" % tmp_html.name)

    def extracting_scopes(self, edit, region, scope_name=''):
        '''extract scope for each char in line wo dups, ineffective but it works?'''
        scopes = []
        for p in range(region.b-region.a):
            sr = self.view.extract_scope(region.a + p)
            # fix multi-line notes, because variable region is always a single line
            if 'note' in scope_name and sr.a < region.a or sr.b - 1 > region.b:
                if scopes and p == scopes[~0].b: # *text* inbetween *markups*
                    sr = sublime.Region(p, region.b + 1)
                else: # multi-line
                    sr = sublime.Region(region.a, region.b + 1)
            # main block, add unique entity to the list
            if sr not in scopes:
                scopes.append(sr)
            # fix intersecting regions, e.g. markup in notes
            if scopes and sr.a < scopes[~0].b and p - 1 == scopes[~0].b:
                scopes.append(sublime.Region(scopes[~0].b, sr.b))
        ln = len(scopes)
        if ('note' in scope_name and ln > 1) or ln > 2:
            # fix bullet
            if scopes[0].intersects(scopes[1]):
                scopes[0] = sublime.Region(scopes[0].a, scopes[1].a)
            # fix text after tag(s)
            if scopes[~0].b <= region.b or scopes[~0].a < region.a:
                scopes.append(sublime.Region(scopes[~0].b, region.b))
            for i, s in enumerate(scopes[:0:~0]):
                # fix overall intersections
                if s.intersects(scopes[~(i + 1)]):
                    if scopes[~(i + 1)].b < s.b:
                        scopes[~i] = sublime.Region(scopes[~(i + 1)].b, s.b)
                    else:
                        scopes[~(i + 1)] = sublime.Region(scopes[~(i + 1)].a, s.a)
        return scopes


class PlainTasksStatsStatus(sublime_plugin.EventListener):
    def on_activated(self, view):
        if not view.score_selector(0, "text.todo") > 0:
            return
        self.set_stats(view)

    @staticmethod
    def set_stats(view):
        view.set_status('PlainTasks', PlainTasksStatsStatus.get_stats(view))

    @staticmethod
    def get_stats(view):
        msgf = view.settings().get('stats_format', '$n/$a done ($percent%) $progress Last task @done $last')

        special_interest = re.findall(r'{{.*?}}', msgf)
        for i in special_interest:
            matches = view.find_all(i.strip('{}'))
            pend, done, canc = [], [], []
            for t in matches:
                # one task may contain same tag/word several times—we count amount of tasks, not tags
                t = view.line(t).a
                scope = view.scope_name(t)
                if 'pending' in scope and t not in pend:
                    pend.append(t)
                elif 'completed' in scope and t not in done:
                    done.append(t)
                elif 'cancelled' in scope and t not in canc:
                    canc.append(t)
            msgf = msgf.replace(i, '%d/%d/%d'%(len(pend), len(done), len(canc)))

        ignore_archive = view.settings().get('stats_ignore_archive', False)
        if ignore_archive:
            archive_pos = view.find(view.settings().get('archive_name', 'Archive:'), 0, sublime.LITERAL)
            pend = len([i for i in view.find_by_selector('meta.item.todo.pending') if i.a < (archive_pos.a if archive_pos and archive_pos.a > 0 else view.size())])
            done = len([i for i in view.find_by_selector('meta.item.todo.completed') if i.a < (archive_pos.a if archive_pos and archive_pos.a > 0 else view.size())])
            canc = len([i for i in view.find_by_selector('meta.item.todo.cancelled') if i.a < (archive_pos.a if archive_pos and archive_pos.a > 0 else view.size())])
        else:
            pend = len(view.find_by_selector('meta.item.todo.pending'))
            done = len(view.find_by_selector('meta.item.todo.completed'))
            canc = len(view.find_by_selector('meta.item.todo.cancelled'))
        allt = pend + done + canc
        percent  = ((done+canc)/float(allt))*100 if allt else 0
        factor   = int(round(percent/10)) if percent<90 else int(percent/10)

        barfull  = view.settings().get('bar_full', u'■')
        barempty = view.settings().get('bar_empty', u'☐')
        progress = '%s%s' % (barfull*factor, barempty*(10-factor)) if factor else ''

        tasks_dates = []
        view.find_all('(^\s*[^\n]*?\s\@(?:done)\s*(\([\d\w,\.:\-\/ ]*\))[^\n]*$)', 0, "\\2", tasks_dates)
        date_format = view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        tasks_dates = [PlainTasksCompleteCommand.check_parentheses(date_format, t, is_date=True) for t in tasks_dates]
        tasks_dates.sort(reverse=True)
        last = tasks_dates[0] if tasks_dates else '(UNKOWN)'

        msg = (msgf.replace('$o', str(pend))
                   .replace('$d', str(done))
                   .replace('$c', str(canc))
                   .replace('$n', str(done+canc))
                   .replace('$a', str(allt))
                   .replace('$percent', str(int(percent)))
                   .replace('$progress', progress)
                   .replace('$last', last)
                )
        return msg


class PlainTasksCopyStats(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.score_selector(0, "text.todo") > 0

    def run(self, edit):
        msg = self.view.get_status('PlainTasks')
        replacements = self.view.settings().get('replace_stats_chars', [])
        if replacements:
            for o, r in replacements:
                msg = msg.replace(o, r)

        sublime.set_clipboard(msg)

class PlainTasksArchiveOrgCommand(PlainTasksBase):
    def runCommand(self, edit):
        # Archive the subtree to our archive file, not just completed tasks.

        archive_filename = self.__createArchiveFilename()

        # Figure out our subtree
        start_line, end_line = self.__findCurrentSubtree()
        if (start_line < 0 or end_line < 0):
            return

        # Todo: Display it?
        #sublime.message_dialog("Debug:\n\nstart:{} end:{}\n".format(
        #    start_line, end_line))

        # Write our region to our section, or to our file
        success, region = self.__writeArchive(archive_filename, start_line, end_line)

        if success is True:
            self.view.erase(edit,region)

        return

    def __writeArchive(self, filename, start_line, end_line):
        # Build our region
        start_region=self.view.line(self.view.text_point(start_line,0))
        region=start_region.cover(self.view.line(
            self.view.text_point(end_line,0)))
        # Write it out!
        sublime.status_message('Archiving tree to {}'.format(filename))
        try:
            with io.open(filename, 'a', encoding='utf8') as fh:
                data = self.view.substr(region)
                fh.write("--- ✄ -----------------------\n")
                fh.write("Archived {}:\n".format(datetime.now().strftime(
                    self.date_format)))
                fh.write("{}\n".format(data))
            return True, region
        except Exception as e:
            sublime.error_message("Error:\n\nUnable to append to {}\n{}".format(
                filename, str(e)))
            return False, None

    def __createArchiveFilename(self):
        # Compute archive filename
        # Split filename int dir, base, and extension, then apply our mask
        path_base, extension=os.path.splitext(self.view.file_name())
        dir=os.path.dirname(path_base)
        base=os.path.basename(path_base)
        sep=os.sep
        # Now build our new filename
        try:
            archive_filename=self.archive_org_filemask.format(
                dir=dir, base=base, ext=extension, sep=sep)
        except:
            # Use our default mask
            archive_filename=self.archive_org_default_filemask.format(
                    dir=dir, base=base, ext=extension, sep=sep)

            # Display error
            sublime.error_message("Invalid filemask.  Using default: {}".format(
                self.archive_org_default_filemask))

        return archive_filename

    def __regionIndentLen(self, region):
        line_contents  = self.view.substr(region).rstrip()
        indent = re.match('^(\s*)\S', line_contents, re.U)
        if indent is None or indent.group(1) is None:
            return 0
        return len(indent.group(1))

    def __findCurrentSubtree(self):

        for region in self.view.sel():
            if not region.empty():
                sublime.error_message("Warning:  Regions not supported yet.  Ignoring selection")
            # either way, leave with only our starting region
            break

        #sublime.message_dialog("Region ({}/{}, {}/{}) xpos={} empty={} size={}".format(
        #    region.begin(), region.a, region.end(), region.b,
        #    region.xpos, region.empty(), region.size()))

        start_region=self.view.line(region)
        start_line, _ = self.view.rowcol(start_region.a)

        # Figure our our starting indent
        start_indent=self.__regionIndentLen(start_region)

        # Are we on a blank line?
        if (start_region.size() - start_indent) <=1:
            # we're empty
            sublime.error_message("Error:\n\n"
                    "Can not start archiving a tree on a blank line")
            return -1, -1, None

        # build regexp that will match our end of indent.
        if start_indent < 1:
            end_regexp="^\S"
        else:
            end_regexp="^[ \t]{{{},{}}}\S".format(0,start_indent)

        #end_regexp="^\s"
        #sublime.message_dialog("Debug\n\nRegexp: {} (indent={})".format(
        #    end_regexp, start_indent))
        end=self.view.find(end_regexp, start_region.b)
        if end.a == -1 and end.b == -1:
            end_point=self.view.size()
            end_line, _ = self.view.rowcol(end_point)
        else:
            end_point=self.view.line(end).b
            end_line, _ = self.view.rowcol(end.a)
            end_line -= 1

        return start_line, end_line

    def get_task_project(self, task, projects):
        index = -1
        for ind, pr in enumerate(projects):
            if task < pr:
                if ind > 0:
                    index = ind-1
                break
        #if there is no projects for task - return empty string
        if index == -1:
            return ''

        prog = re.compile('^\n*(\s*)(.+):(?=\s|$)\s*(\@[^\s]+(\(.*?\))?\s*)*')
        hierarhProject = ''

        if index >= 0:
            depth = re.match(r"\s*", self.view.substr(self.view.line(task))).group()
            while index >= 0:
                strProject = self.view.substr(projects[index])
                if prog.match(strProject):
                    spaces = prog.match(strProject).group(1)
                    if len(spaces) < len(depth):
                        hierarhProject = prog.match(strProject).group(2) + ((" / " + hierarhProject) if hierarhProject else '')
                        depth = spaces
                        if len(depth) == 0:
                            break
                else:
                    sep = re.compile('(^\s*)---.{3,5}---+$')
                    spaces = sep.match(strProject).group(1)
                    if len(spaces) < len(depth):
                        depth = spaces
                        if len(depth) == 0:
                            break
                index -= 1
        if not hierarhProject:
            return ''
        else:
            return hierarhProject

    def get_task_note(self, task, tasks):
        note_line = task.end() + 1
        while self.view.scope_name(note_line) == 'text.todo notes.todo ':
            note = self.view.line(note_line)
            if note not in tasks:
                tasks.append(note)
            note_line = self.view.line(note_line).end() + 1

