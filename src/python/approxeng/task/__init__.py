import logging
from abc import ABC, abstractmethod
import inspect
import types

TASKS = {}
RESOURCES = {}

LOG = logging.getLogger('approxeng.task')


def task(_func=None, *, name=None):
    """
    Decorator to indicate that a function is a simple task. The function will be registered, using either the
    name if explicitly provided, or the name of the function otherwise.
    """
    if _func is not None:
        # Called with no name argument
        register_task(name=_func.__name__, value=_func)
        return _func
    else:
        # Called with an explicit argument, use this to register it
        def decorator(func):
            task_name = name if name is not None else func.__name__
            register_task(name=task_name, value=func)
            return func

        return decorator


def resource(_func=None, *, name=None):
    """
    Decorator to indicate that a function produces a resource. If the resource is a static value you should probably
    use the register_resource instead.
    """
    if _func is not None:
        # Called with no name argument
        register_resource(_func.__name__, _func)
        return _func
    else:
        # Called with an explicit name argument, use this to register it
        def decorator(func):
            register_resource(name, func)
            return func

        return decorator


class TaskException(Exception):
    pass


class Task(ABC):
    """
    Abstract base class for tasks, things which are called repeatedly to perform some higher function.
    """

    global_count = 0

    class World:
        """
        The world that the task tick sees, consists of all resources the task said it needed.
        """

        def __init__(self, resources, global_count, task_count):
            self.dict = {task_resource: RESOURCES[task_resource].value() for task_resource in resources}
            self.dict['global_count'] = global_count
            self.dict['task_count'] = task_count

        def __getitem__(self, item):
            if isinstance(item, tuple):
                return [self.__getattr__(single_item) for single_item in item]
            return self.__getattr__(item)

        def __getattr__(self, item: str):
            if item in self.dict:
                return self.dict[item]
            raise AttributeError

        def __contains__(self, item):
            return item in self.dict

    def __init__(self, name, resources=None):
        """
        Create a new task

        :param name:
            Name used internally by this task
        :param resources:
            A string, or list of strings, containing names of resources which must be available for this task to
            function. Any such resources will be initialised and shutdown alongside the task itself. If this is
            set to None then all resources registered will be available, otherwise only those explicitly named here
            will be accessible from the task logic.
        """
        self._resources = resources
        if resources is not None and not isinstance(resources, list):
            self._resources = [resources]
        self.active = False
        self.name = name
        self.task_count = 0

    @property
    def resources(self):
        """
        A list of names of resources needed by this task, if this was originally set to None then this returns a list
        containing all the registered resource names.
        """
        if self._resources is None:
            return [task_resource for task_resource in RESOURCES]
        return self._resources

    def do_startup(self):
        """
        If this task is not currently active, call startup on any required resources, then call startup on the task
        implementation. No need to call this explicitly as it's called if the task isn't active on the first tick.
        """
        if self.active:
            LOG.warning('Task "%s" startup called but task already active', self.name)
        else:
            LOG.info('Task "%s" starting', self.name)
            for task_resource in self.resources:
                if task_resource not in RESOURCES:
                    raise TaskException('Required resource "{}" not defined'.format(task_resource))
                RESOURCES[task_resource].startup()
            self.startup()
            self.active = True

    def do_shutdown(self):
        """
        If this task is active, shut it down, then call shutdown on all resources.
        """
        if self.active:
            LOG.info('Task "%s" shutting down', self.name)
            self.shutdown()
            for task_resource in self.resources:
                RESOURCES[task_resource].shutdown()
            self.active = False

    def do_tick(self):
        """
        Start up the task, if needed, then call the tick method, passing in the world and tick count.
        """
        if not self.active:
            self.do_startup()
        LOG.debug('Task "%s", task_tick %i, global_tick %i', self.name, self.task_count, Task.global_count)
        return_value = self.tick(
            world=Task.World(resources=self.resources, task_count=self.task_count, global_count=Task.global_count))
        Task.global_count = Task.global_count + 1
        self.task_count = self.task_count + 1
        return return_value

    @abstractmethod
    def startup(self):
        """
        Implement to provide startup logic for the task.
        """
        pass

    @abstractmethod
    def shutdown(self):
        """
        Implement to provide shutdown logic for the task.
        """
        pass

    @abstractmethod
    def tick(self, world):
        """
        Called every tick, do your stuff here!

        :param world:
            A world object, access any required resources through properties on this object.
        :return:
            Used to signal what to do at the end of the tick:
            None - continue, call the same task again
            True - exit from the task loop. Probably don't do this, instead...
            ...String or Task - shut this task down and set the specified task (name or direct reference) to be the
            active one. If you want to exit the best way to do so is to delegate to the exit task, or to a custom task
            which gracefully shuts down your hardware before exiting from the loop.
        """
        pass


