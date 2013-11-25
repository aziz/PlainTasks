#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sublime
import sublime_plugin
import webbrowser
from datetime import datetime
if int(sublime.version()) < 3000:
    import locale


class PlainTasksBase(sublime_plugin.TextCommand):
    def run(self, edit):
        self.taskpaper_compatible = self.view.settings().get('taskpaper_compatible')
        if self.taskpaper_compatible:
            self.open_tasks_bullet = self.done_tasks_bullet = self.canc_tasks_bullet = '-'
            self.before_date_space = ''
        else:
            self.open_tasks_bullet = self.view.settings().get('open_tasks_bullet')
            self.done_tasks_bullet = self.view.settings().get('done_tasks_bullet')
            self.canc_tasks_bullet = self.view.settings().get('cancelled_tasks_bullet')
            self.before_date_space = ' '
        self.before_tasks_bullet_spaces = ' ' * self.view.settings().get('before_tasks_bullet_margin')
        self.date_format = self.view.settings().get('date_format')
        if self.view.settings().get('done_tag') or self.taskpaper_compatible:
            self.done_tag = "@done"
            self.canc_tag = "@cancelled"
        else:
            self.done_tag = ""
            self.canc_tag = ""
        if int(sublime.version()) < 3000:
            self.sys_enc = locale.getpreferredencoding()
        self.project_postfix = self.view.settings().get('project_tag')
        self.archive_name = self.view.settings().get('archive_name')
        self.runCommand(edit)


class PlainTasksNewCommand(PlainTasksBase):
    def runCommand(self, edit):
        selections = list(self.view.sel()) # for ST3 support
        selections.reverse() # because with multiple selections regions would be messed up after first iteration
        for region in selections:
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            has_bullet = re.match('^(\s*)(' + re.escape(self.open_tasks_bullet) + '|' + re.escape(self.done_tasks_bullet) + '|' + re.escape(self.canc_tasks_bullet) + ')', self.view.substr(line))
            not_empty_line = re.match('^(\s*)(\S.+)$', self.view.substr(line))
            empty_line     = re.match('^(\s+)$', self.view.substr(line))
            current_scope  = self.view.scope_name(line.a)
            if has_bullet:
                grps = has_bullet.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.open_tasks_bullet + ' '
            elif 'header' in current_scope and not self.view.settings().get('header_to_task'):
                grps = not_empty_line.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.before_tasks_bullet_spaces + self.open_tasks_bullet + ' '
            elif 'separator' in current_scope:
                grps = not_empty_line.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.before_tasks_bullet_spaces + self.open_tasks_bullet + ' '
            elif not ('header' and 'separator') in current_scope or self.view.settings().get('header_to_task'):
                if not_empty_line:
                    grps = not_empty_line.groups()
                    line_contents = (grps[0] if len(grps[0]) > 0 else self.before_tasks_bullet_spaces) + self.open_tasks_bullet + ' ' + grps[1]
                elif empty_line: # only whitespaces
                    grps = empty_line.groups()
                    line_contents = grps[0] + self.open_tasks_bullet + ' '
                else: # completely empty, no whitespaces
                    line_contents = self.before_tasks_bullet_spaces + self.open_tasks_bullet + ' '
            else:
                print('oops, need to improve PlainTasksNewCommand')
            self.view.replace(edit, line, line_contents)

        # convert each selection to single cursor, ready to type
        new_selections = []
        for sel in list(self.view.sel()):
            if not sel.empty():
                new_selections.append(sublime.Region(sel.b, sel.b))
            else:
                new_selections.append(sel)
        self.view.sel().clear()
        for sel in new_selections:
            self.view.sel().add(sel)


