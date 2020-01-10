Menu Generation
===============

Most robots will require some kind of menu system, to select challenges, configure settings etc. To build this we need
three things:

    1. A definition of the menu structure.
    2. Some way to display the current state.
    3. Some way to navigate around the menus, select items etc.

You could do all this with a bunch of ``if`` statements, but that approach very rapidly becomes unmaintainable. Instead
this library provides a way to configure a menu system from a dictionary (explicitly defined, or loaded from a YAML
file), and then automatically builds the corresponding tasks to display and navigate around those configured items.

Because all robots are different, you will have to write a bit of custom code to handle display and navigation. You do
this by subclassing :class:`approxeng.task.menu.MenuTask` and implementing two methods,
:meth:`~approxeng.task.menu.MenuTask.get_menu_action` and :meth:`~approxeng.task.menu.MenuTask.display_menu`. You then
use this class when calling :func:`~approxeng.task.menu.register_menu_tasks` (to load from a dictionary) or
:func:`~approxeng.task.menu.register_menu_tasks_from_yaml` when loading menu definitions from a YAML file.

If your display and navigation system needs access to resources (it almost certainly does) such as joysticks, or display
hardware, these are provided in the normal way to the menu tasks through the world object. You have access to this when
implementing your custom menu task class, along with other properties you'll need such as the currently selected item,
name of the active menu and similar. When you call the register function you can explicitly specify which resources your
class needs to function, this works the same way as for any other task (the menus are just tasks themselves).

To activate a menu, just switch active task to the name of the menu. This is probably something you'd do as a root task
in most robots, but you might want to explicitly activate them at other times - there's no limit to the number of menus
you can have, and there's nothing special about the root one, that's just the task you choose to start with.

Menu Definitions
----------------

We'll use YAML syntax here, but you can also build dictionaries directly (YAML is more concise, and easier to edit than
a Python dict). Firstly the most simple definition - a single menu which will give the user the option to launch one of
two tasks:

.. code-block:: yaml

    - name: top_menu
      title: Main Menu
      items:
        - title: First task
          task: task_a
        - title: Second task
          task: task_b

For those not familiar with YAML, this is a single item list. That item is a dictionary, with keys 'name', 'title', and
'items'. 'items' is a list of dictionaries with keys 'title' and 'task' (in this case). Hopefully it should be possible
to follow what's happening!

There's a single menu defined here. It's called 'top_menu', and should display 'Main Menu' in some form when active. It
has two possible options, 'First task' and 'Second task', which will launch 'task_a' and 'task_b' respectively when
selected. When passed in to :func:`~approxeng.task.menu.register_menu_tasks_from_yaml` this will register a single task
called 'top_menu', this can then be launched like any other task.

Multiple Menus
**************

You can specify multiple menus in a single file, just add more items to the top level list:

.. code-block:: yaml

    - name: top_menu
      title: Main Menu
      items:
        - title: First task
          task: task_a
        - title: Go to submenu
          task: sub_menu
    - name: sub_menu
      title: Sub Menu
      items:
        - title: Back
          task: top_menu
        - title: Do a thing
          task: task_c
        - title: Do another thing
          task: task_d

This defines two menus, and also provides navigation between them. There's nothing special about menus, they just turn
into named tasks so in this case the item 'Go to a submenu' activates a task called 'sub_menu', and the second menu in
this YAML definition creates a task called 'sub_menu', which in turn has an item 'Back' which activates the 'top_menu'
task. So we have a nested menu structure, but it's a bit clunky.

More Concise Nested Menus
*************************

The example above is a bit verbose, it creates an item which calls a menu task, then creates a menu task which has an
item that calls the top menu task etc. This is sufficiently common that the library has a special syntax to handle it.
The following will produce the same menu structure as the previous example, but with two differences:

    1. It's a much shorter definition.
    2. The sub-menu task will have a name (all tasks do) but you haven't explicitly defined it. That means you
       can't manually activate that sub-menu. Not an issue here, if you need to do this use the form shown above.

