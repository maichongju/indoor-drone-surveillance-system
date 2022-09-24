from copy import deepcopy
from statistics import mean

class List:
    """A special list that have a maximum size. If the list is full, the oldest
    value will be removed when a new value is added. The max size can not be changed
    during the lifetime of the list.
    """
    def __init__(self, max_size: int = -1):
        self._max_size = max_size if max_size > 0 else -1
        self._data = []
        
        
    def append(self, item):
        """Append an item to the list
        """
        self._data.append(item)
        if self._max_size > 0 and len(self._data) > self._max_size:
            self._data.pop(0)
        
    def pop(self, index: int):
        """Remove the item at the given index
        """
        return self._data.pop(index)
    
    def to_list(self) -> list:
        """Return a python list of the data.
        """
        return deepcopy(self._data)
    
    def sum(self):
        return sum(self._data)
    
    def avg(self):
        if self.is_empty:
            return 0
        return mean(self._data)
    
    def clear(self):
        self._data = []
        
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, List):
            return False
        return self._data == __o._data
        
    def __str__(self):
        return str(self._data)
    
    def __len__(self):
        return len(self._data)
        
    def __iter__(self):
        """Enable iteration over the list
        """
        return iter(self._data)
    
    def __getitem__(self, index: int):
        """Get the item at the given index
        """
        return self._data[index]
    
    @property
    def max_size(self) -> int:
        """The maximum size of the list. `-1` means no limit.
        """
        return self._max_size
    
    @property
    def is_empty(self) -> bool:
        """Return True if the list is empty.
        """
        return len(self._data) == 0