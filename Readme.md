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

## Usage
**NOTE:** In windows or Linux use `ctrl` instead of `⌘`

☐ `⌘ + enter` or `⌘ + i`: new task

☐ `⌘ + d`: toggle task as completed. You can also use your mouse to mark a task a completed. just hold down `⌘` (or `ctrl` if you're on Windows or Linux) and click the task. Clicking again will toggle the task back to the pending state.

☐ `alt + c`: toggle task as cancelled.

☐ `⌘ + shift + a` will archive the done tasks, by removing them from your list and appending them to the bottom of the file under Archive project

☐ `⌘ + shift + u` will open the url under the cursor in your default browser

☐ Anything with colon at the end of the line is a project title, you can also nest projects by indenting them. 

☐ You can write plain text as notes or descriptions wherever you want.

☐ You can add tags using **`@`** sign

☐ PlainTasks comes with a simple snippet for creating separators, if you feel that your task list is becoming too long you can split it into several sections (and fold some of them) using this snippet:

`--` and then `tab key` will give you this: `--- ✄ -----------------------`

☐ You can create a link to a file within your project by prefixing the file name with a pound sign like: `#filename`.  
  In SublimeText 3 you can even specify a symbol inside that file by using @ symbol like: `#filename@symbol`.  
  Pressing `alt + l` will open the file in Sublime.

### Editor Useful Tools:

☐ Use **`⌘ + control + up/down (ctrl+shift+up/down on Windows)`** to move tasks up and down.

☐ Use **`⌘ + r`** to see a list of projects and quickly jump between them


★ See the [Tutorial](https://github.com/aziz/PlainTasks/blob/master/messages/Tutorial.todo) for more detailed information.

## Settings
PlainTasks is an opinionated plugin, which means that it is highly configured to look in a specific way. but this does not mean that you can not customize it. If you feel that something does not look right and you want to change it, you can easily do it in your user settings file. 

Go to `Preferences > Package Settings > PlainTasks` and open `Settings - User`, there you can override all the default settings. to get an idea you can take a look at `Settings - Default`.

Here is a list of PlainTasks' specific settings:

* **open_tasks_bullet**  
  Default: ☐  
  other valid options: - ❍ ❑ ■ □ ☐ ▪ ▫ – — ≡ → ›

* **done_tasks_bullet**  
  Default: ✔  
  other valid options: + ✓ ☑

* **date_format**  
  Default: (%y-%m-%d %H:%M)

* **done_tag**  
  Default: true  
  Determines whether done tasks should gain a @done tag or not    

* **before_tasks_bullet_margin**  
  Default: 1  
  Determines the number of spaces (default indent) before the task bullet

## Taskpaper Compatibility
Go to `Preferences > Package Settings > PlainTasks` and open `Settings - User`, then
add these settings to the json file:

```json
{
  "before_tasks_bullet_margin": 0,
  "tab_size": 2,
  "translate_tabs_to_spaces": false,
  "open_tasks_bullet": "-",
  "done_tasks_bullet": "-",
  "canc_tasks_bullet": "-"
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

You can contribute on [github](https://github.com/aziz/PlainTasks).    
We always welcome pull requests. Here's some general requirement for pull requests be accepted:  
- [PEP8](http://www.python.org/dev/peps/pep-0008/) is our coding style guide..
- Please create a branch before sending pull requests.
- Your pull request should be atomic. That is, fix a bug or implementing a feature in one commit instead of multiple commit. This is a recommendation, not a requirement.


## Inspiration
- Thanks to Chagel for the [iTodo plugin](https://github.com/chagel/itodo).  
- Thanks to [Taskmate for TextMate](https://github.com/svenfuchs/taskmate).
- Thanks to [TaskPaper Mac application from hogbaysoftware.com](http://www.hogbaysoftware.com/products/taskpaper)

## License
Copyright 2012-2013 [Allen Bargi](https://twitter.com/aziz). Licensed under the MIT License
