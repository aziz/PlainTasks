# coding: utf-8

import sublime
import os
import re
import webbrowser
import cgi
import tempfile

platform = sublime.platform()
ST2 = int(sublime.version()) < 3000

# io is not operable in ST2 on Linux, but in all other cases io is better
# https://github.com/SublimeTextIssues/Core/issues/254
if ST2 and platform == 'linux':
    import codecs as io
else:
    import io

if not ST2:
    from .plist_parser import parse_file
    from .PlainTasks import PlainTasksBase
else:
    from plist_parser import parse_file
    from PlainTasks import PlainTasksBase


def hex_to_rgba(value):
    value = value.lstrip('#')
    length = len(value)
    if length == 3:
        value = ''.join([v*2 for v in list(value)])
    alpha = [str(round(int(value[6:], 16)/255., 2) if length > 6 else 1.)]
    return [str(int(value[i:i+2], 16)) for i in range(0, 6, 2)] + alpha


def convert_to_rgba_css(word):
    rgba = hex_to_rgba(word)
    rgba_css = 'rgb%s(%s)' % ('a' if len(rgba) > 3 else '', ','.join(rgba))
    return rgba_css


default_ccsl = [  # hand-made repr of tasks.hidden-tmTheme
    'body { background-color: #efe9b7; }',
    'a { color: rgba(0, 62, 114, .55); font-weight: bold; }',
    '.bullet-pending { font-style: normal; font-weight: bold; color: rgba(0,0,0,.6); }',
    '.bullet-done { font-style: normal; font-weight: bold; color: #00723e; }',
    '.bullet-cancelled { font-style: normal; font-weight: bold; color: #b60101; }',
    '.sep { font-style: normal; color: rgba(0,0,0,.44); }',
    '.sep-archive { font-style: normal; color: rgba(0,0,0,.44); }',
    '.header { font-weight: bold; font-style: normal; color: #bc644a; background-color: rgba(0,0,0,.05); width: 100%; }',
    '.tag { font-weight: bold; font-style: normal; color: #C37763; }',
    '.tag-done, .tag-cancelled { font-style: normal; color:#A49F85; }',
    '.tag-today, .tag-critical, .tag-high, .tag-low { font-weight: bold; font-style: normal; color: #000000; }',
    '.tag-today { background: #EADD4E; } .tag-critical{ background: #FF0000; }',
    '.tag-high { background: #FF7F00; }',
    '.tag-low { background: #222222; color: #ffffff; }',
    '.done, .cancelled { color: #66654F; }',
    '.note { font-style: normal; color: #858266; }'
]

scope_to_tag = {  # key is name of regex group, value is regex expression
    'body': r'^body$',
    'a':    r'(?:todo\.)?url(?!\.)',
    # PENDING
    '__open':           r'(?:^|\b)meta(?!\.)',
    '__bullet_pending': r'bullet\.pending(?!\.)',
    # COMPLETED
    '__done':        r'comment(?!\.)',
    '__bullet_done': r'bullet\.completed(?!\.)',
    '__tag_done':    r'tag\.todo\.completed(?!\.)',
    # CANCELLED
    '__cancelled':        r'item\.todo\.cancelled(?!\.)',
    '__bullet_cancelled': r'bullet\.cancelled(?!\.)',
    '__tag_cancelled':    r'tag\.todo\.cancelled(?!\.)',
    # PROJECT & NOTE
    '__header': r'keyword(?!\.)',
    '__note':   r'notes(?:\.todo(?!\.))?',
    # TAGS
    '__tag':          r'(?:^|meta\.)tag(?:\.todo)?(?!\.)',
    '__tag_today':    r'(?:tag\.todo\.)?today(?!\.)',
    '__tag_critical': r'(?:tag\.todo\.)?critical(?!\.)',
    '__tag_high':     r'(?:tag\.todo\.)?high(?!\.)',
    '__tag_low':      r'(?:tag\.todo\.)?low(?!\.)',
    # SEPARATORS
    '__sep':         r'separator(?:\.todo(?!\.))?',
    '__sep_archive': r'archive(?:\.todo(?!\.))?'
}
allrxinone = r'|'.join([('(?P<%s>%s)' % (t, r)) for t, r in scope_to_tag.items()])
SCOPES_REGEX = re.compile(allrxinone)


def convert_tmtheme_to_css(theme_file):
    '''return list of css lines ready to be pasted'''
    if not theme_file:
        return default_ccsl

    theme_as_dict = parse_file(theme_file)
    cssl = []

    # make default color pink, easy to see in case of bugs
    default_color = 'rgb(236,9,140)'
    for i in theme_as_dict.get('settings'):
        s = i.get('settings', {})
        if 'caret' in s:
            default_color = convert_to_rgba_css(s['caret'])

    for item in theme_as_dict.get('settings'):
        scope = item.get('scope', 'body')
        props = item.get('settings', {})
        props_str = ''
        if props:
            for k, v in props.items():
                k = k.replace('foreground', 'color')
                if v:
                    if any(k == w for w in ('background', 'color')):
                        props_str += '%s: %s; ' % (k, convert_to_rgba_css(v) or v)
                    elif k == 'fontStyle':
                        if 'bold' in v:
                            props_str += 'font-weight: bold; font-style: normal; '
                        elif 'italic' in v:
                            props_str += 'font-weight: normal; font-style: italic; '
            if not props.get('fontStyle'):
                props_str += 'font-weight: normal; font-style: normal; '
            if not props.get('foreground'):
                props_str += 'color: %s; ' % default_color
        else:
            props_str += 'color: %s; font-weight: normal; font-style: normal; ' % default_color
        if scope == 'keyword':
            props_str += 'width: 100%; '

        mo = re.search(SCOPES_REGEX, scope)
        tag = mo.lastgroup.replace('__', '.').replace('_', '-') if mo else ''
        if tag:
            cssl.append('%s { %s}' % (tag, props_str))
        # else:
            # if not any(w in scope for w in ('bold', 'italic')):
                # print('\n\n')
                # print('NO TAG FOR', scope)
                # print('REGEX:')
                # print(allrxinone)
                # print(allrxinone.replace(')|(', ')\n('))
                # print('\n\n')
    return cssl


