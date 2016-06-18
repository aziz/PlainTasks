#!/usr/bin/python
# -*- coding: utf-8 -*-

import sublime, sublime_plugin
import os
import re
import webbrowser
import itertools
from datetime import datetime
from datetime import timedelta

platform = sublime.platform()
ST2 = int(sublime.version()) < 3000

if ST2:
    import locale

# io is not operable in ST2 on Linux, but in all other cases io is better
# https://github.com/SublimeTextIssues/Core/issues/254
if ST2 and platform == 'linux':
    import codecs as io
else:
    import io

NT = platform == 'windows'
if NT:
    import subprocess

class PlainTasksBase(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        settings = self.view.settings()

        self.taskpaper_compatible = settings.get('taskpaper_compatible', False)
        if self.taskpaper_compatible:
            self.open_tasks_bullet = self.done_tasks_bullet = self.canc_tasks_bullet = '-'
            self.before_date_space = ''
        else:
            self.open_tasks_bullet = settings.get('open_tasks_bullet', u'☐')
            self.done_tasks_bullet = settings.get('done_tasks_bullet', u'✔')
            self.canc_tasks_bullet = settings.get('cancelled_tasks_bullet', u'✘')
            self.before_date_space = settings.get('before_date_space', ' ')

        translate_tabs_to_spaces = settings.get('translate_tabs_to_spaces', False)
        self.before_tasks_bullet_spaces = ' ' * settings.get('before_tasks_bullet_margin', 1) if not self.taskpaper_compatible and translate_tabs_to_spaces else '\t'
        self.tasks_bullet_space = settings.get('tasks_bullet_space', ' ' if self.taskpaper_compatible or translate_tabs_to_spaces else '\t')

        self.date_format = settings.get('date_format', '(%y-%m-%d %H:%M)')
        if settings.get('done_tag', True) or self.taskpaper_compatible:
            self.done_tag = "@done"
            self.canc_tag = "@cancelled"
        else:
            self.done_tag = ""
            self.canc_tag = ""

        self.project_postfix = settings.get('project_tag', True)
        self.archive_name = settings.get('archive_name', 'Archive:')
        # org-mode style archive stuff
        self.archive_org_default_filemask = u'{dir}{sep}{base}_archive{ext}'
        self.archive_org_filemask = settings.get('archive_org_filemask', self.archive_org_default_filemask)

        if ST2:
            self.sys_enc = locale.getpreferredencoding()
        self.runCommand(edit, **kwargs)


class PlainTasksNewCommand(PlainTasksBase):
    def runCommand(self, edit):
        # list for ST3 support;
        # reversed because with multiple selections regions would be messed up after first iteration
        regions = itertools.chain(*(reversed(self.view.lines(region)) for region in reversed(list(self.view.sel()))))
        header_to_task = self.view.settings().get('header_to_task', False)
        # ST3 (3080) moves sel when call view.replace only by delta between original and
        # new regions, so if sel is not in eol and we replace line with two lines,
        # then cursor won’t be on next line as it should
        sels = self.view.sel()
        eol  = None
        for i, line in enumerate(regions):
            line_contents  = self.view.substr(line).rstrip()
            not_empty_line = re.match('^(\s*)(\S.*)$', self.view.substr(line))
            empty_line     = re.match('^(\s+)$', self.view.substr(line))
            current_scope  = self.view.scope_name(line.a)
            eol = line.b  # need for ST3 when new content has line break
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
                eol = None
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
            if eol:
                # move cursor to eol of original line, workaround for ST3
                sels.subtract(sels[~i])
                sels.add(sublime.Region(eol, eol))
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


class PlainTasksNewWithDateCommand(PlainTasksBase):
    def runCommand(self, edit):
        self.view.run_command('plain_tasks_new')
        sels = list(self.view.sel())
        suffix = ' @created%s' % datetime.now().strftime(self.date_format)
        for s in reversed(sels):
            self.view.insert(edit, s.b, suffix)
        self.view.sel().clear()
        offset = len(suffix)
        for i, sel in enumerate(sels):
            self.view.sel().add(sublime.Region(sel.a + i*offset, sel.b + i*offset))


class PlainTasksCompleteCommand(PlainTasksBase):
    def runCommand(self, edit):
        original = [r for r in self.view.sel()]
        try:
            done_line_end = ' %s%s%s' % (self.done_tag, self.before_date_space, datetime.now().strftime(self.date_format).decode(self.sys_enc))
        except:
            done_line_end = ' %s%s%s' % (self.done_tag, self.before_date_space, datetime.now().strftime(self.date_format))
        done_line_end = done_line_end.replace('  ', ' ').rstrip()
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
                self.view.replace(edit, line, replacement.rstrip())
                offset = -offset
            elif 'cancelled' in current_scope:
                grps = canc_matches.groups()
                self.view.insert(edit, line.end(), done_line_end)
                parentheses = self.check_parentheses(self.date_format, grps[4] or '')
                replacement = u'%s%s%s%s' % (grps[0], self.done_tasks_bullet, grps[2], parentheses)
                self.view.replace(edit, line, replacement.rstrip())
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

        toggle_times = [datetime.strptime(toggle, self.date_format) for toggle in toggle_matches]
        all_times = [start] + toggle_times + [end]
        pairs = zip(all_times[::2], all_times[1::2])
        deltas = [pair[1] - pair[0] for pair in pairs]

        delta = sum(deltas, timedelta())
        if self.view.settings().get('decimal_minutes', False):
            days = delta.days
            delta = u'%s%s%s%.2f' % (days or '', ' day, ' if days == 1 else '', ' days, ' if days > 1 else '', delta.seconds/3600.0)
        else:
            delta = str(delta)
        if delta[~6:] == '0:00:00':  # strip meaningless time
            delta = delta[:~6]
        elif delta[~2:] == ':00':  # strip meaningless seconds
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
            canc_line_end = ' %s%s%s' % (self.canc_tag, self.before_date_space, datetime.now().strftime(self.date_format).decode(self.sys_enc))
        except:
            canc_line_end = ' %s%s%s' % (self.canc_tag, self.before_date_space, datetime.now().strftime(self.date_format))
        canc_line_end = canc_line_end.replace('  ', ' ').rstrip()
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
            toggle_matches = re.findall(toggle, line_contents, re.U)

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
                # self.view.replace(edit, line, replacement.rstrip())
                # offset = -offset
            elif 'cancelled' in current_scope:
                grps = canc_matches.groups()
                parentheses = PlainTasksCompleteCommand.check_parentheses(self.date_format, grps[4] or '')
                replacement = u'%s%s%s%s' % (grps[0], self.open_tasks_bullet, grps[2], parentheses)
                self.view.replace(edit, line, replacement.rstrip())
                offset = -offset
        self.view.sel().clear()
        for ind, pt in enumerate(original):
            ofs = ind * offset
            new_pt = sublime.Region(pt.a + ofs, pt.b + ofs)
            self.view.sel().add(new_pt)

        PlainTasksStatsStatus.set_stats(self.view)


class PlainTasksArchiveCommand(PlainTasksBase):
    def runCommand(self, edit, partial=False):
        rds = 'meta.item.todo.completed'
        rcs = 'meta.item.todo.cancelled'

        # finding archive section
        archive_pos = self.view.find(self.archive_name, 0, sublime.LITERAL)

        if partial:
            all_tasks = self.get_archivable_tasks_within_selections()
        else:
            all_tasks = self.get_all_archivable_tasks(archive_pos, rds, rcs)

        if not all_tasks:
            sublime.status_message('Nothing to archive')
        else:
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
                               match_task.group(1) +  # bullet
                               (self.tasks_bullet_space if pr else '') + pr + (':' if pr else '') +
                               match_task.group(2) +  # very task
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

    def get_all_archivable_tasks(self, archive_pos, rds, rcs):
        done_tasks = [i for i in self.view.find_by_selector(rds) if i.a < (archive_pos.a if archive_pos and archive_pos.a > 0 else self.view.size())]
        for i in done_tasks:
            self.get_task_note(i, done_tasks)

        canc_tasks = [i for i in self.view.find_by_selector(rcs) if i.a < (archive_pos.a if archive_pos and archive_pos.a > 0 else self.view.size())]
        for i in canc_tasks:
            self.get_task_note(i, canc_tasks)

        all_tasks = done_tasks + canc_tasks
        all_tasks.sort()
        return all_tasks

    def get_archivable_tasks_within_selections(self):
        all_tasks = []
        for region in self.view.sel():
            for l in self.view.lines(region):
                line = self.view.line(l)
                if ('completed' in self.view.scope_name(line.a)) or ('cancelled' in self.view.scope_name(line.a)):
                    all_tasks.append(line)
                    self.get_task_note(line, all_tasks)
        return all_tasks


class PlainTasksNewTaskDocCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.settings().add_on_change('color_scheme', lambda: self.set_proper_scheme(view))
        view.set_syntax_file('Packages/PlainTasks/PlainTasks.tmLanguage')

    def set_proper_scheme(self, view):
        if view.id() != sublime.active_window().active_view().id():
            return
        pts = sublime.load_settings('PlainTasks.sublime-settings')
        if view.settings().get('color_scheme') == pts.get('color_scheme'):
            return
        # Since we cannot create file with syntax, there is moment when view has no settings,
        # but it is activated, so some plugins (e.g. Color Highlighter) set wrong color scheme
        view.settings().set('color_scheme', pts.get('color_scheme'))


class PlainTasksOpenUrlCommand(sublime_plugin.TextCommand):
    #It is horrible regex but it works perfectly
    URL_REGEX = r"""(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))
        +(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""

    def run(self, edit):
        s = self.view.sel()[0]
        start, end = s.a, s.b
        if 'url' in self.view.scope_name(start):
            while self.view.substr(start) != '<': start -= 1
            while self.view.substr(end)   != '>': end += 1
            rgn = sublime.Region(start + 1, end)
            # optional select URL
            self.view.sel().add(rgn)
            url = self.view.substr(rgn)
            if NT and all([not ST2, ':' in url]):
                # webbrowser uses os.startfile() under the hood, and it is not reliable in py3;
                # thus call start command for url with scheme (eg skype:nick) and full path (eg c:\b)
                subprocess.Popen(['start', url], shell=True)
            else:
                webbrowser.open_new_tab(url)
        else:
            self.search_bare_weblink_and_open(start, end)

    def search_bare_weblink_and_open(self, start, end):
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
    LINK_PATTERN = re.compile( # simple ./path/
        r'''(?ixu)(?:^|[ \t])\.[\\/]
            (?P<fn>
            (?:[a-z]\:[\\/])?      # special case for Windows full path
            (?:[^\\/:">]+[\\/]?)+) # the very path (single filename/relative/full)
            (?=[\\/:">])           # stop matching path
                                   # options:
            (>(?P<sym>\w+))?(\:(?P<line>\d+))?(\:(?P<col>\d+))?(\"(?P<text>[^\n]*)\")?
        ''')
    MD_LINK = re.compile( # markdown [](path)
        r'''(?ixu)\][ \t]*\(\<?(?:file\:///?)?
            (?P<fn>.*?((\\\))?.*?)*)
              (?:\>?[ \t]*
              \"((\:(?P<line>\d+))?(\:(?P<col>\d+))?|(\>(?P<sym>\w+))?|(?P<text>[^\n]*))
              \")?
            \)
        ''')
    WIKI_LINK = re.compile(  # ORGMODE, NV, and all similar formats [[link][opt-desc]]
        r'''(?ixu)\[\[(?:file(?:\+(?:sys|emacs))?\:)?(?:\.[\\/])?
            (?P<fn>.*?((\\\])?.*?)*)
              (?# options for orgmode link [[path::option]])
              (?:\:\:(((?P<line>\d+))?(\:(?P<col>\d+))?|(\*(?P<sym>\w+))?|(?P<text>.*?((\\\])?.*?)*)))?
            \](?:\[(.*?)\])?
            \]
              (?# options for NV [[path]] "option" — NV not support it, but PT should support so it wont break NV)
              (?:[ \t]*
              \"((\:(?P<linen>\d+))?(\:(?P<coln>\d+))?|(\>(?P<symn>\w+))?|(?P<textn>[^\n]*))
              \")?
        ''')

    def _format_res(self, res):
        if res[3] == 'f':
            return [res[0], "line: %d column: %d" % (int(res[1]), int(res[2]))]
        elif res[3] == 'd':
            return [res[0], 'Add folder to project' if not ST2 else 'Folders are supported only in Sublime 3']

    def _on_panel_selection(self, selection):
        if selection >= 0:
            res = self._current_res[selection]
            win = sublime.active_window()
            if ST2 and res[3] == "d":
                return sublime.status_message('Folders are supported only in Sublime 3')
            elif res[3] == "d":
                data = win.project_data()
                if not data:
                    data = {}
                if "folders" not in data:
                    data["folders"] = []
                data["folders"].append({'follow_symlinks': True,
                                        'path': res[0]})
                win.set_project_data(data)
            else:
                self.opened_file = win.open_file('%s:%s:%s' % res[:3],
                                                 sublime.ENCODED_POSITION)

    def show_panel_or_open(self, fn, sym, line, col, text):
        win = sublime.active_window()
        self._current_res = list()
        if sym:
            for name, _, pos in win.lookup_symbol_in_index(sym):
                if name.endswith(fn):
                    line, col = pos
                    self._current_res.append((name, line, col, "f"))
        else:
            fn = fn.replace('/', os.sep)
            all_folders = win.folders() + [os.path.dirname(v.file_name()) for v in win.views() if v.file_name()]
            for folder in set(all_folders):
                for root, _, _ in os.walk(folder):
                    name = os.path.abspath(os.path.join(root, fn))
                    if os.path.isfile(name):
                        self._current_res.append((name, line or 0, col or 0, "f"))
                    if os.path.isdir(name):
                        self._current_res.append((name, 0, 0, "d"))
            if os.path.isfile(fn):  # check for full path
                self._current_res.append((fn, line or 0, col or 0, "f"))
            elif os.path.isdir(fn):
                self._current_res.append((fn, 0, 0, "d"))
            self._current_res = list(set(self._current_res))
        if not self._current_res:
            sublime.error_message('File was not found\n\n\t%s' % fn)
        if len(self._current_res) == 1:
            self._on_panel_selection(0)
        else:
            entries = [self._format_res(res) for res in self._current_res]
            win.show_quick_panel(entries, self._on_panel_selection)

    def run(self, edit, fn=None):
        point = self.view.sel()[0].begin()
        line = self.view.substr(self.view.line(point))
        match_link = self.LINK_PATTERN.search(line)
        match_md   = self.MD_LINK.search(line)
        match_wiki = self.WIKI_LINK.search(line)
        if match_link:
            fn, sym, line, col, text = match_link.group('fn', 'sym', 'line', 'col', 'text')
        elif match_md:
            fn, sym, line, col, text = match_md.group('fn', 'sym', 'line', 'col', 'text')
            # unescape some chars
            fn = (fn.replace('\\(', '(').replace('\\)', ')'))
        elif match_wiki:
            fn   = match_wiki.group('fn')
            sym  = match_wiki.group('sym') or match_wiki.group('symn')
            line = match_wiki.group('line') or match_wiki.group('linen')
            col  = match_wiki.group('col') or match_wiki.group('coln')
            text = match_wiki.group('text') or match_wiki.group('textn')
            # unescape some chars
            fn   = (fn.replace('\\[', '[').replace('\\]', ']'))
            if text:
                text = (text.replace('\\[', '[').replace('\\]', ']'))
        if fn:
            self.show_panel_or_open(fn, sym, line, col, text)
            if text:
                sublime.set_timeout(lambda: self.find_text(self.opened_file, text, line), 300)
        else:
            sublime.status_message('Line does not contain a valid link to file')

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
            )?''', matchstr)
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
        delta = now + timedelta(days=(number*7 if weeks else number), minutes=minute, hours=hour)
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
                elif not day:  # @due(0) == today
                    day = now.day
                # else would be day>now, i.e. future day in current month
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


class PlainTasksRemoveBold(sublime_plugin.TextCommand):
    def run(self, edit):
        for s in reversed(list(self.view.sel())):
            a, b = s.begin(), s.end()
            for r in sublime.Region(b + 2, b), sublime.Region(a - 2, a):
                self.view.erase(edit, r)


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
        barempty = view.settings().get('bar_empty', u'□')
        progress = '%s%s' % (barfull*factor, barempty*(10-factor)) if factor else ''

        tasks_dates = []
        view.find_all('(^\s*[^\n]*?\s\@(?:done)\s*(\([\d\w,\.:\-\/ ]*\))[^\n]*$)', 0, "\\2", tasks_dates)
        date_format = view.settings().get('date_format', '(%y-%m-%d %H:%M)')
        tasks_dates = [PlainTasksCompleteCommand.check_parentheses(date_format, t, is_date=True) for t in tasks_dates]
        tasks_dates.sort(reverse=True)
        last = tasks_dates[0] if tasks_dates else '(UNKNOWN)'

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
        # Archive the curent subtree to our archive file, not just completed tasks.
        # For now, it's mapped to ctrl-shift-o or super-shift-o

        # TODO: Mark any tasks found as complete, or maybe warn.

        # Get our archive filename
        archive_filename = self.__createArchiveFilename()

        # Figure out our subtree
        region = self.__findCurrentSubtree()
        if region.empty():
            # How can we get here?
            sublime.error_message("Error:\n\nCould not find a tree to archive.")
            return

        # Write our region or our archive file
        success = self.__writeArchive(archive_filename, region)

        # only erase our region if the write was successful
        if success:
            self.view.erase(edit,region)

        return

    def __writeArchive(self, filename, region):
        # Write out the given region

        sublime.status_message(u'Archiving tree to {0}'.format(filename))
        try:
            # Have to use io.open because windows doesn't like writing
            # utf8 to regular filehandles
            with io.open(filename, 'a', encoding='utf8') as fh:
                data = self.view.substr(region)
                # Is there a way to read this in?
                fh.write(u"--- ✄ -----------------------\n")
                fh.write(u"Archived {0}:\n".format(datetime.now().strftime(
                    self.date_format)))
                # And, finally, write our data
                fh.write(u"{0}\n".format(data))
            return True

        except Exception as e:
            sublime.error_message(u"Error:\n\nUnable to append to {0}\n{1}".format(
                filename, str(e)))
            return False

    def __createArchiveFilename(self):
        # Create our archive filename, from the mask in our settings.

        # Split filename int dir, base, and extension, then apply our mask
        path_base, extension = os.path.splitext(self.view.file_name())
        dir  = os.path.dirname(path_base)
        base = os.path.basename(path_base)
        sep  = os.sep

        # Now build our new filename
        try:
            # This could fail, if someone messed up the mask in the
            # settings.  So, if it did fail, use our default.
            archive_filename = self.archive_org_filemask.format(
                dir=dir, base=base, ext=extension, sep=sep)
        except:
            # Use our default mask
            archive_filename = self.archive_org_default_filemask.format(
                    dir=dir, base=base, ext=extension, sep=sep)

            # Display error, letting the user know
            sublime.error_message(u"Error:\n\nInvalid filemask:{0}\nUsing default: {1}".format(
                self.archive_org_filemask, self.archive_org_default_filemask))

        return archive_filename

    def __findCurrentSubtree(self):
        # Return the region that starts at the cursor, or starts at
        # the beginning of the selection

        line = self.view.line(self.view.sel()[0].begin())
        # Start finding the region at the beginning of the next line
        region = self.view.indented_region(line.b + 2)

        if region.contains(line.b):
            # there is no subtree
            return sublime.Region(-1, -1)

        if not region.empty():
            region = sublime.Region(line.a, region.b)

        return region


def pt_mouse(view, args):
    if view.score_selector(0, "text.todo") > 0:
        cursor = view.sel()[0].a
        # cursor = user click on left side of bullet, -1 = right side
        if any('bullet' in view.scope_name(r) for r in [cursor, cursor - 1]):
            view.run_command('plain_tasks_complete')
    else:
        system_command = args["command"] if "command" in args else None
        if system_command:
            system_args = dict({"event": args["event"]}.items())
            system_args.update(dict(args["args"].items()))
            view.run_command(system_command, system_args)

if not ST2:
    class PlainTasksClickCommand(sublime_plugin.TextCommand):
        def run_(self, view, args):
            pt_mouse(self.view, args)
else:
    class PlainTasksClickCommand(sublime_plugin.TextCommand):
        def run_(self, args):
            pt_mouse(self.view, args)
