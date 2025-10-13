import ast
import datetime as dt
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs" / "code_analysis.md"


def summarize_docstring(doc: str | None) -> str:
    if not doc:
        return ""
    first_line = doc.strip().splitlines()[0].strip()
    return first_line


def collect_imports(tree: ast.AST) -> List[str]:
    imports: List[str] = []
    for node in tree.body:  # type: ignore[attr-defined]
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ", ".join(alias.name for alias in node.names)
            imports.append(f"{module} -> {names}")
    return imports


def format_args(args: ast.arguments) -> str:
    parts: List[str] = []
    posonly = list(getattr(args, "posonlyargs", []))
    for arg in posonly:
        parts.append(arg.arg)
    if posonly:
        parts.append("/")

    for arg in args.args:
        parts.append(arg.arg)

    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    elif args.kwonlyargs:
        parts.append("*")

    for arg in args.kwonlyargs:
        parts.append(arg.arg)

    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")

    return ", ".join(parts)


def main() -> None:
    files = sorted(ROOT.rglob("*.py"))
    generated = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = []
    lines.append("# Code Analysis Overview")
    lines.append("")
    lines.append(f"Generated on {generated}.")
    lines.append("")
    lines.append(f"Total Python files analyzed: {len(files)}.")
    lines.append("")

    for path in files:
        rel = path.relative_to(ROOT)
        source = path.read_text(encoding="utf-8")
        if source.startswith("\ufeff"):
            source = source.lstrip("\ufeff")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            lines.append(f"## {rel}")
            lines.append("")
            lines.append(f"- **Error:** Failed to parse ({exc})")
            lines.append("")
            continue

        module_doc = summarize_docstring(ast.get_docstring(tree))
        imports = collect_imports(tree)

        classes: List[str] = []
        functions: List[str] = []

        for node in tree.body:  # type: ignore[attr-defined]
            if isinstance(node, ast.ClassDef):
                class_doc = summarize_docstring(ast.get_docstring(node)) or "(no docstring)"
                methods: List[str] = []
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        args = format_args(child.args)
                        method_doc = summarize_docstring(ast.get_docstring(child)) or ""
                        if method_doc:
                            methods.append(f"`{child.name}({args})` — {method_doc}")
                        else:
                            methods.append(f"`{child.name}({args})`")
                if methods:
                    method_lines = "\n    - ".join(methods)
                    classes.append(
                        f"- `{node.name}` — {class_doc}\n    - {method_lines}"
                    )
                else:
                    classes.append(f"- `{node.name}` — {class_doc}")
            elif isinstance(node, ast.FunctionDef):
                args = format_args(node.args)
                func_doc = summarize_docstring(ast.get_docstring(node)) or ""
                if func_doc:
                    functions.append(f"- `{node.name}({args})` — {func_doc}")
                else:
                    functions.append(f"- `{node.name}({args})`")

        lines.append(f"## {rel}")
        lines.append("")
        if module_doc:
            lines.append(f"- **Module docstring:** {module_doc}")
        else:
            lines.append("- **Module docstring:** (none)")

        if imports:
            imports_inline = ", ".join(f"`{imp}`" for imp in imports)
            lines.append(f"- **Imports:** {imports_inline}")
        else:
            lines.append("- **Imports:** (none)")

        if classes:
            lines.append("- **Classes:**")
            lines.extend(classes)
        else:
            lines.append("- **Classes:** (none)")

        if functions:
            lines.append("- **Functions:**")
            lines.extend(functions)
        else:
            lines.append("- **Functions:** (none)")

        lines.append("")

    TARGET.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
