
class Caller():
    """ An object were callbacks can be registered and called. Same `Caller` class from
    `cflib.utils.callbacks`"""

    def __init__(self):
        """ Create the object """
        self.callbacks = []

    def add_callback(self, cb):
        """ Register cb as a new callback. Will not register duplicates. """
        if ((cb in self.callbacks) is False):
            self.callbacks.append(cb)

    def remove_callback(self, cb):
        """ Un-register cb from the callbacks """
        self.callbacks.remove(cb)

    def call(self, *args):
        """ Call the callbacks registered with the arguments args """
        copy_of_callbacks = list(self.callbacks)
        for cb in copy_of_callbacks:
            cb(*args)


class VariableCallback:
    """Special variable contain the value and the callback. Must use the `get` and `set`"""

    def __init__(self, value):
        self._value = value
        self.callbacks = Caller()

    def set(self, value):
        """Setting the value and call the callback with the new value

        Args:
            value : new value to set
        """
        self._value = value
        self.callbacks.call(value)

    def get(self):
        """Get the value"""
        return self._value

    def __getstate__(self):
        return self._value