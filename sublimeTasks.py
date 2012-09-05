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
        self.runCommand(edit)


class NewCommand(SublimeTasksBase):
    def runCommand(self, edit):
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            has_bullet = re.match('^(\s*)[' + re.escape(self.open_tasks_bullet) + re.escape(self.done_tasks_bullet) + ']', self.view.substr(line))
            if has_bullet:
                grps = has_bullet.groups()
                line_contents = self.view.substr(line) + '\n' + grps[0] + self.open_tasks_bullet + ' '
                self.view.replace(edit, line, line_contents)
            else:
                has_space = re.match('^(\s+)(.*)', self.view.substr(line))
                # is_heading = self.view.score_selector(line, "keyword.control.header.todo") == 0
                # print is_heading
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
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line).rstrip()
            rom = '^(\s*)' + re.escape(self.open_tasks_bullet) + '\s*(.*)$'
            rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '\s*([^\b]*)\s*@done(.)+\)$'
            open_matches = re.match(rom, line_contents)
            done_matches = re.match(rdm, line_contents)
            if open_matches:
                grps = open_matches.groups()
                self.view.insert(edit, line.end(), " @done (%s)" % datetime.now().strftime("%Y-%m-%d %H:%M"))
                replacement = u'%s%s %s' % (grps[0], self.done_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)
            elif done_matches:
                grps = done_matches.groups()
                replacement = u'%s%s %s' % (grps[0], self.open_tasks_bullet, grps[1].rstrip())
                self.view.replace(edit, line, replacement)


class ArchiveCommand(SublimeTasksBase):
    def runCommand(self, edit):
        #print "========================================================================"

        file_content = self.view.substr(sublime.Region(0, self.view.size()))
        done_tasks = []
        rdm = '^(\s*)' + re.escape(self.done_tasks_bullet) + '\s*([^\b]*)\s*@done(.)+\)$'
        # finding done tasks
        for line in file_content.split("\n"):
            if line == "Archive:":
                break
            done_matches = re.match(rdm, line)
            if done_matches:
                done_tasks.append(line)

        # print done_tasks

        # deleting done tasks
        for task in done_tasks:
            region = self.view.find(re.escape(task + "\n"), 0)
            self.view.erase(edit, region)

        # finding archive section
        archive_pos = self.view.find("Archive:", 0)
        if archive_pos:
            line = self.view.line(archive_pos)
            line_content = self.view.substr(line)
        else:
            self.view.insert(edit, self.view.size(), u"\n\n＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿\nArchive:")
            line = self.view.line(self.view.size())
            line_content = self.view.substr(line)

        # adding done tasks to archive section
        if done_tasks:
            self.view.replace(edit, line, line_content + "\n" + "\n".join(done_tasks))

        # if no archive section add one at the end of file
        # manipulate each done task and prefix it with project name

        # x = sublime.active_window().active_view()


class NewTaskDocCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.set_syntax_file('Packages/Tasks/tasks.tmLanguage')
