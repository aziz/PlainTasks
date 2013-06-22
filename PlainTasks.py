#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sublime
import sublime_plugin
import webbrowser
from datetime import datetime


class PlainTasksBase(sublime_plugin.TextCommand):
    def run(self, edit):
        self.open_tasks_bullet = self.view.settings().get('open_tasks_bullet')
        self.done_tasks_bullet = self.view.settings().get('done_tasks_bullet')
        self.canc_tasks_bullet = self.view.settings().get('canc_tasks_bullet')
        self.before_tasks_bullet_spaces = ' ' * self.view.settings().get('before_tasks_bullet_margin')
        self.date_format = self.view.settings().get('date_format')
        if self.view.settings().get('done_tag'):
            self.done_tag = "@done"
            self.canc_tag = "@cancelled"
        else:
            self.done_tag = ""
            self.canc_tag = ""
        self.runCommand(edit)


class PlainTasksNewCommand(PlainTasksBase):
    def runCommand(self, edit):
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            has_bullet = re.match('^(\s*)[' + re.escape(self.open_tasks_bullet) + re.escape(self.done_tasks_bullet) + re.escape(self.canc_tasks_bullet) + ']', self.view.substr(line))
            current_scope = self.view.scope_name(self.view.sel()[0].b)

            if has_bullet:
                grps = has_bullet.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.open_tasks_bullet + ' '
                self.view.replace(edit, line, line_contents)
            elif 'header' in current_scope:
                header = re.match('^(\s*)\S+', self.view.substr(line))
                if header:
                    grps = header.groups()
                    line_contents = self.view.substr(line) + '\n' + grps[0] + self.before_tasks_bullet_spaces + self.open_tasks_bullet + ' '
                else:
                    line_contents = self.before_tasks_bullet_spaces + self.open_tasks_bullet + ' '
                self.view.replace(edit, line, line_contents)
                end = self.view.sel()[0].b
                pt = sublime.Region(end, end)
                self.view.sel().clear()
                self.view.sel().add(pt)
            else:
                has_space = re.match('^(\s+)(.*)', self.view.substr(line))
                if has_space:
                    grps = has_space.groups()
                    spaces = grps[0]
                    line_contents = spaces + self.open_tasks_bullet + ' ' + grps[1]
                    self.view.replace(edit, line, line_contents)
                else:
                    line_contents = self.before_tasks_bullet_spaces + self.open_tasks_bullet + ' ' + self.view.substr(line)
                    self.view.replace(edit, line, line_contents)
                    end = self.view.sel()[0].b
                    pt = sublime.Region(end, end)
                    self.view.sel().clear()
                    self.view.sel().add(pt)


