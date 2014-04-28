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
        translate_tabs_to_spaces = self.view.settings().get('translate_tabs_to_spaces')
        self.before_tasks_bullet_spaces = ' ' * self.view.settings().get('before_tasks_bullet_margin') if translate_tabs_to_spaces else '\t'
        self.tasks_bullet_space = self.view.settings().get('tasks_bullet_space', ' ' if translate_tabs_to_spaces else '\t')
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
            not_empty_line = re.match('^(\s*)(\S.+)$', self.view.substr(line))
            empty_line     = re.match('^(\s+)$', self.view.substr(line))
            current_scope  = self.view.scope_name(line.a)
            if 'item' in current_scope:
                grps = not_empty_line.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.open_tasks_bullet + self.tasks_bullet_space
            elif 'header' in current_scope and not self.view.settings().get('header_to_task'):
                grps = not_empty_line.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.before_tasks_bullet_spaces + self.open_tasks_bullet + self.tasks_bullet_space
            elif 'separator' in current_scope:
                grps = not_empty_line.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.before_tasks_bullet_spaces + self.open_tasks_bullet + self.tasks_bullet_space
            elif not ('header' and 'separator') in current_scope or self.view.settings().get('header_to_task'):
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
        rom = r'^(\s*)(\[\s\]|.)(\s*.*)$'
        rdm = r'^(\s*)(\[x\]|.)(\s*[^\b]*?\s*)(?=\s@done|@project|\s\(|$).*$'
        rcm = r'^(\s*)(\[\-\]|.)(\s*[^\b]*?\s*)(?=\s@cancelled|@project|\s\(|$).*$'
        started = r'^\s*[^\b]*?\s*@started(\([\d\w,\.:\-\/ @]*\)).*$'
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            open_matches = re.match(rom, line_contents, re.U)
            done_matches = re.match(rdm, line_contents, re.U)
            canc_matches = re.match(rcm, line_contents, re.U)
            started_matches = re.match(started, line_contents, re.U)
            current_scope = self.view.scope_name(line.a)
            if 'pending' in current_scope:
                grps = open_matches.groups()
                eol = self.view.insert(edit, line.end(), done_line_end)
                replacement = u'%s%s%s' % (grps[0], self.done_tasks_bullet, grps[2].rstrip())
                self.view.replace(edit, line, replacement)
                if started_matches:
                    eol -= len(grps[1]) - len(self.done_tasks_bullet)
                    self.calc_end_start_time(self, edit, line, started_matches.group(1), done_line_end, eol)
            elif 'header' in current_scope:
                eol = self.view.insert(edit, line.end(), done_line_end)
                if started_matches:
                    self.calc_end_start_time(self, edit, line, started_matches.group(1), done_line_end, eol)
                indent = re.match('^(\s*)\S', line_contents, re.U)
                self.view.insert(edit, line.begin() + len(indent.group(1)), '%s ' % self.done_tasks_bullet)
            elif 'completed' in current_scope:
                grps = done_matches.groups()
                replacement = u'%s%s%s' % (grps[0], self.open_tasks_bullet, grps[2].rstrip())
                self.view.replace(edit, line, replacement)
                offset = -offset
            elif 'cancelled' in current_scope:
                grps = canc_matches.groups()
                self.view.insert(edit, line.end(), done_line_end)
                replacement = u'%s%s%s' % (grps[0], self.done_tasks_bullet, grps[2].rstrip())
                self.view.replace(edit, line, replacement)
                offset = -offset
        self.view.sel().clear()
        for ind, pt in enumerate(original):
            ofs = ind * offset
            new_pt = sublime.Region(pt.a + ofs, pt.b + ofs)
            self.view.sel().add(new_pt)

    @staticmethod
    def calc_end_start_time(self, edit, line, started_matches, done_line_end, eol, tag='lasted'):
        start = datetime.strptime(started_matches, self.date_format)
        end = datetime.strptime(done_line_end.replace('@done', '').replace('@cancelled', '').strip(), self.date_format)
        self.view.insert(edit, line.end() + eol, ' @%s(%s)' % (tag, str(end - start)))