.. code-block:: yaml

    - name: top_menu
      title: Main Menu
      items:
        - title: First task
          task: task_a
        - menu:
              title: Sub Menu
              items:
                - title: Do a thing
                  task: task_c
                - title: Do another thing
                  task: task_d

With a nested definition like this you don't have to define the 'back' task, as the menu system knows what the parent
menu is and handles it with a special 'up' action.


Implementing a MenuTask
-----------------------

To connect the menu system to your control and display resources you'll need to create a new subclass of
:class:`~approxeng.task.menu.MenuTask`, implementing two methods:

.. autoclass:: approxeng.task.menu.MenuTask
    :members: get_menu_action, display_menu
    :noindex:

As an example, let's suppose we're using approxeng.input as the input library, and that we've put the controller object
into the world as a resource called joystick. The implementation of the
:meth:`~approxeng.task.menu.MenuTask.get_menu_action`  might look like this:

.. code-block:: python

    from approxeng.task.menu import MenuClass, MenuAction

    class MyMenuClass(MenuClass):

        def get_menu_action(world):

            # Get any buttons pressed since last check
            buttons_pressed = world.joystick.presses

            if 'dleft' in buttons_pressed:
                return MenuAction.previous
            elif 'dright' in buttons_pressed:
                return MenuAction.next
            elif 'dup' in buttons_pressed:
                return MenuAction.up
            elif 'cross' in buttons_pressed:
                return MenuAction.select

This implementation gets the controller object from the world, then gets a button presses object representing any new
button presses. It then checks in turn for the d-pad left, right, and up buttons, and for the cross button. And that's
all you need to do for navigation.

Next suppose we have a display module attached, it's a simple object with a couple of methods used to set the two lines
of text. We register it as a resource called 'display' and use it to implement
:meth:`~approxeng.task.menu.MenuTask.display_menu` in our new class to finish it:

.. code-block:: python

    from approxeng.task.menu import MenuClass, MenuAction

    class MyMenuClass(MenuClass):

        def get_menu_action(self, world):

            # Get any buttons pressed since last check
            buttons_pressed = world.joystick.presses

            if 'dleft' in buttons_pressed:
                return MenuAction.previous
            elif 'dright' in buttons_pressed:
                return MenuAction.next
            elif 'dup' in buttons_pressed:
                return MenuAction.up
            elif 'cross' in buttons_pressed:
                return MenuAction.select

        def display_menu(self, world, title, item_title, item_index, item_count):

            # Get the display
            display = world.display

            display.set_line_1(title+' '+(item_index+1)+'/'+item_count)
            display.set_line_2(item_title)

This will show the menu title, along with an indication of the number of items on the first line of the display, and the
current selected item on the second line. We can navigate through the items within a menu using the left and right d-pad
buttons, select on by pressing the cross button, or go up in the menu structure (if there's a parent menu) by pressing
the d-pad up button.

Registering Menu Tasks
----------------------

Now we have a menu definition, along with a mechanism to display and navigate it, we just have to build the
corresponding tasks and register them. In this example we're going to use a YAML file, but you could also pass in the
dictionary of menus directly, the structure is exactly the same in both cases.

.. code-block:: python

    from approxeng.task.menu import register_menu_tasks_from_yaml
    from approxeng.task import run

    class MyMenuClass(MenuClass)
        # Class you created in the previous stage

    register_menu_tasks_from_yaml(filename='menu_definition.yml',
                                  menu_task_class=MyMenuClass,
                                  resources=['joystick','display'])

    run(root_task='top_menu')

This loads in the definition from the file, creates tasks for each menu, configures the menu system to use the menu
class you defined, and to make the 'joystick' and 'display' resources available to those tasks when running. It then
runs the task called 'top_menu', which is the task for the menu with the same name in that file.

Note - you don't ever construct an instance of your menu class, the library does that for you. Just pass in the actual
class (so no brackets!).

