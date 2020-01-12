from approxeng.input.selectbinder import ControllerResource
from time import sleep
from approxeng.task import task, run, register_resource
from approxeng.task.menu import register_menu_tasks_from_yaml, MenuTask, MenuAction
from redboard import RedBoard, Display


class MenuControllerTask(MenuTask):
    """
    Use a connected gamepad as menu navigation, write out menus to the redboard's display module
    """

    def get_menu_action(self, world):
        if 'dleft' in world.joystick.presses:
            return MenuAction.previous
        if 'dright' in world.joystick.presses:
            return MenuAction.next
        if 'cross' in world.joystick.presses:
            return MenuAction.select
        if 'dup' in world.joystick.presses:
            return MenuAction.up

    def display_menu(self, world, title, item_title, item_index, item_count):
        pass


# Redboard motor object as 'motors'
register_resource('motors', RedBoard())
# Menu tasks from the yaml file
register_menu_tasks_from_yaml(filename='robot_menu.yaml', menu_task_class=MenuControllerTask,
                              resources=['joystick', 'display'])

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
