from __future__ import annotations
from dataclasses import dataclass
from sympy.solvers import solve
from sympy import Symbol, Matrix, solve_linear_system, Number
from sympy.abc import x,y

@dataclass
class Equation:
    """ A class to represent a linear equaltion of the form `y = ax + b`"""
    @staticmethod
    def get_by_points(x1: float, y1: float, x2: float, y2: float) -> Equation:
        
        system = Matrix(((x1,1,y1),(x2,1,y2)))
        result = solve_linear_system(system, x, y)
        if len(result) == 0:
            raise ValueError("Invalid points")
        
        return Equation(result[x], result[y])
        

    def __init__(self, a: float | int, b: float | int):

        if not self._is_valid(a) or not self._is_valid(b):
            raise TypeError("a must be a float or int")

        if a == 0:
            raise ValueError("a cannot be 0")

        self.a = a
        self.b = b

        self._expr = self.a * x + self.b
        # expr for x on the left hand side
        self._expr_x = (y - self.b) / self.a

    def eval_x(self, y_val: float) -> float:
        """Evaluate the equation with the given `y`
        """
        if not self._is_valid(y_val):
            raise TypeError('Invalid y')
        return self.expr_x.subs(y, y_val)

    def eval_y(self, x_val: float) -> float:
        """Evaluate the equation with the given `x`
        """
        if not self._is_valid(x_val):
            raise TypeError('Invalid x')

        return self.expr.subs(x, x_val)

    def intersection(self, other: Equation) -> tuple[float, float] | None:
        """calculate the intersection point of this equation and the 
        given equation. If there is no intersection, return None. 
        """
        result = solve(self.expr - other.expr, Symbol("x"))
        if len(result) == 0:
            return None
        inter_x = result[0]
        inter_y = self.eval_y(inter_x)

        return (float(inter_x), float(inter_y))
    
    def _is_valid(self, value) -> bool:
        """Check if the value  is valid for evaluation"""
        if not isinstance(value, (float, int, Number)):
            return False
        return True


    @property
    def expr(self):
        return self._expr

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Equation):
            return False
        if self.a == __o.a and self.b == __o.b:
            return True
        return False

    def __str__(self) -> str:
        return f"y = {self.a}x + {self.b}"