class SimpleTask(Task):
    """
    Class that wraps a single task function, including basic state consisting of an initially blank dict that
    the task can safely write to and read from for the duration of the run.

    The function wrapped by the task can accept any or all of the following parameters:

    state : passed the state dict, persists across multiple calls within a task session.
    world : passed the world state, consisting of a set of named resources as requested by the task specification.
    count : monotonically ascending tick count across the entire application.
    """

    def __init__(self, task_function, name):
        """
        Create a new simple task instance, this is generally going to be called from within the library when wrapping
        a task function.

        :param task_function:
            A function, which may accept any or all of [state, world, count] parameters, and which will be called every
            tick while this task is active.
        :param resources:
            A list of named resources to be supplied through the world parameter to the task function.
        :param name:
            The name of the task, this is only really used internally for logging, the canonical name is defined by the
            key under which the task is registered.
        """

        resources = [key for key in inspect.signature(task_function).parameters.keys()]

        # task_state isn't a normal world resource, we'll explicitly add it later but we don't want the framework
        # to try to initialise it. Remove it from the list of resources if it's been specified and make a note that
        # we did so so we know to add it back in later
        if 'task_state' in resources:
            resources.remove('task_state')
            self.uses_state = True
        else:
            self.uses_state = False

        # The world always contains task_count and global_count, but we may not want it to. Remember whether these are
        # used for later.
        self.use_task_count = 'task_count' in resources
        self.use_global_count = 'global_count' in resources

        if self.use_task_count:
            resources.remove('task_count')
        if self.use_global_count:
            resources.remove('global_count')

        super(SimpleTask, self).__init__(resources=resources, name=name)
        self.task_function = task_function
        self.state = {}

    def startup(self):
        """
        Clear the state dict, this should never be needed but doesn't hurt to check
        """
        self.state.clear()

    def shutdown(self):
        """
        Clear the state dict
        """
        self.state.clear()

    def tick(self, world):
        """
        A single task tick. Calls the task function, supplying it with whatever parameters it needs.

        :param world:
            World state, set of resources accessible as properties.
        :return:
            The return value from the task function. As elsewhere, this is interpreted as follows:
            None - don't change anything, keep this task running, call it again
            True - exit from the task processing loop, shutting down the process
            Task or String - shut this task down, set the named or provided task as the current task
        """
        if self.uses_state:
            world.dict.update({'task_state': self.state})
        if not self.use_task_count:
            del world.dict['task_count']
        if not self.use_global_count:
            del world.dict['global_count']

        return self.task_function(**world.dict)


def register_task(name, value):
    """
    Explicitly register a task, either from a function or from an instance of Task

    :param name:
        Name used to reference the task
    :param value:
        Either a task function, in which case this behaves as if the function were annotated with @task, or a Task
        object. You may want to use the latter, more verbose, form if extensive setup or custom state handling is
        needed by your task, although in general most of such handling should be done with resources and tasks
        themselves should remain largely state free.
    """
    if isinstance(value, types.FunctionType):
        TASKS[name] = SimpleTask(name=name, task_function=value)
        LOG.info('Registered task function "%s", required resources: %s', name, TASKS[name].resources)
    elif isinstance(value, Task):
        TASKS[name] = value
        LOG.info('Registered task class "%s", required resources: %s', name, value.resources)


class Resource(ABC):
    """
    Abstract base class for resources, things which are used by tasks and which may have a lifecycle. When a new task
    is started, any resources the task requires are started. On each task tick the value method is called on each
    resource and is used to populate the world dict passed to the task function. When the task is shut down each
    resource has its shutdown function called.
    """

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def startup(self):
        """
        Called before the resource is used by any tasks which require it. It should never be called when already active,
        but code defensively here and check.
        """
        pass

    @abstractmethod
    def shutdown(self):
        """
        Called after a task which used this resource has finished. Also called if another resource is registered with
        the same name, or if the task loop exits. You must implement this to handle multiple calls sensibly, i.e. check
        that you haven't already tidied up, don't assume this will only be called after the resource has been started.
        """
        pass

    @abstractmethod
    def value(self):
        """
        Get the value of the resource. The result of this will be passed to any tasks through the world object, or to
        any task functions requesting the resource through a named parameter.
        """
        pass


class SimpleResource(Resource):
    """
    Simple resource constructed with value, and optional setup / teardown functions. All these functions should be
    no-argument ones.
    """

    def __init__(self, name, value_func, startup_func=None, shutdown_func=None):
        super(SimpleResource, self).__init__(name=name)
        self.value_func = value_func
        self.startup_func = startup_func
        self.shutdown_func = shutdown_func

    def startup(self):
        if self.startup_func is not None:
            self.startup_func()

    def shutdown(self):
        if self.shutdown_func is not None:
            self.shutdown_func()

    def value(self):
        return self.value_func()