class PlainTasksCompleteCommand(PlainTasksBase):
    def runCommand(self, edit):
        original = [r for r in self.view.sel()]
        done_line_end = ' %s %s' % (self.done_tag, datetime.now().strftime(self.date_format))
        offset = len(done_line_end)
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            rom = '^(\s*)' + re.escape(self.open_tasks_bullet) + '\s*(.*)$'
            rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '\s*([^\b]*?)\s*(%s)+[\(\)\d\w,\.:\-\/ @]*\s*$' % self.done_tag
            rcm = '^(\s*)' + re.escape(self.canc_tasks_bullet) + '\s*([^\b]*?)\s*(%s)+[\(\)\d\w,\.:\-\/ @]*\s*$' % self.canc_tag
            open_matches = re.match(rom, line_contents, re.U)
            done_matches = re.match(rdm, line_contents, re.U)
            canc_matches = re.match(rcm, line_contents, re.U)
            if open_matches:
                grps = open_matches.groups()
                self.view.insert(edit, line.end(), done_line_end)
                replacement = u'%s%s %s' % (grps[0], self.done_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
            elif done_matches:
                grps = done_matches.groups()
                replacement = u'%s%s %s' % (grps[0], self.open_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
                offset = -offset
            elif canc_matches:
                grps = canc_matches.groups()
                self.view.insert(edit, line.end(), done_line_end)
                replacement = u'%s%s %s' % (grps[0], self.done_tasks_bullet, grps[1].rstrip())
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
        canc_line_end = ' %s %s' % (self.canc_tag, datetime.now().strftime(self.date_format))
        offset = len(canc_line_end)
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            rom = '^(\s*)' + re.escape(self.open_tasks_bullet) + '\s*(.*)$'
            rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '\s*([^\b]*?)\s*(%s)+[\(\)\d\w,\.:\-\/ @]*\s*$' % self.done_tag
            rcm = '^(\s*)' + re.escape(self.canc_tasks_bullet) + '\s*([^\b]*?)\s*(%s)+[\(\)\d\w,\.:\-\/ @]*\s*$' % self.canc_tag
            open_matches = re.match(rom, line_contents, re.U)
            done_matches = re.match(rdm, line_contents, re.U)
            canc_matches = re.match(rcm, line_contents, re.U)
            if open_matches:
                grps = open_matches.groups()
                self.view.insert(edit, line.end(), canc_line_end)
                replacement = u'%s%s %s' % (grps[0], self.canc_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
            elif done_matches:
                pass
                # grps = done_matches.groups()
                # replacement = u'%s%s %s' % (grps[0], self.canc_tasks_bullet, grps[1].rstrip())
                # self.view.replace(edit, line, replacement)
                # offset = -offset
            elif canc_matches:
                grps = canc_matches.groups()
                replacement = u'%s%s %s' % (grps[0], self.open_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
                offset = -offset
        self.view.sel().clear()
        for ind, pt in enumerate(original):
            ofs = ind * offset
            new_pt = sublime.Region(pt.a + ofs, pt.b + ofs)
            self.view.sel().add(new_pt)


class PlainTasksArchiveCommand(PlainTasksBase):
    def runCommand(self, edit):
        rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '\s*([^\b]*?)\s*(%s)+[\(\)\d\.:\-\/ @]*[ \t]*$' % self.done_tag
        rcm = '^(\s*)' + re.escape(self.canc_tasks_bullet) + '\s*([^\b]*?)\s*(%s)+[\(\)\d\.:\-\/ @]*[ \t]*$' % self.canc_tag

        # finding archive section
        archive_pos = self.view.find('Archive:', 0, sublime.LITERAL)

        done_tasks = []
        done_task = self.view.find(rdm, 0)
        # print(done_task)
        while done_task and (not archive_pos or done_task < archive_pos):
            done_tasks.append(done_task)
            done_task = self.view.find(rdm, done_task.end() + 1)

        canc_tasks = []
        canc_task = self.view.find(rcm, 0)
        # print(canc_task)
        while canc_task and (not archive_pos or canc_task < archive_pos):
            canc_tasks.append(canc_task)
            canc_task = self.view.find(rcm, canc_task.end() + 1)

        all_tasks = done_tasks + canc_tasks
        all_tasks.sort()

        if all_tasks:
            if archive_pos:
                line = self.view.full_line(archive_pos).end()
            else:
                self.view.insert(edit, self.view.size(), u'\n\n＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿\nArchive:\n')
                line = self.view.size()

            projects = self.view.find_all('^\s*(\w+.+:\s*$\n?)|^\s*---.{3,5}---+$', 0)

            # adding tasks to archive section
            self.view.insert(edit, line, '\n'.join(self.before_tasks_bullet_spaces +
                self.view.substr(task).lstrip() + self.get_task_project(task, projects) for task in all_tasks) + '\n')
            # remove moved tasks (starting from the last one otherwise it screw up regions after the first delete)
            for task in reversed(all_tasks):
                self.view.erase(edit, self.view.full_line(task))

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

        prog = re.compile('^\n*([ \t]*).+:')
        hierarhProject = ''

        if index >= 0:
            depth = re.match(r"\s*", self.view.substr(self.view.line(task))).group()
            while index >= 0:
                strProject = self.view.substr(projects[index])
                if prog.match(strProject):
                    spaces = prog.match(strProject).group(1)
                    if len(spaces) < len(depth):
                        hierarhProject = strProject.strip().strip(':') + ((" / " + hierarhProject) if hierarhProject else '')
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
            return ' @project(' + hierarhProject + ')'


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

    LINK_PATTERN = re.compile(r'#(?P<fn>[^ \t\n\r\f\v@]+)(@(?P<sym>\w+))?')

    def _format_res(self, res):
        return [res[0], "line: %d column: %d" % (res[1], res[2])]

    def _on_panel_selection(self, selection):
        if selection >= 0:
            res = self._current_res[selection]
            win = sublime.active_window()
            win.open_file('%s:%s:%s' % res, sublime.ENCODED_POSITION)

    def show_panel_or_open(self, fn, sym):
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
                    filenames = [os.path.join(root, f) for f in filenames]
                    for name in filenames:
                        if name.endswith(fn):
                            self._current_res.append((name, 0, 0))

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
            fn, sym = match.group('fn', 'sym')
            self.show_panel_or_open(fn, sym)
