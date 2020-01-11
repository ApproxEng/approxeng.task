from approxeng.task import task, TASKS, resource, RESOURCES, register_resource, run, TaskException
import logging
import cachetools.func
from time import sleep

LOG = logging.getLogger('demo')

#logging.basicConfig(level=logging.INFO)


@resource(name='list_resource')
def bar():
    return ['a', 'b', 'c']


register_resource('string_resource', 'a value')


@task(name='first_task')
def root(list_resource, task_count):
    sleep(0.1)
    LOG.info(task_count)
    LOG.info(list_resource)
    if task_count > 2:
        return 'second_task'


@task
def second_task(string_resource):
    LOG.info('Ooh, a string "%s", too exciting, sleeping for a bit', string_resource)
    # LOG.info(world._dict)
    sleep(0.5)
    raise Exception("foo")


LOG.info(TASKS)
LOG.info(RESOURCES)

run(root_task='first_task', raise_exceptions=False)