class PlainTasksConvertToHtml(PlainTasksBase):
    def is_enabled(self):
        return self.view.score_selector(0, "text.todo") > 0

    def runCommand(self, edit, ask=False):
        all_lines_regions = self.view.split_by_newlines(sublime.Region(0, self.view.size()))
        html_doc = []
        patterns = {'HEADER':    'text.todo keyword.control.header.todo ',
                    'EMPTY':     'text.todo ',
                    'NOTE':      'text.todo notes.todo ',
                    'OPEN':      'text.todo meta.item.todo.pending ',
                    'DONE':      'text.todo meta.item.todo.completed ',
                    'CANCELLED': 'text.todo meta.item.todo.cancelled ',
                    'SEPARATOR': 'text.todo meta.punctuation.separator.todo ',
                    'ARCHIVE':   'text.todo meta.punctuation.archive.todo '
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
                    elif 'url' in sn:
                        note += '<a href="{0}">{0}</a>'.format(cgi.escape(self.view.substr(s).strip('<>')))
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
                    elif 'tag.todo.critical' in sn:
                        pending += '<span class="tag-critical">%s</span>' % self.view.substr(s)
                    elif 'tag.todo.high' in sn:
                        pending += '<span class="tag-high">%s</span>' % self.view.substr(s)
                    elif 'tag.todo.low' in sn:
                        pending += '<span class="tag-low">%s</span>' % self.view.substr(s)
                    elif 'italic' in sn:
                        pending += '<i>%s</i>' % cgi.escape(self.view.substr(s).strip('_*'))
                    elif 'bold' in sn:
                        pending += '<b>%s</b>' % cgi.escape(self.view.substr(s).strip('_*'))
                    elif 'url' in sn:
                        pending += '<a href="{0}">{0}</a>'.format(cgi.escape(self.view.substr(s).strip('<>')))
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

        title = os.path.basename(self.view.file_name()) if self.view.file_name() else 'Export'
        html  = self.produce_html_from_template(title, html_doc)

        if ask:
            window = sublime.active_window()
            nv = window.new_file()
            nv.set_syntax_file('Packages/HTML/HTML.tmLanguage')
            nv.set_name(title + '.html')
            nv.insert(edit, 0, html)
            window.run_command('close_file')
            return

        tmp_html = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        tmp_html.write(html.encode('utf-8'))
        tmp_html.close()
        webbrowser.open_new_tab("file://%s" % tmp_html.name)

    def produce_html_from_template(self, title, html_doc):
        html_lines = []
        ppath = sublime.packages_path()
        tmtheme = os.path.join(ppath, self.view.settings().get('color_scheme').replace('Packages/', '', 1))
        css = '\n'.join(convert_tmtheme_to_css(tmtheme))
        with io.open(os.path.join(ppath, 'PlainTasks/templates/template.html'), 'r', encoding='utf8') as template:
            for line in template:
                line = (line.replace('$title', title)
                            .replace('$content', '\n'.join(html_doc))
                            .replace('$css', css)
                            .strip('\n'))
                html_lines.append(line)
        return u'\n'.join(html_lines)

    def extracting_scopes(self, edit, region, scope_name=''):
        '''extract scope for each char in line wo dups, ineffective but it works?'''
        scopes = []

        for p in range(region.b-region.a):
            p += region.a
            sr = self.view.extract_scope(p)
            # fix multi-line, because variable region is always a single line
            if sr.a < region.a or sr.b - 1 > region.b:
                if scopes and p == scopes[~0].b:  # *text* inbetween *markups*
                    sr = sublime.Region(p, region.b)
                else:  # multi-line
                    sr = sublime.Region(region.a, region.b)
            # main block, add unique entity to the list
            if sr not in scopes:
                scopes.append(sr)
            elif scopes and self.view.scope_name(p) != self.view.scope_name(scopes[~0].a):
                scopes.append(sublime.Region(p, region.b))
            # fix intersecting regions, e.g. markup in notes
            if scopes and sr.a < scopes[~0].b and p - 1 == scopes[~0].b:
                scopes.append(sublime.Region(scopes[~0].b, sr.b))

        if scopes and scopes[~0].b > region.b:
            # avoid line break at eol
            scopes[~0] = sublime.Region(scopes[~0].a, region.b)

        if len(scopes) > 1:
            # fix bullet
            if scopes[0].intersects(scopes[1]):
                scopes[0] = sublime.Region(scopes[0].a, scopes[1].a)
            # fix text after tag(s)
            if scopes[~0].b < region.b or scopes[~0].a < region.a:
                scopes.append(sublime.Region(scopes[~0].b, region.b))
            new_scopes = scopes[:0:~0]
            for i, s in enumerate(new_scopes):
                # fix overall intersections
                if s.intersects(scopes[~(i + 1)]):
                    if scopes[~(i + 1)].b < s.b:
                        scopes[~i] = sublime.Region(scopes[~(i + 1)].b, s.b)
                        new_scopes[i] = scopes[~i]
                    else:
                        scopes[~(i + 1)] = sublime.Region(scopes[~(i + 1)].a, s.a)
                        if len(new_scopes) > i + 1:
                            new_scopes[i + 1] = scopes[~(i + 1)]
        return scopes
