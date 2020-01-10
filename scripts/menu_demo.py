from approxeng.task.menu import register_menu_tasks_from_yaml, KeyboardMenuTask
from approxeng.task import run

new_tasks = register_menu_tasks_from_yaml(filename='menu_demo.yml',
                                          menu_task_class=KeyboardMenuTask)
run(root_task=new_tasks[0])
