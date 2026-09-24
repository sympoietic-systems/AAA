"""AST-based architecture debt inventory.

The inventory is a ratchet: existing debt may shrink, while new direct
repository calls from async routes and new broad catches fail verification.
"""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
from typing import Final

PRODUCTION_EXCEPTION_ROOTS: Final = ("services", "modules", "metabolisation")


def _attribute_parts(node: ast.expr) -> tuple[str, ...]:
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return tuple(reversed(parts))


def _is_sync_boundary_candidate(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Attribute):
        return False
    owner = _attribute_parts(call.func.value)
    if not owner:
        return False
    terminal = owner[-1]
    return (
        terminal == "repo"
        or terminal == "manager"
        or terminal.endswith("_repo")
        or terminal.endswith("Service")
        or any(part.endswith("_repo") or part.endswith("_manager") for part in owner)
    )


def _call_signature(call: ast.Call) -> str:
    assert isinstance(call.func, ast.Attribute)
    owner = ".".join(_attribute_parts(call.func.value))
    return f"{owner}.{call.func.attr}"


def _is_to_thread(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Attribute) and _attribute_parts(call.func) == ("asyncio", "to_thread")


class _AsyncRouteVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self._async_depth = 0
        self._await_depth = 0
        self._offload_depth = 0
        self.calls: Counter[str] = Counter()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._async_depth += 1
        for statement in node.body:
            self.visit(statement)
        self._async_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._async_depth == 0:
            self.generic_visit(node)

    def visit_Await(self, node: ast.Await) -> None:
        self._await_depth += 1
        self.visit(node.value)
        self._await_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        if _is_to_thread(node):
            self.visit(node.func)
            self._offload_depth += 1
            for argument in node.args:
                self.visit(argument)
            for keyword in node.keywords:
                self.visit(keyword.value)
            self._offload_depth -= 1
            return
        if (
            self._async_depth
            and not self._await_depth
            and not self._offload_depth
            and _is_sync_boundary_candidate(node)
        ):
            self.calls[_call_signature(node)] += 1
        self.generic_visit(node)


def scan_sync_route_calls(repo_root: Path) -> dict[str, dict[str, int]]:
    routes_root = repo_root / "backend" / "api" / "routes"
    inventory: dict[str, dict[str, int]] = {}
    for path in sorted(routes_root.rglob("*.py")):
        visitor = _AsyncRouteVisitor()
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        if visitor.calls:
            relative = path.relative_to(repo_root).as_posix()
            inventory[relative] = dict(sorted(visitor.calls.items()))
    return inventory


class _BroadCatchVisitor(ast.NodeVisitor):
    """Inventory broad catches by their owning callable boundary."""

    def __init__(self) -> None:
        self._scope: list[str] = []
        self.catches: Counter[str] = Counter()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_callable(node)

    def _visit_callable(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if isinstance(node.type, ast.Name) and node.type.id == "Exception":
            boundary = ".".join(self._scope) if self._scope else "<module>"
            self.catches[boundary] += 1
        self.generic_visit(node)


def scan_broad_catches(repo_root: Path) -> dict[str, dict[str, int]]:
    backend_root = repo_root / "backend"
    inventory: dict[str, dict[str, int]] = {}
    for root_name in PRODUCTION_EXCEPTION_ROOTS:
        for path in sorted((backend_root / root_name).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            visitor = _BroadCatchVisitor()
            visitor.visit(tree)
            if visitor.catches:
                inventory[path.relative_to(repo_root).as_posix()] = dict(sorted(visitor.catches.items()))
    return inventory


def debt_growth(current: dict[str, dict[str, int]], baseline: dict[str, dict[str, int]]) -> list[str]:
    growth: list[str] = []
    for path, calls in current.items():
        allowed_calls = baseline.get(path, {})
        for signature, count in calls.items():
            allowed = allowed_calls.get(signature, 0)
            if count > allowed:
                growth.append(f"{path}: {signature} {count}>{allowed}")
    return growth
