.. _simple_api:

Simple Usage
============

This library helps you break down your robot code into two things: Tasks, and Resources.

    * Tasks are things your robot does, examples might be manual control, following a line, that kind of thing.
      They are the intelligence behind your robot.
    * Resources are things your robot has, such as motors, sensors, connections to a game controller, flashing lights.
      In this library, more specifically, resources are software representations of those (normally physical) things.
      Tasks use resources to do stuff.

Defining Resources
------------------

Resources can vary, from simple things that never change (such as access to a motor driver board), to complex chains of
processes such as an entire image processing pipeline running across multiple cores or CPUs.

Constant Resources
******************

This is the simplest kind of resource, it never changes but we want to give tasks access to it. All resources have a
name, which is used to retrieve them in a task. In this case we've called the motor resource ``motors`` (this could be
the object returned from initialising an explorer HAT, or any other motor driver, or it could be something you've
written yourself, the task framework doesn't care!)

.. code-block:: python

    from approxeng.task import register_resource

    # Create the motor board object, this will depend on the hardware
    # fitted to your robot.
    motor_board = ...

    # Tell the task framework about it, give it a name.
    register_resource(name='motors', value=motor_board)


Variable Resources
******************

Resources like sensors could be provided in the same way, but then each of your tasks would have to make the calls to
read your sensor data, and the aim of this library is to separate out the intelligence (tasks) and access to hardware
(resources). To make this easier, resources can also be functions - in this case the value passed to each call to the
task is the result of the function:

.. code-block:: python

    from approxeng.task import resource

    @resource
    def light_sensor():
        # Call your library functions to read the ambient light sensor (for example)
        sensor_reading = ....
        # And return it. This function will be called every time the task is polled, and the
        # result will be made available to the task
        return sensor_reading

In this case we didn't provide a name - by default the resource will have the name of the function, so in this case
``light_sensor`` but you can also explicitly name it:

.. code-block:: python

    from approxeng.task import resource

    @resource(name='lux')
    def light_sensor():
        # Call your library functions to read the ambient light sensor (for example)
        sensor_reading = ....
        # And return it. This function will be called every time the task is polled, and the
        # result will be made available to the task
        return sensor_reading

This will make the sensor reading available under the ``lux`` property to tasks which use it.

Resource Dependencies
*********************

If you need to have access to the value of a resource when computing the value of a second resource (for example, you
might have a resource that does some processing on a camera image, but don't want to duplicate your camera frame grab
code) you can do so by registering a function with parameters - these parameters are read as the names of resources
which should be read before calling your resource function. Be aware that this allows you to create cyclical
dependencies which will throw an error the first time you attempt to use them!

.. code-block:: python

    from approxeng.task import resource

    @resource(name='simple_resource')
    def read_basic_sensor():
        #... read a simple sensor here

    @resource(name='complex_resource')
    def read_fused_sensor(simple_resource):
        #... read another sensor and fuse the two sensor readings together

    @task
    def some_task(complex_resource):
        #... use the fused sensor, basic sensor reading is supplied to the fused sensor then to this task

As the example above shows the library will automatically work out which resources it needs to initialise based on the
ones you declare in your task and any dependencies those resources themselves have.

Advanced Resources
******************

Some resources may require more extensive setup than allowed by the examples above. For these you can create your own
implementation of the :class:`approxeng.task.Resource` class, and register it through the
:func:`approxeng.task.register_resource` call. Implementing this class allows you to access startup and shutdown
methods which will be called automatically when a task starts and stops using the resource.

If any resources have dependencies, these are also used to calculate the startup and shutdown order, with resources
started up such that a resource's dependencies will always have startup called before that resource, and shutdown after
(this only applies if you're implementing your own subclasses of :class:`~approxeng.task.Resource` as no other methods
grant access to the startup and shutdown methods)

Defining Tasks
--------------

Now you've got some resources, time to do something with them! You do this by creating tasks, and, as with the
resources, there are various ways to do that depending on how much control you need over the lifecycle.

Simple Tasks
************

.. code-block:: python

    from approxeng.task import task, run
    import time

    @task
    def some_task():
        print('Task running')
        time.sleep(1)

    # Run the task
    run(root_task='some_task')

This code does two things. Firstly we define a task - in this case this is just a function which prints *Task running*
and sleeps for a second. Not terribly exciting! It is, however, a fully functional task. Note the
:func:`~approxeng.task.task` decorator on ``some_task``, it appears above as ``@task`` -
this tells the framework that it's a task, and, just like the resources, the registered task has a default name which is
the same as the name of the function.

Secondly, we run the task. The root task is the first task to run (tasks can switch to other tasks, we'll look at that
next). Because there's no logic here to switch tasks or to exit, this will run forever and print *Task running* every
second. It also doesn't use any resource, so it's not a great example but you have to start somewhere. Let's fix that.

.. code-block:: python

    from approxeng.task import task, resource, run
    import time

    @resource(name='lux')
    def read_light_sensor():
        sensor_reading = ...
        return sensor_reading

    @task(name='light_monitor')
    def light_monitoring_task(lux):
        print('Light reading is {}'.format(lux))
        sleep(1)

    run(root_task='light_monitor')

