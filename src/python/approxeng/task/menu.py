import uuid
import copy
import logging
import yaml
from approxeng.task import register_task, Task
from enum import Enum, unique
from abc import abstractmethod

LOG = logging.getLogger('approxeng.task.menu')


@unique
class MenuAction(Enum):
    select = 1
    next = 2
    previous = 3
    up = 4


class MenuTask(Task):
    """
    A single menu, consisting of a title and a set of items, each of which will launch a
    task when selected. Optionally menus may have a parent.
    """

    def __init__(self, name, title, parent_task, resources=None):
        super(MenuTask, self).__init__(name, resources)
        self.name = name
        self.title = title
        self.parent_task = parent_task
        self.item_index = 0
        self.items = []
        # True if the display should be updated
        self.display_update = True
        LOG.debug('Created menu task %s with title "%s"', self.name, self.title)

    def add_item(self, title, task_name):
        LOG.debug('Adding "%s"->%s to menu task %s', title, task_name, self.name)
        self.items.append({'title': title, 'task': task_name})

    def startup(self):
        """
        :internal:
        :return:
        """
        self.item_index = 0
        self.display_update = True

    def shutdown(self):
        pass

    def tick(self, world):
        action = self.get_menu_action(world)
        if action is not None:
            if action is MenuAction.next:
                LOG.debug('Menu action = next')
                self.item_index = (self.item_index + 1) % (len(self.items) - 1)
                self.display_update = True
            elif action is MenuAction.previous:
                LOG.debug('Menu action = previous')
                self.item_index = (self.item_index - 1) % (len(self.items) - 1)
                self.display_update = True
            elif action is MenuAction.select:
                LOG.debug('Menu action = select')
                return self.items[self.item_index]['task']
            elif action is MenuAction.up and self.parent_task is not None:
                LOG.debug('Menu action = up')
                return self.parent_task
            elif isinstance(action, int):
                LOG.debug('Menu action = select index %i', action)
                if 0 <= action < len(self.items):
                    return self.items[action]['task']
        if self.display_update:
            LOG.debug('Menu, updating display')
            self.display_menu(world=world, title=self.title, item_title=self.items[self.item_index]['title'],
                              item_index=self.item_index, item_count=len(self.items))
            self.display_update = False

    @abstractmethod
    def get_menu_action(self, world):
        """
        Get the action, if any, to take on this menu item.

        :param world:
            Provides any resources needed to read the appropriate action
        :return:
            None for no action, or an instance of :class:`~approxeng.task.menu.MenuAction` for navigation, or an int to
            immediately select that index item.
        """
        pass

    @abstractmethod
    def display_menu(self, world, title, item_title, item_index, item_count):
        """
        Display the current menu state

        :param world:
            Provides any resources needed to display the menu
        :param title:
            Title for the current menu
        :param item_title:
            Title for the currently selected item
        :param item_index:
            Index of the currently selected item
        :param item_count:
            Number of available items
        """
        pass


class KeyboardMenuTask(MenuTask):
    """
    Not particularly clever implementation of :class:`~approxeng.task.menu.MenuTask` that uses print statements and
    ``input()`` to get menu choices. Has the advantage of working with no additional resources, so handy for testing.
    """

    def get_menu_action(self, world):
        """
        Print the menu, then prompt the user to select an index or, if parent is defined, ``u`` to to up.
        """
        print(self.title)
        print('=' * len(self.title))
        for index, item in enumerate(self.items):
            print('{}: {}'.format(index, item['title']))
        if self.parent_task is None:
            value = input('\nSelect an item...')
        else:
            value = input('\nSelect an item, or "u" for up...')
        try:
            return int(value)
        except ValueError:
            if value == 'u' and self.parent_task is not None:
                return MenuAction.up

    def display_menu(self, world, title, item_title, item_index, item_count):
        """
        Don't display here, because we block on input so if we did this *properly* we'd end up waiting for the user
        to enter a response before then showing them the options. While this *is* amusing, it's probably not helpful.
        """
        pass


def register_menu_tasks_from_yaml(filename, menu_task_class=MenuTask, resources=None):
    """

    :param filename:
    :param menu_task_class:
    :param resources:
    :return:
    """
    with open(filename, 'r') as stream:
        try:
            menu_dict = yaml.safe_load(stream)
            return register_menu_tasks(menu_dict=menu_dict, menu_task_class=menu_task_class, resources=resources)
        except yaml.YAMLError as exc:
            LOG.error('Unable to load YAML from %s', filename, exc_info=True)


def register_menu_tasks(menu_dict, menu_task_class=MenuTask, resources=None):
    """

    :param menu_dict:
    :param menu_task_class:
    :param resources:
    :return:
    """
    menus = copy.deepcopy(menu_dict)
    all_task_names = []
    for menu in menus:
        # Internal name for the menu task
        name = menu['name']
        # Display name for the menu
        title = menu['title']
        # If this was a nested menu this is the name of the parent menu task, None otherwise
        parent = None
        if 'parent_task' in menu:
            parent = menu['parent_task']

        print(f'{name}:"{title}"')
        task = menu_task_class(name=name, title=title, parent_task=parent, resources=resources)
        all_task_names.append(name)
        for item in menu['items']:
            if 'menu' in item:
                # Nested menu, expand it out
                new_task_id = 'menu_task_' + uuid.uuid1().hex
                sub_menu_dict = item['menu']
                sub_menu_dict['name'] = new_task_id
                sub_menu_dict['parent_task'] = name
                item.clear()
                item['title'] = sub_menu_dict['title']
                item['task'] = new_task_id
                menus.append(sub_menu_dict)
            if 'title' in item and 'task' in item:
                # Titled task item, add it to the menu
                task.add_item(title=item['title'], task_name=item['task'])
        register_task(name=name, value=task)
    return all_task_names