class PlainTasksCancelCommand(PlainTasksBase):
    def runCommand(self, edit):
        original = [r for r in self.view.sel()]
        try:
            canc_line_end = ' %s%s%s' % (self.canc_tag,self.before_date_space, datetime.now().strftime(self.date_format).decode(self.sys_enc))
        except:
            canc_line_end = ' %s%s%s' % (self.canc_tag,self.before_date_space, datetime.now().strftime(self.date_format))
        offset = len(canc_line_end)
        rom = r'^(\s*)(\[\s\]|.)(\s*.*)$'
        rdm = r'^(\s*)(\[x\]|.)(\s*[^\b]*?\s*)(?=\s@done|@project|\s\(|$).*$'
        rcm = r'^(\s*)(\[\-\]|.)(\s*[^\b]*?\s*)(?=\s@cancelled|@project|\s\(|$).*$'
        started = '^\s*[^\b]*?\s*@started(\([\d\w,\.:\-\/ @]*\)).*$'
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            open_matches = re.match(rom, line_contents, re.U)
            done_matches = re.match(rdm, line_contents, re.U)
            canc_matches = re.match(rcm, line_contents, re.U)
            started_matches = re.match(started, line_contents, re.U)
            current_scope = self.view.scope_name(line.a)
            if 'pending' in current_scope:
                grps = open_matches.groups()
                eol = self.view.insert(edit, line.end(), canc_line_end)
                replacement = u'%s%s%s' % (grps[0], self.canc_tasks_bullet, grps[2].rstrip())
                self.view.replace(edit, line, replacement)
                if started_matches:
                    eol -= len(grps[1]) - len(self.canc_tasks_bullet)
                    PlainTasksCompleteCommand.calc_end_start_time(self, edit, line, started_matches.group(1), canc_line_end, eol, tag='wasted')
            elif 'header' in current_scope:
                eol = self.view.insert(edit, line.end(), canc_line_end)
                if started_matches:
                    PlainTasksCompleteCommand.calc_end_start_time(self, edit, line, started_matches.group(1), canc_line_end, eol, tag='wasted')
                indent = re.match('^(\s*)\S', line_contents, re.U)
                self.view.insert(edit, line.begin() + len(indent.group(1)), '%s ' % self.canc_tasks_bullet)
            elif 'completed' in current_scope:
                sublime.status_message('You cannot cancel what have been done, can you?')
                # grps = done_matches.groups()
                # replacement = u'%s%s%s' % (grps[0], self.canc_tasks_bullet, grps[2].rstrip())
                # self.view.replace(edit, line, replacement)
                # offset = -offset
            elif 'cancelled' in current_scope:
                grps = canc_matches.groups()
                replacement = u'%s%s%s' % (grps[0], self.open_tasks_bullet, grps[2].rstrip())
                self.view.replace(edit, line, replacement)
                offset = -offset
        self.view.sel().clear()
        for ind, pt in enumerate(original):
            ofs = ind * offset
            new_pt = sublime.Region(pt.a + ofs, pt.b + ofs)
            self.view.sel().add(new_pt)


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

            projects = self.view.find_all('^\s*(\w+.+:\s*(\@[^\s]+(\(.*?\))?\s*)*$\n?)|^\s*---.{3,5}---+$', 0)

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
    LINK_PATTERN = re.compile(r'\.[\\/](?P<fn>[^\\/:*?"<>|]+)+[\\/]?(>(?P<sym>\w+))?(\:(?P<line>\d+))?(\:(?P<col>\d+))?(\"(?P<text>[^\n]*)\")?', re.I| re.U)

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
                for root, dirnames, filenames in os.walk(folder):
                    filenames = [os.path.join(root, f) for f in filenames]
                    for name in filenames:
                        if name.lower().endswith(fn.lower()):
                            self._current_res.append((name, line if line else 0, col if col else 0))
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


class PlainTasksConvertToHtml(PlainTasksBase):
    def is_enabled(self):
        return self.view.score_selector(0, "text.todo") > 0

    def runCommand(self, edit):
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
                ht = '<span class="header">%s</span>' % self.view.substr(r)

            elif i == patterns['EMPTY']:
                # these are empty lines
                ht = '<span class="empty-line">%s</span>' % self.view.substr(r)

            elif patterns['NOTE'] in i:
                ht = note = '<span class="note">%s</span>' % self.view.substr(r)

            elif patterns['OPEN'] in i:
                scopes = self.extracting_scopes(self, r)
                indent = self.view.substr(sublime.Region(r.a, scopes[0].a)) if r.a != scopes[0].a else ''
                pending = '<span class="open">%s' % indent
                for s in scopes:
                    sn = self.view.scope_name(s.a)
                    if 'bullet' in sn:
                        pending += '<span class="bullet-pending">%s</span>' % self.view.substr(s)
                    elif 'meta.tag' in sn:
                        pending += '<span class="tag">%s</span>' % self.view.substr(s)
                    elif 'tag.todo.today' in sn:
                        pending += '<span class="tag-today">%s</span>' % self.view.substr(s)
                    else:
                        pending += self.view.substr(s)
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
                        done += '<span class="tag-done">%s</span>' % self.view.substr(s)
                    else:
                        done += self.view.substr(s)
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
                        cancelled += '<span class="tag-cancelled">%s</span>' % self.view.substr(s)
                    else:
                        cancelled += self.view.substr(s)
                ht = cancelled + '</span>'

            elif patterns['SEPARATOR'] in i:
                ht = sep = '<span class="sep">%s</span>' % self.view.substr(r)

            elif patterns['ARCHIVE'] in i:
                ht = sep_archive = '<span class="sep-archive">%s</span>' % self.view.substr(r)

            else:
                sublime.error_message('Hey! you are not supposed to see this message.\n'
                                      'Please, report an issue in PlainTasks repository on GitHub.')
            html_doc.append(ht)

        # create file
        import tempfile, io
        tmp_html = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        with io.open('%s/PlainTasks/templates/template.html' % sublime.packages_path(), 'r', encoding='utf8') as template:
            title = os.path.basename(self.view.file_name()) if self.view.file_name() else 'Export'
            for line in template:
                line = line.replace('$title', title).replace('$content', '\n'.join(html_doc))
                tmp_html.write(line.encode('utf-8'))
        tmp_html.close()
        webbrowser.open_new_tab("file://%s" % tmp_html.name)

    def extracting_scopes(self, edit, region):
        '''extract scope for each char in line wo dups, ineffective but reliable'''
        scopes = []
        for p in range(region.b-region.a):
            scope_region = self.view.extract_scope(region.a + p)
            if scope_region != region and scope_region.b - 1 <= region.b and scope_region not in scopes:
                    scopes.append(scope_region)
        if len(scopes) > 2:
            # fix bullet
            if scopes[0].intersects(scopes[1]):
                scopes[0] = sublime.Region(scopes[0].a, scopes[1].a)
            # fix text after tag(s)
            if scopes[~0].b <= region.b or scopes[~0].a < region.a:
                scopes.append(sublime.Region(scopes[~0].b, region.b))
                for i, s in enumerate(scopes[:0:~0]):
                    if s.intersects(scopes[~(i + 1)]):
                        scopes[~i] = sublime.Region(scopes[~(i + 1)].b, s.b)
        return scopes
