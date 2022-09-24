from ml.objectdetection import ObjectRecord
import jsonpickle
import pytest

class TestObjectRecord:
    def test_record_to_json(self):
        record = ObjectRecord("test",1,2,3,4,0.5)
        json = record.__getstate__()
        expect = {
            "name": "test",
            "x1": 1.0,
            "y1": 2.0,
            "x2": 3.0,
            "y2": 4.0,
            "prob": 0.5
        }
        assert json == expect