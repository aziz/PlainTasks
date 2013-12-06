## [PlainTasks](https://github.com/aziz/PlainTasks)
An opinionated todo-list plugin for Sublime Text (2 & 3) editor
![](http://f.cl.ly/items/2y2m3v1i0S2V1t2m2A0e/Screen%20Shot%202012-04-21%20at%2012.27.05%20AM.png)

## Installation
To install this plugin, you have two options:

1. If you have Package Control installed, simply search for `PlainTasks` to install.

2. Clone source code to Sublime Text packages folder.

## Start a new todo-list
Bring up the command palette (it's `⌘ + shift + p`  in OS X and `ctrl + shift + p` in Windows) and type `task` and select `Tasks: New document` command. 

**NOTE:** Save your todo files with `todo`, `todolist`, `tasks` or `taskpaper` file extensions or just name them `TODO` with no extension.
For more portability you can use `todolist.txt` either as a filename or as suffix for any arbitrary filename.

## Usage
**NOTE:** In windows or Linux use `ctrl` instead of `⌘`

☐ `⌘ + enter` or `⌘ + i`: new task

☐ `⌘ + d`: toggle task as completed. You can also use your mouse to mark a task a completed. just hold down `⌘` (or `ctrl` if you're on Windows or Linux) and click the task. Clicking again will toggle the task back to the pending state.

☐ `ctrl + c`: toggle task as cancelled on Mac. `alt + c` on Windows/Linux.

☐ `⌘ + shift + a` will archive the done tasks, by removing them from your list and appending them to the bottom of the file under Archive project

☐ `⌘ + shift + u` will open the url under the cursor in your default browser

☐ Anything with colon at the end of the line is a project title, you can also nest projects by indenting them. 

☐ You can write plain text as notes or descriptions wherever you want.

☐ You can add tags using **`@`** sign

☐ PlainTasks comes with a simple snippet for creating separators, if you feel that your task list is becoming too long you can split it into several sections (and fold some of them) using this snippet:

`--` and then `tab key` will give you this: `--- ✄ -----------------------`

☐ Couple of tags are in completion rules:  

- type `s`, press tab key — it'll become `@started` — press tab again and current date will be inserted, when you'll complete or cancel a task with such tag, you'll know how many time has passed since start;
- type `t`, press tab key — it'll become `@today` — this one is highlighted differently than other tags, you can easily spot which task is important.

☐ You can create a link to a file within your project by prefixing the file name with a dot and (back)slash like: `.\filename\ ./another filename/`.  
  The line and column can be specified by colons: `.\filename:11:8`.  
  In SublimeText 3 you can specify a symbol inside that file by using \> character like: `.\filename>symbol`.  
  In SublimeText 2 you can specify a text inside that file by using inch characters like: `.\filename"any text"`.  
  Pressing `ctrl + o` (`alt + o` on Windows/Linux) will open the file in Sublime and scroll to specific position if any.

### Editor Useful Tools:

☐ Use **`⌘ + control + up/down (ctrl + shift + up/down on Windows)`** to move tasks up and down.

☐ Use **`⌘ + r`** to see a list of projects and quickly jump between them


★ See the [Tutorial](https://github.com/aziz/PlainTasks/blob/master/messages/Tutorial.todo) for more detailed information.

## Settings
PlainTasks is an opinionated plugin, which means that it is highly configured to look in a specific way, but this does not mean that you can not customize it. If you feel that something does not look right and you want to change it, you can easily do it in your user settings file. 

Go to `Preferences > Package Settings > PlainTasks` and open `Settings - User`, there you can override all the default settings, to get an idea you can take a look at `Settings - Default`.

Here is a list of PlainTasks' specific settings:

|            Setting             |     Default      |                                 Options/Description                                 |
| ------------------------------ | ---------------- | ----------------------------------------------------------------------- |
| **open_tasks_bullet**          | ☐                | - ❍ ❑ ■ □ ☐ ▪ ▫ – — ≡ → ›                                               |
| **done_tasks_bullet**          | ✔                | ✓   ☑ +                                                                   |
| **cancelled_tasks_bullet**     | ✘                | x                                                                       |
| **date_format**                | `(%y-%m-%d %H:%M)` |                                                                         |
| **done_tag**                   | true             | Determines whether done tasks should gain a @done tag or not            |
| **before_tasks_bullet_margin** | 1                | Determines the number of spaces (default indent) before the task bullet |
| **project_tag**                | true             | Postfix archived task with project tag, otherwise prefix                |
| **archive_name**               | `Archive:`       | Make sure it is the unique project name within your todo files          |
| **indent_after_task**          | true             | Determines whether next line after task should be indented or not       |
| **new_on_top**                 | true             | How to sort archived tasks (done_tag=true and default date_format are required)|
| **header_to_task**             | absent (false)   | If true, a project title line will be converted to a task on the certain keystroke  |



## Taskpaper Compatibility
Go to `Preferences > Package Settings > PlainTasks` and open `Settings - User`, then
add these settings to the json file:

```json
{
  "before_tasks_bullet_margin": 0,
  "tab_size": 2,
  "translate_tabs_to_spaces": false,
  "date_format": "(%y-%m-%d)",
  "taskpaper_compatible": true
}
```

## [BONUS] Custom todo icon
PlainTasks comes with a custom todo icon that you can find in the `icons` folder. You can assign it to your todo files to give them a better look and distinguish them from other plain text files. Google and find out how to assign a custom icon to a file type in your operating system.

![](http://f.cl.ly/items/2t312B30121l2X1l0927/todo-icon.png)

## [Introduction to PlainTasks Screencast](https://tutsplus.com/lesson/pretty-task-management/)
[![](http://i46.tinypic.com/9ggbd3.png)](https://tutsplus.com/lesson/pretty-task-management/)


## Contributors
- [Dominique Wahli](https://github.com/bizoo)
- [Jesse Robertson](https://github.com/speilberg0)
- [Marc Schlaich](https://github.com/schlamar)
- [Stanislav Parfeniuk](https://github.com/travmik)
- [Vova Kolobok](https://github.com/vovkkk)

You can contribute on [github](https://github.com/aziz/PlainTasks)


## Inspiration
- Thanks to Chagel for the [iTodo plugin](https://github.com/chagel/itodo).  
- Thanks to [Taskmate for TextMate](https://github.com/svenfuchs/taskmate).
- Thanks to [TaskPaper Mac application from hogbaysoftware.com](http://www.hogbaysoftware.com/products/taskpaper)

## License
Copyright 2012-2013 [Allen Bargi](https://twitter.com/aziz). Licensed under the MIT License
