.. _changelog-label:

Change Log
==========

Version 0.0.5
-------------

Resources can now have dependencies, and will be called with the values of any dependencies as part of the task tick.

Version 0.0.4
-------------

Cleaned up resource handling, tasks can now stop the loop and return a value to the caller through the
:class:`approxeng.task.TaskStop` class.

Version 0.0.3
-------------

Task functions now specify resources through parameter names rather than accessing the world object directly. So
instead of:

.. code-block:: python

    @task(resources=['lux'])
    check_light_level(world)
        light_level = world.lux

You can now do:

.. code-block:: python

    @task
    check_light_level(lux)

And the light level is passed directly to the task function without any need to reference the world object to get it.

Version 0.0.2
-------------

Added menu automation.

Version 0.0.1
-------------

Initial release.