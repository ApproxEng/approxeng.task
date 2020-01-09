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
name, which is used to retrieve them in a task. In this case we've called the motor class 'motors' (this could be the
object returned from initialising an explorer HAT, or any other motor driver, or it could be something you've written
yourself, the task framework doesn't care!)

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
'light_sensor' but you can also explicitly name it:

.. code-block:: python

    from approxeng.task import resource

    @resource(name='lux')
    def light_sensor():
        # Call your library functions to read the ambient light sensor (for example)
        sensor_reading = ....
        # And return it. This function will be called every time the task is polled, and the
        # result will be made available to the task
        return sensor_reading

This will make the sensor reading available under the 'lux' property to tasks which use it.

Advanced Resources
******************

Some resources may require more extensive setup than allowed by the examples above. For these you can create your own
implementation of the :class:`~approxeng.task.Resource` class, and register it through the register_resource call.
Implementing this class allows you to access startup and shutdown methods which will be called automatically when a task
starts and stops using the resource.

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

This code does two things. Firstly we define a task - in this case this is just a function which prints 'Task running'
and sleeps for a second. Not terribly exciting! It is, however, a fully functional task. Note the @task decorator - this
tells the framework that it's a task, and, just like the resources, it has a default name which is the same as the
function.

Secondly, we run the task. The root task is the first task to run (tasks can switch to other tasks, we'll look at that
next). Because there's no logic here to switch tasks or to exit, this will run forever and print 'Task running' every
second. It also doesn't use any resource, so it's not a great example but you have to start somewhere. Let's fix that.

.. code-block:: python

    from approxeng.task import task, resource, run
    import time

    @resource(name='lux')
    def read_light_sensor():
        sensor_reading = ...
        return sensor_reading

    @task(name='light_monitor')
    def light_monitoring_task(world):
        light_reading = world.lux
        print('Light reading is {}'.format(light_reading))
        sleep(1)

    run(root_task='light_monitor')

This code is very similar to the previous example, but we've also defined a resource. By doing this, and then adding the
'world' parameter to our task function, we've told the framework a few things:

    1. There's a resource, called 'lux', that reads the light sensor when called.
    2. We want access to the world - a special object that provides all resources to a task
    3. Each time the task is called, we want to have up-to-date values for each of the resources

Sometimes reading sensors can be time consuming. There are a few ways to make this easier, you could have the resource
cache its value and only actually update from the hardware at a certain interval, but the most obvious saving is not to
even use resources we don't actually need. Suppose the robot has a bunch of different sensors, it might have a compass,
light meter, wheel encoders, rangefinders etc. If a task doesn't need the rangefinder we should be able to just ignore
it rather than waste time reading from it. You can do this by adding a 'resources' property to the task annotation.

.. code-block:: python

    from approxeng.task import task, resource, run
    import time

    @resource(name='expensive_sensor')
    def read_the_expensive_sensor
        # This takes aaaaages...
        # ...

    @resource(name='lux')
    def read_light_sensor():
        sensor_reading = ...
        return sensor_reading

    @task(name='light_monitor', resources=['lux'])
    def light_monitoring_task(world):
        light_reading = world.lux
        print('Light reading is {}'.format(light_reading))
        sleep(1)

    run(root_task='light_monitor')

We've added a (fake) expensive sensor, we want to avoid reading this unless we need it! By setting 'resources=['lux']'
on the task we're telling the framework that the world only needs to contain the lux resource, and not the
expensive_sensor one. This means when this task is running we never touch the expensive sensor.

By default, if you don't specify a list of needed resources, all available ones are used. Be careful you're not wasting
your robot's time with something it doesn't need!

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
    @task(name='light_monitor', resources=['lux'])
    def light_monitoring_task(world):
        light_reading = world.lux
        if light_reading > 9000:
            return 'run_away'
        sleep(1)

    @task(name='run_away', resources=['lux','motors'])
    def run_away_and_hide(world)
        # Fire up the motors and get out of here!
        world.motors.go_really_fast()
        light_reading = world.lux
        if light_reading < 1000:
            # Ah, soothing darkness
            return 'light_monitor'
        sleep(1)

    run(root_task='light_monitor')

If your task function returns a value, it indicates that it wants to stop that task and do something else. Exactly what
that something else is depends on what you return.

    * If you return True, the run command will finish, no more tasks will be run.
    * If you return a String matching the name of another task, that task becomes the current one.

So in this case, the light_monitor waits for the light to get really bright, then switches control to the 'run_away'
task, which in turn waits for the light to get nice and dim and hands back control to the monitor.