This code is very similar to the previous example, but the task function has a parameter ``lux``. If you specify one or
more parameters in your task function you're asking the library to make sure the resources with the same names as
those parameters are initialised when your task starts, shut down when it stops, and made available each time your task
is called.

In this case, the library will call your ``read_light_sensor()`` function and pass the result into the
``light_monitoring_task(lux)`` call.

Simple Stateful Tasks and Task Counts
*************************************

In addition to accessing resources through named parameters on your task function you also always have access to three
additional values:

    * ``task_count`` is an integer which starts at 0 when your task is started, and increments after each call.
    * ``global_count`` is an integer which starts at 0 when the library is loaded, and increments after each call.
    * ``task_state`` is a dict, initialised to be empty when your task is started and preserved across subsequent calls. You
      can use this if you need to carry state across multiple calls to your task. This is cleared when the task is shut
      down.

Switching Tasks
***************

The examples above all run forever, they have no way to control which task is running, handle failures etc. Suppose we
want a robot that waits until the light reaches a certain level, then runs away from it. We could do this with two
tasks, and control that switches between them as follows:

.. code-block:: python

    from approxeng.task import task, resource, run
    import time

    @resource(name='lux')
    def read_light_sensor():
        sensor_reading = ...
        return sensor_reading

    # Create the motor board object, this will depend on the hardware
    # fitted to your robot.
    motor_board = ...

    # Tell the task framework about it, give it a name.
    register_resource(name='motors', value=motor_board)

    # Task to wait for the light to get too bright
    @task(name='light_monitor')
    def light_monitoring_task(lux):
        if lux > 9000:
            return 'run_away'
        sleep(1)

    @task(name='run_away')
    def run_away_and_hide(motors, lux)
        # Fire up the motors and get out of here!
        motors.go_really_fast()
        if lux < 1000:
            # Ah, soothing darkness. Stop the motors and start monitoring
            motors.stop()
            return 'light_monitor'
        sleep(1)

    run(root_task='light_monitor')

If your task function returns a value, it indicates that it wants to stop that task and do something else. Exactly what
that something else is depends on what you return.

    * If you return a string matching the name of another task, that task becomes the current one.
    * If you return an instance of :class:`~approxeng.task.Task`, that task becomes the current one.
    * If you return an instance of :class:`~approxeng.task.TaskStop`, the loop exits. If the instance wraps a value
      the wrapped value will be returned by the :func:`~approxeng.task.run` function.

So in this case, the light_monitor waits for the light to get really bright, then switches control to the 'run_away'
task, which in turn waits for the light to get nice and dim and hands back control to the monitor.

Pre-task Functions
------------------

There might be some things you want to do before a task runs which are universal - they should always run no matter
what task is active. This could be used for a few things:

    * Setting up a resource to the correct state. For example, the ``approxeng.input`` controller instances should have
      their check_presses() method called before any task checks for button presses.
    * Adding universal fault handling, for example checking that a controller is still connected.
    * Adding universal behaviours, such as always shutting down motors and bouncing to the main menu if the user presses
      the home button on a connected controller.

To do this you can register any number of no-argument functions when you call the :func:`~approxeng.task.run` function.
The example below is from some code I wrote to drive a simple robot around, and shows a pre-task function that does
all the things listed above:

.. code-block:: python

    # Loop forever until a task exits for a reason other than disconnection
    while True:
        try:
            with ControllerResource() as joystick:

                # Tell the task system about the joystick
                register_resource('joystick', joystick)


                def check_joystick():
                    """
                    Called before every tick, sets up button presses, checks for joystick
                    disconnection, and bounces back to the home menu via a motor shutdown
                    task if the home button is pressed.
                    """
                    if not joystick.connected:
                        return TaskStop('disconnection')
                    joystick.check_presses()
                    if 'home' in joystick.presses:
                        return 'stop'


                # Run the task loop
                exit_reason = run(root_task='main_menu',
                                  error_task='stop',
                                  check_tasks=[check_joystick])

                # If we disconnected then wait for reconnection, otherwise break out
                # and exit the script.
                if exit_reason is not 'disconnection':
                    break

        except IOError:
            # Raised if there's no available controller, display this information
            display.text(line1='Simple Robot Script', line3='Waiting for Controller')
            sleep(1)

The ``check_tasks`` parameter of the :func:`~approxeng.task.run` function, if specified, takes an array of functions
which will be run in sequence immediately before the :meth:`~approxeng.task.Task.tick` is called on a
:class:`~approxeng.task.Task`. If any of these functions return a value, the actual task is skipped and the return value
is treated exactly the way it would have been treated if returned from the task. So, in the example above there are
three possible outcomes of the ``check_joystick`` function:

  * If the joystick is connected, and ``home`` hasn't been pressed, it doesn't return a value and the task will be run
    as normal.
  * If the joystick is not connected, it returns a :class:`~approxeng.task.TaskStop`, wrapping the string
    ``disconnection``. This causes the call to :func:`~approxeng.task.run` to complete and return that string, which is
    then handled to break out of the inner loop and go back to waiting for a joystick connection.
  * If the joystick is connected and ``home`` has been pressed, return the string ``stop``. This is treated as the name
    of a task, and will switch control to the ``stop`` task - in this case this should probably shut the motors down and
    then bounce back to the main menu, but the details aren't important here.