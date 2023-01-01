import unittest
from map.path import Path, Position

class TestPath(unittest.TestCase):
    def test_something(self):
        path = Path('test', [Position(0.6,1.5,0.4), Position(0.6,7.1,0.4)])
        locations = [
            Position(x=0.71, y=2.5, z=0.4),
            Position(x=2.14, y=2.58, z=0.4),
            Position(x=2.24, y=5.27, z=0.39),
            Position(x=63 / 100, y=267 / 50, z=0.39)
        ]
        expected = [
            Position(0.6,1.5,0.4),
            Position(0.6,2.4,0.4),
            Position(2.14,2.4,0.4),
            Position(2.14,5.27,0.4),
            Position(0.6,5.27,0.4),
            Position(0.6,7.1,0.4)
        ]

        path.get_next_position()
        path.add_positions_to_current(locations)

        for x,y in zip(path._positions, expected):
            self.assertEqual(x, y)
if __name__ == '__main__':
    unittest.main()
