from approxeng.input.selectbinder import ControllerResource
from time import sleep
from approxeng.task import task, run, register_resource
from approxeng.task.menu import register_menu_tasks_from_yaml

register_menu_tasks_from_yaml(filename='robot_menu.yaml')

while True:
    try:
        with ControllerResource() as joystick:

            # Tell the task system about the joystick
            register_resource('joystick', joystick)


            def check_joystick():
                # Check whether the joystick is connected
                if not joystick.connected:
                    # Returning True from here exists the task loop
                    return True
                # Check for presses before calling the active task
                joystick.check_presses()
                # If home button pressed, jump to the main_menu task
                if 'home' in joystick.presses:
                    return 'main_menu'


            # Run the root task
            run(root_task='main_menu', check_tasks=[check_joystick])

    except IOError:
        # Joystick not found, sleep and try again
        sleep(1)
