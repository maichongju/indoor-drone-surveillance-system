import pytest
from general.equation import Equation



class TestEquation:
    @pytest.mark.parametrize("x1, y1, x2, y2, a, b",
                             [
                                 (0,5,-1,2,3,5)
                                 
                             ])
    def test_get_by_points(self, x1, y1, x2, y2, a, b):
        eq = Equation.get_by_points(x1, y1, x2, y2)
        assert eq.a == a
        assert eq.b == b
        
        
        