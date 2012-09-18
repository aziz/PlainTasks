#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import sublime
import sublime_plugin
from datetime import datetime


class SublimeTasksBase(sublime_plugin.TextCommand):
    def run(self, edit):
        self.open_tasks_bullet = self.view.settings().get('open_tasks_bullet')
        self.done_tasks_bullet = self.view.settings().get('done_tasks_bullet')
        self.date_format = self.view.settings().get('date_format')
        if self.view.settings().get('done_tag'):
            self.done_tag = "@done"
        else:
            self.done_tag = ""
        self.runCommand(edit)


class NewCommand(SublimeTasksBase):
    def runCommand(self, edit):
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            has_bullet = re.match('^(\s*)[' + re.escape(self.open_tasks_bullet) + re.escape(self.done_tasks_bullet) + ']', self.view.substr(line))
            current_scope = self.view.scope_name(self.view.sel()[0].b)
            if has_bullet:
                grps = has_bullet.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.open_tasks_bullet + ' '
                self.view.replace(edit, line, line_contents)
            elif 'header' in current_scope:
                header = re.match('^(\s*)\S+', self.view.substr(line))
                grps = header.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + ' ' + self.open_tasks_bullet + ' '
                self.view.replace(edit, line, line_contents)
            else:
                has_space = re.match('^(\s+)(.*)', self.view.substr(line))
                if has_space:
                    grps = has_space.groups()
                    spaces = grps[0]
                    line_contents = spaces + self.open_tasks_bullet + ' ' + grps[1]
                    self.view.replace(edit, line, line_contents)
                else:
                    line_contents = ' ' + self.open_tasks_bullet + ' ' + self.view.substr(line)
                    self.view.replace(edit, line, line_contents)
                    end = self.view.sel()[0].b
                    pt = sublime.Region(end, end)
                    self.view.sel().clear()
                    self.view.sel().add(pt)


class CompleteCommand(SublimeTasksBase):
    def runCommand(self, edit):
        original = [r for r in self.view.sel()]
        done_line_end = ' %s %s' % (self.done_tag, datetime.now().strftime(self.date_format))
        offset = len(done_line_end)
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            rom = '^(\s*)' + re.escape(self.open_tasks_bullet) + '\s*(.*)$'
            rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '\s*([^\b]*?)\s*(%s)?[\(\)\d\.:\-/ ]*\s*$' % self.done_tag
            open_matches = re.match(rom, line_contents)
            done_matches = re.match(rdm, line_contents)
            if open_matches:
                grps = open_matches.groups()
                print grps
                self.view.insert(edit, line.end(), done_line_end)
                replacement = u'%s%s %s' % (grps[0], self.done_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
            elif done_matches:
                grps = done_matches.groups()
                replacement = u'%s%s %s' % (grps[0], self.open_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
                offset = -offset
        self.view.sel().clear()
        for ind, pt in enumerate(original):
            ofs = ind * offset
            new_pt = sublime.Region(pt.a + ofs, pt.b + ofs)
            self.view.sel().add(new_pt)


class ArchiveCommand(SublimeTasksBase):
    def runCommand(self, edit):
        rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '\s*([^\b]*?)\s*(%s)?[\(\)\d\.:\-/ ]*[ \t]*$' % self.done_tag

        # finding archive section
        archive_pos = self.view.find('Archive:', 0, sublime.LITERAL)

        done_tasks = []
        done_task = self.view.find(rdm, 0)
        print done_task
        while done_task and (not archive_pos or done_task < archive_pos):
            done_tasks.append(done_task)
            done_task = self.view.find(rdm, done_task.end() + 1)

        if done_tasks:
            if archive_pos:
                line = self.view.full_line(archive_pos).end()
            else:
                self.view.insert(edit, self.view.size(), u'\n\n＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿\nArchive:\n')
                line = self.view.size()

            # adding done tasks to archive section
            self.view.insert(edit, line, '\n'.join(' ' + self.view.substr(done_task).lstrip() for done_task in done_tasks) + '\n')
            # remove moved tasks (starting from the last one otherwise it screw up regions after the first delete)
            for done_task in reversed(done_tasks):
                self.view.erase(edit, self.view.full_line(done_task))


class NewTaskDocCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.set_syntax_file('Packages/PlainTasks/PlainTasks.tmLanguage')
