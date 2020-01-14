from approxeng.task.menu import register_menu_tasks_from_yaml, KeyboardMenuTask
from approxeng.task import run
import logging

# Create a logger
LOG = logging.getLogger('demo')

# Set logging to INFO level - this means you'll see logs from the task library itself
logging.basicConfig(level=logging.INFO)

# Create a bunch of tasks automatically from the menu_demo.yml file, returns the list of all new tasks.
# We specify here that it should use the built-in menu task class KeyboardMenuTask, this uses the console
# to print out the list of available options and lets you navigate by keyboard. It's possible to implement
# your own custom classes to handle display and navigation of the menu system, for example with a controller
# and built-in OLED display in your robot.
new_tasks = register_menu_tasks_from_yaml(filename='menu_demo.yml',
                                          menu_task_class=KeyboardMenuTask)

# Call the run(..) function, passing it the first task name from the above call. This will always be the
# name of the first menu in the YAML file. When run(..) returns it will return any values that were
# defined in {'title', 'return'} pairs in that file, in this case either the string 'some_string' or the
# int 1
LOG.info('Returned value {} from run function'.format(run(root_task=new_tasks[0])))
