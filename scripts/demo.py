from approxeng.task import task, TASKS, resource, RESOURCES, register_resource, run
import logging
import cachetools.func
from time import sleep

LOG = logging.getLogger('demo')

logging.basicConfig(level=logging.INFO)


@resource(name='list')
def bar():
    return ['a', 'b', 'c']


register_resource('string', 'a value')


@task(name='first_task', resources='list')
def root(world, count, state):
    sleep(0.1)
    LOG.info(count)
    LOG.info(world.list)
    if count > 2:
        return 'second_task'


@task(resources=['string'])
def second_task(world):
    LOG.info('Ooh, a string "%s", too exciting, sleeping for a bit', world.string)
    LOG.info(world._dict)
    sleep(0.5)
    raise Exception("foo")



LOG.info(TASKS)
LOG.info(RESOURCES)

run(root_task='first_task')