class PlainTasksCompleteCommand(PlainTasksBase):
    def runCommand(self, edit):
        original = [r for r in self.view.sel()]
        try:
            done_line_end = ' %s%s%s' % (self.done_tag, self.before_date_space, datetime.now().strftime(self.date_format).decode(self.sys_enc))
        except:
            done_line_end = ' %s%s%s' % (self.done_tag, self.before_date_space, datetime.now().strftime(self.date_format))
        offset = len(done_line_end)
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            if self.taskpaper_compatible:
                rom = '^(\s*)-(\s*[^\b]*\s*)(?!\s@(done|cancelled)).*$'
                rdm = '^(\s*)-(\s*[^\b]*?\s*)(?=\s@done).*$'
                rcm = '^(\s*)-(\s*[^\b]*?\s*)(?=\s@cancelled).*$'
            else:
                rom = '^(\s*)' + re.escape(self.open_tasks_bullet) + '(\s*.*)$'
                rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '(\s*[^\b]*?\s*)(?=\s@done|@project|\s\(|$).*$'
                rcm = '^(\s*)' + re.escape(self.canc_tasks_bullet) + '(\s*[^\b]*?\s*)(?=\s@cancelled|@project|\s\(|$).*$'
            started = '^\s*[^\b]*?\s*@started(\([\d\w,\.:\-\/ @]*\)).*$'
            open_matches = re.match(rom, line_contents, re.U)
            done_matches = re.match(rdm, line_contents, re.U)
            canc_matches = re.match(rcm, line_contents, re.U)
            started_matches = re.match(started, line_contents, re.U)
            if open_matches and not (done_matches or canc_matches):
                grps = open_matches.groups()
                eol = self.view.insert(edit, line.end(), done_line_end)
                replacement = u'%s%s%s' % (grps[0], self.done_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
                if started_matches:
                    start = datetime.strptime(started_matches.group(1), self.date_format)
                    end = datetime.strptime(done_line_end.replace(' @done ', ''), self.date_format)
                    self.view.insert(edit, line.end() + eol, ' @lasted(%s)' % str(end - start))
            elif done_matches:
                grps = done_matches.groups()
                replacement = u'%s%s%s' % (grps[0], self.open_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
                offset = -offset
            elif canc_matches:
                grps = canc_matches.groups()
                self.view.insert(edit, line.end(), done_line_end)
                replacement = u'%s%s%s' % (grps[0], self.done_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
                offset = -offset
        self.view.sel().clear()
        for ind, pt in enumerate(original):
            ofs = ind * offset
            new_pt = sublime.Region(pt.a + ofs, pt.b + ofs)
            self.view.sel().add(new_pt)


class PlainTasksCancelCommand(PlainTasksBase):
    def runCommand(self, edit):
        original = [r for r in self.view.sel()]
        try:
            canc_line_end = ' %s%s%s' % (self.canc_tag,self.before_date_space, datetime.now().strftime(self.date_format).decode(self.sys_enc))
        except:
            canc_line_end = ' %s%s%s' % (self.canc_tag,self.before_date_space, datetime.now().strftime(self.date_format))
        offset = len(canc_line_end)
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            if self.taskpaper_compatible:
                rom = '^(\s*)-(\s*[^\b]*\s*)(?!\s@(done|cancelled)).*$'
                rdm = '^(\s*)-(\s*[^\b]*?\s*)(?=\s@done).*$'
                rcm = '^(\s*)-(\s*[^\b]*?\s*)(?=\s@cancelled).*$'
            else:
                rom = '^(\s*)' + re.escape(self.open_tasks_bullet) + '(\s*.*)$'
                rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '(\s*[^\b]*?\s*)(?=\s@done|@project|\s\(|$).*$'
                rcm = '^(\s*)' + re.escape(self.canc_tasks_bullet) + '(\s*[^\b]*?\s*)(?=\s@cancelled|@project|\s\(|$).*$'
            started = '^\s*[^\b]*?\s*@started(\([\d\w,\.:\-\/ @]*\)).*$'
            open_matches = re.match(rom, line_contents, re.U)
            done_matches = re.match(rdm, line_contents, re.U)
            canc_matches = re.match(rcm, line_contents, re.U)
            started_matches = re.match(started, line_contents, re.U)
            if open_matches and not (done_matches or canc_matches):
                grps = open_matches.groups()
                eol = self.view.insert(edit, line.end(), canc_line_end)
                replacement = u'%s%s%s' % (grps[0], self.canc_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
                if started_matches:
                    start = datetime.strptime(started_matches.group(1), self.date_format)
                    end = datetime.strptime(canc_line_end.replace(' @cancelled ', ''), self.date_format)
                    self.view.insert(edit, line.end() + eol, ' @wasted(%s)' % str(end - start))
            elif done_matches:
                pass
                # grps = done_matches.groups()
                # replacement = u'%s%s%s' % (grps[0], self.canc_tasks_bullet, grps[1].rstrip())
                # self.view.replace(edit, line, replacement)
                # offset = -offset
            elif canc_matches:
                grps = canc_matches.groups()
                replacement = u'%s%s%s' % (grps[0], self.open_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
                offset = -offset
        self.view.sel().clear()
        for ind, pt in enumerate(original):
            ofs = ind * offset
            new_pt = sublime.Region(pt.a + ofs, pt.b + ofs)
            self.view.sel().add(new_pt)


class PlainTasksArchiveCommand(PlainTasksBase):
    def runCommand(self, edit):
        if self.taskpaper_compatible:
            rdm = '^(\s*)-(\s*[^\n]*?\s*)(?=\s@done)[\(\)\d\w,\.:\-\/ @]*\s*[^\n]$'
            rcm = '^(\s*)-(\s*[^\n]*?\s*)(?=\s@cancelled)[\(\)\d\w,\.:\-\/ @]*\s*[^\n]$'
        else:
            rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '\s+.*$'
            rcm = '^(\s*)' + re.escape(self.canc_tasks_bullet) + '\s+.*$'

        # finding archive section
        archive_pos = self.view.find(self.archive_name, 0, sublime.LITERAL)

        done_tasks = []
        done_task = self.view.find(rdm, 0)
        # print(done_task)
        while done_task and (not archive_pos or done_task < archive_pos):
            done_tasks.append(done_task)
            self.get_task_note(done_task, done_tasks)
            done_task = self.view.find(rdm, done_task.end() + 1)

        canc_tasks = []
        canc_task = self.view.find(rcm, 0)
        # print(canc_task)
        while canc_task and (not archive_pos or canc_task < archive_pos):
            canc_tasks.append(canc_task)
            self.get_task_note(canc_task, canc_tasks)
            canc_task = self.view.find(rcm, canc_task.end() + 1)

        all_tasks = done_tasks + canc_tasks
        all_tasks.sort()

        if all_tasks:
            if archive_pos:
                line = self.view.full_line(archive_pos).end()
            else:
                create_archive = u'\n\n＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿\n' + self.archive_name + '\n'
                self.view.insert(edit, self.view.size(), create_archive)
                line = self.view.size()

            projects = self.view.find_all('^\s*(\w+.+:\s*(\@[^\s]+(\(.*?\))?\s*)*$\n?)|^\s*---.{3,5}---+$', 0)

            # adding tasks to archive section
            for task in all_tasks:
                if self.taskpaper_compatible:
                    match_task = re.match('^\s*(-)(\s*[^\n]*?)', self.view.substr(task), re.U)
                else:
                    match_task = re.match('^\s*(' + re.escape(self.done_tasks_bullet) + '|' + re.escape(self.canc_tasks_bullet) + ')(\s+.*$)', self.view.substr(task), re.U)
                if match_task:
                    pr = self.get_task_project(task, projects)
                    if self.project_postfix:
                        eol = (self.before_tasks_bullet_spaces + self.view.substr(task).lstrip() +
                               (' @project(' if pr else '') + pr + (')' if pr else '') +
                               '\n')
                    else:
                        eol = (self.before_tasks_bullet_spaces +
                               match_task.group(1) + # bullet
                               (' ' if pr else '') + pr + (':' if pr else '') +
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

        prog = re.compile('^\n*(\s*)(.+):\s*(\@[^\s]+(\(.*?\))?\s*)*')
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
            tasks.append(self.view.line(note_line))
            note_line = self.view.line(note_line).end() + 1


class PlainTasksNewTaskDocCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.set_syntax_file('Packages/PlainTasks/PlainTasks.tmLanguage')


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
    LINK_PATTERN = re.compile(r'\.[\\/](?P<fn>[^\\/:*?"<>|]+[\\/]?)+[\\/]?(>(?P<sym>\w+))?(\:(?P<line>\d+))?(\:(?P<col>\d+))?(\"(?P<text>[^\n]*)\")?', re.I| re.U)

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
            for folder in win.folders():
                for root, dirnames, filenames in os.walk(folder):
                    filenames = [os.path.join(root, f) for f in filenames] + [v.file_name() for v in win.views() if v.file_name()]
                    for name in filenames:
                        if name.lower().endswith(fn.lower()):
                            self._current_res.append((name, line if line else 0, col if col else 0))
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
                sublime.set_timeout(lambda:self.find_text(self.opened_file, text, line), 50)

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
            tasks_prefixed_date.sort(reverse=self.view.settings().get('new_on_top'))
            eol = archive_pos.end()
            for a in tasks_prefixed_date:
                eol += self.view.insert(edit, eol, '\n' + re.sub('^\([\d\w,\.:\-\/ ]*\)([^\b]*$)', '\\1', a))
        else:
            sublime.status_message("Nothing to sort")


class PlainTaskInsertDate(PlainTasksBase):
    def runCommand(self, edit):
        for s in reversed(list(self.view.sel())):
            self.view.insert(edit, s.b, datetime.now().strftime(self.date_format))
