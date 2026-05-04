from __future__ import annotations

import ast
from dataclasses import dataclass


FORBIDDEN_IMPORT_NAMES = {
    "os", "sys", "subprocess", "socket", "urllib", "http", "ftplib", "telnetlib",
    "multiprocessing", "threading", "ctypes", "signal", "importlib", "builtins",
    "marshal", "pickle", "shelve", "asyncio", "selectors", "ssl", "requests",
    "httpx", "aiohttp", "websockets",
}
FORBIDDEN_NAMES = {
    "__import__", "eval", "exec", "compile", "globals", "locals", "vars",
    "open", "setattr", "delattr",
}
ALLOWED_TOP_LEVEL_IMPORTS = {
    "random", "math", "statistics", "dataclasses", "typing", "collections",
    "itertools", "functools", "operator", "enum", "abc", "json", "coachbench",
    "agents", "__future__",
}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    lineno: int
    col: int
    code: str
    message: str


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def _issue(self, node: ast.AST, code: str, message: str) -> None:
        self.issues.append(ValidationIssue("error", getattr(node, "lineno", 0), getattr(node, "col_offset", 0), code, message))

    def _check_import(self, node: ast.AST, name: str) -> None:
        root = name.split(".", 1)[0]
        if root in FORBIDDEN_IMPORT_NAMES:
            self._issue(node, "E_FORBIDDEN_IMPORT", f"Import is forbidden: {root}")
        elif root not in ALLOWED_TOP_LEVEL_IMPORTS:
            self._issue(node, "E_IMPORT_NOT_ALLOWED", f"Import is not allowlisted: {root}")

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_import(node, alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self._check_import(node, node.module)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in FORBIDDEN_NAMES:
            self._issue(node, "E_FORBIDDEN_NAME", f"Name is forbidden: {node.id}")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__"):
            self._issue(node, "E_DUNDER_ATTRIBUTE", f"Dunder attribute access is forbidden: {node.attr}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant) or not isinstance(node.args[1].value, str):
                self._issue(node, "E_DYNAMIC_GETATTR", "getattr requires a string literal attribute")
        self.generic_visit(node)


def validate_agent_source(source: str) -> list[ValidationIssue]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [ValidationIssue("error", exc.lineno or 0, exc.offset or 0, "E_SYNTAX", str(exc))]
    visitor = _Visitor()
    visitor.visit(tree)
    return visitor.issues
