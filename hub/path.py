from general.utils import Position

class Path:
    """Path class to contain a list of points for the drone to fly to
    """
    def __init__(self):
        self._points = []
        self._current = 0
        
    def add_points(self, point: Position):
        if not isinstance(point, Position):
            raise TypeError('point must be Position')
        self._points.append(point)
        
    def get_next_position(self) -> Position| None:
        """ Get the next point in the path. If there is no next point, `None` is returned. 
        """
        if self._current >= len(self._points):
            return None
        point = self._points[self._current]
        self._current += 1
        return point
    
    def is_empty(self) -> bool:
        return len(self._points) == 0
    
    def reset(self):
        self._current = 0



if __name__ == '__main__':
    p = Path()
    p.add_points(Position(1, 1, 1))
    p.add_points(Position(2, 2, 2))
    print(p.get_next_position())
    print(p.get_next_position())
    print(p.get_next_position())
    p.reset()
    print(p.get_next_position())