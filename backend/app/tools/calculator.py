import ast
import operator
import re


class CalculatorError(ValueError):
    pass


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise CalculatorError("Exponent is outside the allowed range")
        return _OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.operand))
    raise CalculatorError("Expression contains an unsupported operation")


def normalize_expression(text: str) -> str:
    value = text.lower().replace(",", "")
    number = r"(-?\d+(?:\.\d+)?)"
    patterns = (
        (rf"{number}\s*%\s*of\s*{number}", lambda a, b: f"({a}/100)*{b}"),
        (rf"{number}\s*(?:times|multiplied by)\s*{number}", lambda a, b: f"{a}*{b}"),
        (rf"(?:add|sum)\s+{number}\s+(?:and|to)\s+{number}", lambda a, b: f"{a}+{b}"),
        (rf"{number}\s+(?:plus)\s+{number}", lambda a, b: f"{a}+{b}"),
        (rf"{number}\s+(?:minus)\s+{number}", lambda a, b: f"{a}-{b}"),
        (rf"{number}\s+(?:divided by|divide by)\s+{number}", lambda a, b: f"{a}/{b}"),
        (rf"(?:divide)\s+{number}\s+by\s+{number}", lambda a, b: f"{a}/{b}"),
    )
    for pattern, render in patterns:
        match = re.search(pattern, value)
        if match:
            return render(match.group(1), match.group(2))
    value = re.sub(r"[^0-9+\-*/().% ]", " ", value)
    return value.strip()


def calculate(expression: str) -> float:
    normalized = normalize_expression(expression)
    if not normalized or len(normalized) > 200:
        raise CalculatorError("Provide a mathematical expression up to 200 characters")
    if "%" in normalized:
        normalized = normalized.replace("%", "/100")
    try:
        result = _evaluate(ast.parse(normalized, mode="eval"))
    except (SyntaxError, ZeroDivisionError, OverflowError) as exc:
        raise CalculatorError("The mathematical expression is invalid") from exc
    if abs(result) > 1e100:
        raise CalculatorError("Result is outside the allowed range")
    return round(result, 10)
