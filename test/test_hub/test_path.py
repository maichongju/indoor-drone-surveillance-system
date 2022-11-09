from general.utils import Position
from hub.path import PathList, Path

FOLDER_PATH = 'path/'


def get_path(file_name):
    return FOLDER_PATH + file_name


class TestPath:
    pass


class TestPathList:

    def test_normal(self):
        with open(get_path('path.json'), 'r') as file:
            paths = PathList.load(file)
            assert paths.size == 2
            path1 = Path(name='test',
                         positions=[Position(0, 1, 1), Position(1, 1, 1), Position(1, 0, 1)],
                         connected=True)
            path2 = Path(name='test1',
                         positions=[Position(0, 1, 1), Position(1, 1, 1), Position(1, 0, 1)])
            assert path1.is_identical(paths[0])
            assert path2.is_identical(paths[1])

    def test_empty(self):
        with open(get_path('empty.json'), 'r') as file:
            paths = PathList.load(file)
            assert paths.size == 0

    def test_save(self):
        with open(get_path('path.json'), 'r') as file:
            paths = PathList.load(file)
            with open(get_path('path_save.json'), 'w') as file1:
                paths.save(file1)

        with open(get_path('path_save.json'), 'r') as file:
            paths1 = PathList.load(file)
            assert paths1.size == 2
            path1 = Path(name='test',
                         positions=[Position(0, 1, 1), Position(1, 1, 1), Position(1, 0, 1)],
                         connected=True)
            path2 = Path(name='test1',
                         positions=[Position(0, 1, 1), Position(1, 1, 1), Position(1, 0, 1)])
            assert path1.is_identical(paths1[0])
            assert path2.is_identical(paths1[1])
# TODO More tests
