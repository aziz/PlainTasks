## [PlainTasks](https://github.com/aziz/PlainTasks)
An opinionated todo-list plugin for Sublime Text (2 & 3) editor
![](http://cl.ly/image/1q100Q212o2Q/ss.png)

## Installation
To install this plugin, you have two options:

1. If you have Package Control installed, simply search for `PlainTasks` to install.

2. Clone source code to Sublime Text packages folder.

## Start a new todo-list
Bring up the command palette (it’s <kbd>⌘ + shift + p</kbd> in OS X and <kbd>ctrl + shift + p</kbd> in Windows) and type `task` and select `Tasks: New document` command. 

**NOTE:** Save your todo files with `todo`, `todolist`, `tasks` or `taskpaper` file extensions or just name them `TODO` with no extension.
For more portability you can use `todolist.txt` either as a filename or as suffix for any arbitrary filename.

## Usage
**NOTE:** In Windows or Linux use <kbd>ctrl</kbd> instead of <kbd>⌘</kbd>

☐ <kbd>⌘ + enter</kbd> or <kbd>⌘ + i</kbd>: new task

☐ <kbd>⌘ + d</kbd>: toggle task as completed.

☐ <kbd>ctrl + c</kbd>: toggle task as cancelled on Mac. <kbd>alt + c</kbd> on Windows/Linux.

☐ <kbd>⌘ + shift + a</kbd> will archive the done tasks, by removing them from your list and appending them to the bottom of the file under Archive project

☐ <kbd>⌘ + shift + o</kbd> will archive in Org-Mode style, removing the entire subtree after cursor and appending it to new file next to original one, e.g. if original is `filename.TODO` then new would be `filename_archive.TODO`

☐ <kbd>⌘ + shift + u</kbd> will open the url under the cursor in your default browser, other than http(s) schemes must be enclosed within `<>`, e.g. `<skype:nickname>`

☐ Anything with colon at the end of the line is a project title, you can also nest projects by indenting them. 

☐ You can write plain text as notes or descriptions wherever you want. Use `_` or `*` for italic and bold just like in Markdown.

☐ You can add tags using **`@`** sign

☐ PlainTasks comes with a simple snippet for creating separators, if you feel that your task list is becoming too long you can split it into several sections (and fold some of them) using this snippet:

`--` and then <kbd>tab</kbd> will give you this: `--- ✄ -----------------------`

☐ Completion rules (<kbd>ctrl+space</kbd> to see list of them):  

- type `t`, press <kbd>tab</kbd> — it’ll become `@today` — this one is highlighted differently than other tags;
- `c`, <kbd>tab</kbd> — `@critical`;
- `h`, <kbd>tab</kbd> — `@high`;
- `l`, <kbd>tab</kbd> — `@low`;
- `s`, <kbd>tab</kbd> — `@started` — press <kbd>tab</kbd> again and current date will be inserted, when you’ll complete or cancel a task with such tag, you’ll know how many time has passed since start;
- `tg`, <kbd>tab</kbd>, <kbd>tab</kbd> work in the same manner as `s`, but inserts `@toggle(current date)` — so you can pause and resume to get more correct result when done/cancel; each toggle tag is either pause or resume depending on its place in sequence;
- `cr`, <kbd>tab</kbd>, <kbd>tab</kbd> — `@created(current date)`;
- `d`, <kbd>tab</kbd> — `@due( )`  
  If you press <kbd>tab</kbd> again, it’ll insert current date, same for `@due( 0)`.  
  You can type short date (similar to [OrgMode’s date prompt](http://orgmode.org/manual/The-date_002ftime-prompt.html), but not the same) and then press <kbd>tab</kbd> to expand it into default format.  
  Short date should be __`@due(year-month-day hour:minute)`__  
  Dot can be used instead of hyphen, but should be consistent _`year.month.day`_

    - year, month, minute, hour can be omitted:

        <table>
         <tr>
          <th>  Notation    </th><th>   Meaning     </th>
         </tr>
         <tr>
          <td>  <code>@due(1)</code>    </td>
          <td>  1st day of next month always    </td>
         </tr>
         <tr>
          <td>  <code>@due(5)</code>    </td>
          <td>  5th day of current month (or next month if current day is 5th or older) </td>
         </tr>
         <tr>
          <td>  <code>@due(2-3)</code>  </td>
          <td>  February 3rd of current year or next one    </td>
         </tr>
         <tr>
          <td>  <code>@due(31 23:)</code>   </td>
          <td>  31st day of current/next month at 23 hours and minutes are equal to current moment  </td>
         </tr>
         <tr>
          <td>  <code>@due(16.1.1 1:1)</code>   </td>
          <td>  January 1st of 2016 at 01:01    <code>@due(16-01-01 01:01)</code>  </td>
         </tr>
        </table>

    - relative period of time starts with a plus sign or two  
      __`+[+][number][DdWw][h:m]`__ — number is optional as well as letter `d` for days or letter `w` for weeks.

        <table>
         <tr>
          <th>  Notation    </th><th>   Meaning     </th>
         </tr>
         <tr>
          <td>  <code>@due(+)</code>    </td>
          <td>  tomorrow as well as <code>@due( +1)</code> or <code>@due( +1d)</code></td>
         </tr>
         <tr>
          <td>  <code>@due(+w)</code>    </td>
          <td>  one week since current date, i.e. <code>@due( +7)</code></td>
         </tr>
         <tr>
          <td>  <code>@due(+3w)</code>  </td>
          <td>  3 weeks since current date, i.e. <code>@due( +21d)</code></td>
         </tr>
         <tr>
          <td>  <code>@due(++)</code>   </td>
          <td>  one day since <code>@created(date)</code> if any, otherwise it is equal to <code>@due(+)</code></td>
         </tr>
         <tr>
          <td>  <code>@due(+2:)</code>   </td>
          <td>  two hours since current date</td>
         </tr>
         <tr>
          <td>  <code>@due(+:555)</code>   </td>
          <td>  555 minutes since current date</td>
         </tr>
         <tr>
          <td>  <code>@due(+2 12:)</code>   </td>
          <td>  2 days and 12 hours since current date</td>
         </tr>
        </table>

☐ You can create a link to a file within your project by prefixing the file name with a dot and (back)slash like: `.\filename\` or `./another filename/`.  
  The line and column can be specified by colons: `.\filename:11:8`.  
  In SublimeText 3 you can specify a symbol inside that file by using \> character like: `.\filename>symbol`.  
  In SublimeText 2 you can specify a text inside that file by using inch characters like: `.\filename"any text"`.  
  Pressing <kbd>ctrl + o</kbd> (<kbd>alt + o</kbd> on Windows/Linux) will open the file in Sublime and scroll to specific position if any.  
  In addition, Markdown and “wiki” (Org-Mode, NV, etc.) styles are supported as well, examples:

```
[](path)
[](path ":11:8")
[](path ">symbol")
[](path "any text")
[[path]]
[[path::11:8]]
[[path::*symbol]]
[[path::any text]]
[[path]] ":11:8"
[[path]] ">symbol"
[[path]] "any text"
```

☐ To convert current document to HTML, bring up the command palette <kbd>⌘ + shift + p</kbd> and type `Tasks: View as HTML` — it will be opened in default webbrowser, so you can view and save it.  
`Tasks: Save as HTML…` ask if you want to save and if yes, allow to choose directory and filename (but won’t open it in webbrowser).

### Editor Useful Tools:

☐ Use **<kbd>⌘ + control + up/down</kbd>** (**<kbd>ctrl + shift + up/down</kbd>** on Windows) to move tasks up and down.

☐ Use **<kbd>⌘ + r</kbd>** to see a list of projects and quickly jump between them


★ See the [Tutorial](https://github.com/aziz/PlainTasks/blob/master/messages/Tutorial.todo) for more detailed information.

## Settings
PlainTasks is an opinionated plugin, which means that it is highly configured to look in a specific way, but this does not mean that you can not customize it. If you feel that something does not look right and you want to change it, you can easily do it in your user settings file. 

Go to `Preferences → Package Settings → PlainTasks` and open `Settings - User`, there you can override all the default settings, to get an idea you can take a look at `Settings - Default`.

Here is a list of PlainTasks’ specific settings:

|            Setting             |     Default      |                                 Options/Description                                 |
| ------------------------------ | ---------------- | ----------------------------------------------------------------------- |
| **open_tasks_bullet**          | ☐                | - ❍ ❑ ■ □ ☐ ▪ ▫ – — ≡ → › [ ]                                           |
| **done_tasks_bullet**          | ✔                | ✓   ☑ + [x]                                                               |
| **cancelled_tasks_bullet**     | ✘                | x [-]                                                                   |
| **date_format**                | `(%y-%m-%d %H:%M)` | See [strfti.me](http://www.strfti.me/) for quick reference; detailed documentation: [ST2](https://docs.python.org/2.6/library/datetime.html#strftime-and-strptime-behavior), [ST3](https://docs.python.org/3.3/library/datetime.html#strftime-and-strptime-behavior) |
| **done_tag**                   | true             | Determines whether done tasks should gain a @done tag or not            |
| **before_tasks_bullet_margin** | 1                | Determines the number of spaces (default indent) before the task bullet |
| **project_tag**                | true             | Postfix archived task with project tag, otherwise prefix                |
| **archive_name**               | `Archive:`       | Make sure it is the unique project name within your todo files          |
| **new_on_top**                 | true             | How to sort archived tasks (done_tag=true and default date_format are required)|
| **header_to_task**             | absent (false)   | If true, a project title line will be converted to a task on the certain keystroke  |
| **decimal_minutes**            | absent (false)   | If true, minutes in lasted/wasted tags will be persent of hour, e.g. 1.50 instead of 1:30 |
| **tasks_bullet_space** | absent (whitespace or tab) | String to place after bullet, might be any character(s) |



### Taskpaper Compatibility
Go to `Preferences → Package Settings → PlainTasks` and open `Settings - User`, then
add these settings to the json file:

```json
{
  "translate_tabs_to_spaces": false,
  "date_format": "(%y-%m-%d)",
  "taskpaper_compatible": true
}
```

### Spell check
It is build-in feature of Sublime, you can toggle spell check with <kbd>F6</kbd>.  
For convinience, you may add bullets in list of ignored words into **`Preferences → Settings - User`**, e.g.

```json
{
  "ignored_words": [ "☐", "✔", "✘", "✄" ]
}
```

## [BONUS] Custom todo icon
PlainTasks comes with a custom todo icon that you can find in the `icons` folder. You can assign it to your todo files to give them a better look and distinguish them from other plain text files. Google and find out how to assign a custom icon to a file type in your operating system.

![](http://f.cl.ly/items/2t312B30121l2X1l0927/todo-icon.png)

## [BONUS] Custom Statistics
Statistics of current file are represented in status-bar, based on `stats_format`, which is `"$n/$a done ($percent%) $progress Last task @done $last"` by default — as you can see it’s just a string containing special directives (see table bellow) and regular chars.

| Directive    | Description                                           |
| ------------ | ----------------------------------------------------- |
| `$o`         | Amount of pending tasks                               |
| `$d`         | Amount of completed tasks                             |
| `$c`         | Amount of cancelled tasks                             |
| `$n`         | Sum of completed and cancelled tasks                  |
| `$a`         | Sum of all tasks                                      |
| `$percent`   | Ratio of `$n` to `$a`                                 |
| `$progress`  | Percent as pseudo graphics (absents if less than 10%) |
| `$last`      | Date of lastly completed task                         |
| `{{...}}`    | Return `pending/completed/cancelled` tasks which matched by regex `...`;<br> e.g. `{{@tag}}` — amounts of tasks with `@tag`; or `{{@a|@b}}` — tasks with either `@a` or `@b` or both.<br> You may add several `{{...}}` to get separate stats for different tags. |

So you can customise it as you like, by adding to `Settings - User`, e.g.

```json
{
    "stats_format": "☐$o ✔$d ✘$c",

    // if you want the statistics do not include the archived tasks:
    "stats_ignore_archive": true
}
```

### Copy statistics
Bring up the command palette and type `Tasks: Copy Statistics`.

### Additional settings for progress bar
```json
{
    "bar_full": "■",   // any char
    "bar_empty": "☐", // any char

    // if you want to avoid Unicode when copy stats — you can define replacements
    // e.g. to convert ■■■■■■☐☐☐☐ to [======    ]
    "replace_stats_chars": [[" ■", " [="], ["■", "="], ["☐ ", " ] "], ["☐", " "]]
}
```

## [Introduction to PlainTasks Screencast](https://tutsplus.com/lesson/pretty-task-management/)
[![](http://i46.tinypic.com/9ggbd3.png)](https://tutsplus.com/lesson/pretty-task-management/)


## Contributors
- @antonioriva
- @binaryannie
- [Ben Johnson](https://github.com/benjohnson)
- [Craig Campbell](https://github.com/ccampbell)
- [Dominique Wahli](https://github.com/bizoo)
- [Germán M. Bravo](https://github.com/Kronuz)
- [Hindol Adhya](https://github.com/Hindol)
- [Jesse Robertson](https://github.com/speilberg0)
- [Marc Schlaich](https://github.com/schlamar)
- [Michael McFarland](https://github.com/mikedmcfarland)
- [Pablo Barrios](https://github.com/sauron)
- [Stanislav Parfeniuk](https://github.com/travmik)
- [Vova Kolobok](https://github.com/vovkkk)

You can contribute on [github](https://github.com/aziz/PlainTasks)


## Inspiration
- Thanks to Chagel for the [iTodo plugin](https://github.com/chagel/itodo).  
- Thanks to [Taskmate for TextMate](https://github.com/svenfuchs/taskmate).
- Thanks to [TaskPaper Mac application from hogbaysoftware.com](http://www.hogbaysoftware.com/products/taskpaper)

## License
Copyright 2012-2013 [Allen Bargi](https://twitter.com/aziz). Licensed under the MIT License
