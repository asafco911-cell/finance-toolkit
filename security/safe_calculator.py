import ast
import operator


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

MAX_EXPONENT = 100


class UnsafeExpressionError(Exception):
    """Raised when an expression contains anything other than plain arithmetic."""
    pass


def _evaluate(node):
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise UnsafeExpressionError(f"Only numbers allowed, got: {type(node.value).__name__}")
        return node.value

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise UnsafeExpressionError(f"Operator not allowed: {op_type.__name__}")

        left = _evaluate(node.left)
        right = _evaluate(node.right)

        if op_type is ast.Pow and abs(right) > MAX_EXPONENT:
            raise UnsafeExpressionError(f"Exponent too large: {right}")

        return ALLOWED_OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise UnsafeExpressionError(f"Unary operator not allowed: {op_type.__name__}")
        return ALLOWED_OPERATORS[op_type](_evaluate(node.operand))

    raise UnsafeExpressionError(f"Expression type not allowed: {type(node).__name__}")


def safe_calculate(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate(tree.body)
        return str(result)

    except UnsafeExpressionError as e:
        return f"Error: {e}"
    except ZeroDivisionError:
        return "Error: division by zero"
    except SyntaxError:
        return "Error: invalid expression syntax"