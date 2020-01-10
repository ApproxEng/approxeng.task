import logging
from approxeng.task.menu import register_menu_tasks_from_yaml, KeyboardMenuTask
from approxeng.task import run

logging.basicConfig(level=logging.INFO)

new_tasks = register_menu_tasks_from_yaml('menu_demo.yml', menu_task_class=KeyboardMenuTask)

if new_tasks:
    run(root_task=new_tasks[0])