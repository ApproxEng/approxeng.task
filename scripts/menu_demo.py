from approxeng.task.menu import register_menu_tasks_from_yaml, KeyboardMenuTask
from approxeng.task import run
import logging

LOG = logging.getLogger('demo')

logging.basicConfig(level=logging.INFO)

new_tasks = register_menu_tasks_from_yaml(filename='menu_demo.yml',
                                          menu_task_class=KeyboardMenuTask)
LOG.info('Returned value {} from run function'.format(run(root_task=new_tasks[0])))
