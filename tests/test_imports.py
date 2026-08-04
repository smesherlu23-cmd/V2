"""Каждый внутренний импорт указывает на существующий модуль и имя.

Отложенные импорты внутри функций не проверяются ни интерпретатором при
запуске, ни обычными тестами: четыре таких импорта пережили рефакторинг
пакетов и роняли программу на первой же отрисовке. Обход AST ловит их без
запуска кода.
"""
import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "app"


def _module_name(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    name = ".".join(rel.parts)
    return name[: -len(".__init__")] if name.endswith(".__init__") else name


def _source_files() -> list[Path]:
    return [p for p in sorted((ROOT / PACKAGE).rglob("*.py"))
            if "__pycache__" not in p.parts]


def _modules() -> dict[str, Path]:
    found = {PACKAGE: ROOT / PACKAGE / "__init__.py"}
    for path in _source_files():
        found[_module_name(path)] = path
    return found


def _exported_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(a.asname or a.name.split(".")[0] for a in node.names)
    return names


def _target_module(module: str, path: Path, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    parts = module.split(".")
    if path.name != "__init__.py":
        parts = parts[:-1]
    base = parts[: len(parts) - node.level + 1]
    return ".".join(base + ([node.module] if node.module else []))


def test_internal_imports_resolve():
    modules = _modules()
    exports = {name: _exported_names(path) for name, path in modules.items()}
    broken: list[str] = []

    for module, path in modules.items():
        if not path.exists():
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(PACKAGE) and alias.name not in modules:
                        broken.append(f"{path}:{node.lineno} no module {alias.name!r}")
                continue
            if not isinstance(node, ast.ImportFrom):
                continue
            target = _target_module(module, path, node)
            if not target.startswith(PACKAGE):
                continue
            if target not in modules:
                broken.append(f"{path}:{node.lineno} no module {target!r}")
                continue
            for alias in node.names:
                if f"{target}.{alias.name}" in modules:
                    continue
                if alias.name not in exports.get(target, set()):
                    broken.append(
                        f"{path}:{node.lineno} {target!r} has no {alias.name!r}")

    assert not broken, "unresolvable internal imports:\n  " + "\n  ".join(broken)


def test_layers_do_not_depend_outwards():
    rank = {"infra": 0, "core": 1, "platform": 1, "controllers": 2, "ui": 3}
    violations: list[str] = []

    for module, path in _modules().items():
        parts = module.split(".")
        if len(parts) < 2 or parts[1] not in rank:
            continue
        layer = parts[1]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ImportFrom):
                continue
            target = _target_module(module, path, node)
            bits = target.split(".")
            if len(bits) < 2 or bits[0] != PACKAGE or bits[1] not in rank:
                continue
            if rank[bits[1]] > rank[layer]:
                violations.append(f"{path}:{node.lineno} {layer} -> {bits[1]}")

    assert not violations, ("a layer imports one above it:\n  "
                            + "\n  ".join(violations))
