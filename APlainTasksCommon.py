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

        self.project_postfix = settings.get('project_tag', True)
        self.archive_name = settings.get('archive_name', 'Archive:')
        # org-mode style archive stuff
        self.archive_org_default_filemask = u'{dir}{sep}{base}_archive{ext}'
        self.archive_org_filemask = settings.get('archive_org_filemask', self.archive_org_default_filemask)

        if not ST3:
            self.sys_enc = locale.getpreferredencoding()
        self.runCommand(edit, **kwargs)