def register_resource(name, value):
    """
    Explicitly register a value as a resource. If the value is a function then wrap it up as the value() method of a
    resource class instance. If it is already a resource class instance just register it. If it's a plain static value
    then wrap it in a function that always returns that value, then wrap that up in the simple class.
    """
    if name in RESOURCES:
        # If this resource was already defined we're going to overwrite it, so shut the existing one down first
        RESOURCES[name].shutdown()
    if isinstance(value, types.FunctionType):
        RESOURCES[name] = SimpleResource(name=name, value_func=value)
        LOG.info('Registered resource function "%s"', name)
    elif isinstance(value, Resource):
        RESOURCES[name] = value
        LOG.info('Registered resource class "%s"', name)
    else:
        def resource_function():
            return value

        RESOURCES[name] = SimpleResource(name=name, value_func=resource_function)
        LOG.info('Registered resource value "%s"', name)


@task(name='exit')
def exit_task(error=None):
    """
    Exit the loop. If there was an exception raised causing this task to run then wrap the exception in the TaskStop,
    otherwise it'll be empty.
    """
    return TaskStop(error)


class TaskStop:
    """
    Wraps a single value, defaulting to None. If a task returns an instance of this class, the task loop will exit and
    the return value of the run() function will be the wrapped value. This allows tasks to exit the loop and pass
    information to the caller as they do so.
    """

    def __init__(self, return_value=None):
        self.return_value = return_value


def run(root_task, error_task='exit', check_tasks=None, raise_exceptions=False):
    """
    Run the task loop!

    :param root_task:
        The first task to start with
    :param error_task:
        The task to switch to if an exception occurs, defaults to the ExitTask to exit the loop. If you have hardware
        such as motors that you need to ensure is deactivated, the best approach is to have a task that only does
        hardware shutdown, handles any errors with that process internally, and then delegates to the exit task to
        stop the task look. Defaults to the exit task if not specified.
    :param check_tasks:
        A sequence of functions which will be called before each tick of the selected task. If any of them return
        then the return value is used instead of calling and using the value of the task's tick. This can be done
        to handle cases like 'make the home button always jump back to the root task', or 'exit the task loop on
        low battery conditions' or similar. Don't put too much logic here, it'll get called every tick. Also good for
        cases where you absolutely want to bail if hardware isn't available (joystick out of range is a particular case)
    :param raise_exceptions:
        Defaults to False, if set to True then any exceptions raised by a task will be handled, then wrapped in a
        TaskException and raised from this call. If False then they will be handled, and control passed to the
        designated error task.
    :returns:
        If the loop exits as the result of a task returning a :class:`~approxeng.task.TaskStop` it will return the
        value wrapped by that instance, otherwise None.
    """

    def get_task(t):
        """
        Resolve a task instance

        :param t:
            Either a name, or a Task object
        :return:
            The task object, if supplied, or the result of a lookup in the TASKS global otherwise
        """
        if isinstance(t, Task):
            return t
        return TASKS[t]

    # Start with the root task as the active one
    active_task = get_task(root_task)
    # Initialise count to 0
    # Loop until we're done
    finished = False
    return_value = None
    try:
        while not finished:
            try:
                response = None
                # If we have any pre-task checks to run do them now. If any of those functions return
                # non-None values we'll use those in place of the active task. Code these carefully!
                # Here's where you'd check for e.g. joystick not connected.
                if check_tasks is not None:
                    for check_task in check_tasks:
                        check_response = check_task()
                        if check_response is not None:
                            response = check_response
                # If no check_task functions returned anything, run the actual task tick
                if response is None:
                    response = active_task.do_tick()
                # If the tick function returned a value it means we need to switch control
                if response is not None:
                    if isinstance(response, Task) or isinstance(response, str):
                        # New task, either name or Task object. Shut down and switch to it for the next tick
                        active_task.do_shutdown()
                        active_task = get_task(response)
                    elif isinstance(response, TaskStop):
                        # TaskStop value returned
                        active_task.do_shutdown()
                        finished = True
                        return_value = response.return_value
            except Exception as e:
                # Anything throwing an exception ends up here. Log it first, then delegate to a handler task
                LOG.exception('Exception raised within task look')
                # Shut the active task down, add the exception to the world as 'error' and launch the error task
                active_task.do_shutdown()
                if raise_exceptions:
                    raise TaskException from e
                register_resource('error', e)
                active_task = get_task(error_task)
    except TaskException as te:
        # Catch and stash the exception in the return value
        return_value = te
    finally:
        # Finished, shut down all resources and exit
        for res in RESOURCES:
            RESOURCES[res].shutdown()
    # If we're raising exceptions, and there was an exception, raise it.
    if raise_exceptions and isinstance(return_value, Exception):
        raise return_value
    # Otherwise return the return value and exit.
    return return_value

