# coding: utf-8
import sublime, sublime_plugin
import itertools

ST3 = int(sublime.version()) >= 3000
if not ST3:
    import locale


def get_all_projects_and_separators(view):
    # because tmLanguage need \n to make background full width of window
    # multiline headers are possible, thus we have to split em to be sure that
    # one header == one line
    projects = itertools.chain(*[view.lines(r) for r in view.find_by_selector('keyword.control.header.todo')])
    return sorted(list(projects) +
                  view.find_by_selector('meta.punctuation.separator.todo'))


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
        self.done_date = settings.get('done_date', True)

        self.project_postfix = settings.get('project_tag', True)
        self.archive_name = settings.get('archive_name', 'Archive:')
        # org-mode style archive stuff
        self.archive_org_default_filemask = u'{dir}{sep}{base}_archive{ext}'
        self.archive_org_filemask = settings.get('archive_org_filemask', self.archive_org_default_filemask)

        if not ST3:
            self.sys_enc = locale.getpreferredencoding()
        self.runCommand(edit, **kwargs)

    def format_line_end(self, tag, tznow):
        try:
            date = tznow.strftime(self.date_format).decode(self.sys_enc)
        except:
            date = tznow.strftime(self.date_format)
        done_line_end = ' %s%s%s' % (tag, self.before_date_space, date if self.done_date else '')
        return done_line_end.replace('  ', ' ').rstrip(), date


class PlainTasksEnabled(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.score_selector(0, "text.todo") > 0

    is_visible = is_enabled


class PlainTasksFold(PlainTasksEnabled):
    def exec_folding(self, visible_region):
        self.view.unfold(sublime.Region(0, self.view.size()))
        for i, d in enumerate(visible_region):
            if not i:  # beginning of document
                self.folding(0, d.a - 1)
            else:  # all regions within
                self.folding(visible_region[i-1].b + 1, d.a - 1)
        if d:  # ending of document
            self.folding(d.b + 1, self.view.size())

    def folding(self, start, end):
        if start < end:
            self.view.fold(sublime.Region(start, end))

    def add_projects_and_notes(self, task_regions):
        '''Context is important, if task has note and belongs to projects, make em visible'''
        def add_note(region):
            # refactor: method in ArchiveCommand
            next_line_begins = region.end() + 1
            while self.view.scope_name(next_line_begins) == 'text.todo notes.todo ':
                note = self.view.line(next_line_begins)
                if note not in task_regions:
                    task_regions.append(note)
                next_line_begins = self.view.line(next_line_begins).end() + 1

        projects = [r for r in get_all_projects_and_separators(self.view) if r.a < task_regions[~0].a]
        for d in reversed(task_regions):
            add_note(d)
            for p in reversed(projects):
                # refactor: different implementation in ArchiveCommand
                project_block = self.view.indented_region(p.end() + 1)
                due_block     = self.view.indented_region(d.begin())
                if all((p not in task_regions, project_block.contains(due_block))):
                    task_regions.append(p)
                    add_note(p)
                if self.view.indented_region(p.begin()).empty():
                    break
        task_regions.sort()
        return task_regions
