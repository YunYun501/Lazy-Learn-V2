from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

CONSTANTS = frozenset({"e", "i", "pi", "infty", "inf"})
OPERATORS = frozenset(
    {
        "sin",
        "cos",
        "tan",
        "log",
        "ln",
        "exp",
        "lim",
        "max",
        "min",
        "det",
        "sup",
        "inf",
        "arg",
        "mod",
    }
)
LATEX_COMMANDS = frozenset(
    {
        "frac",
        "int",
        "sum",
        "prod",
        "partial",
        "left",
        "right",
        "begin",
        "end",
        "sqrt",
        "cdot",
        "times",
        "displaystyle",
        "text",
        "mathrm",
        "mathbf",
        "vec",
        "hat",
        "bar",
        "tilde",
        "dot",
        "ddot",
        "overline",
        "underline",
        "overbrace",
        "underbrace",
    }
)

GREEK_LETTERS = frozenset(
    {
        "alpha",
        "beta",
        "gamma",
        "omega",
        "theta",
        "phi",
        "sigma",
        "mu",
        "lambda",
        "delta",
        "epsilon",
        "rho",
        "tau",
        "pi",
    }
)


@dataclass
class EquationInfo:
    raw_latex: str
    variables: set[str]
    is_parseable: bool


def clean_mineru_artifacts(latex: str) -> str:
    if not isinstance(latex, str):
        raise TypeError("latex must be a string")

    cleaned = latex.strip()
    cleaned = cleaned.replace("$$", "")
    cleaned = re.sub(r"\\llap\s*{[^}]*}", "", cleaned)
    cleaned = re.sub(r"\\marginpar\s*{[^}]*}", "", cleaned)
    cleaned = re.sub(r"\\\s+", r"\\", cleaned)
    cleaned = re.sub(r"\\{2,}", r"\\", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _normalize_greek(command: str) -> str | None:
    name = command.lstrip("\\")
    if name in GREEK_LETTERS:
        return name
    return None


def _normalize_subscript(subscript: str) -> str | None:
    subscript = subscript.strip()
    greek_match = re.match(r"\\([a-zA-Z]+)", subscript)
    if greek_match:
        greek = greek_match.group(1)
        if greek in GREEK_LETTERS:
            return greek
    token_match = re.search(r"[a-zA-Z0-9]+", subscript)
    if token_match:
        return token_match.group(0)
    return None


def _extract_simple_vars(fragment: str) -> set[str]:
    vars_found: set[str] = set()
    for greek in re.findall(r"\\([a-zA-Z]+)", fragment):
        if greek in GREEK_LETTERS:
            vars_found.add(greek)
    for letter in re.findall(r"(?<!\\)(?<![A-Za-z])[A-Za-z](?![A-Za-z])", fragment):
        vars_found.add(letter)
    return vars_found


def extract_variables(latex: str) -> set[str]:
    variables: set[str] = set()
    working = latex

    for match in re.finditer(r"\\(?:vec|mathbf)\s*{([^}]+)}", working):
        variables.update(_extract_simple_vars(match.group(1)))
    working = re.sub(r"\\(?:vec|mathbf)\s*{[^}]+}", " ", working)

    for match in re.finditer(
        r"\\frac\s*{\\partial\s+([^}]+)}\s*{\\partial\s+([^}]+)}", working
    ):
        variables.update(_extract_simple_vars(match.group(1)))
        variables.update(_extract_simple_vars(match.group(2)))
    working = re.sub(
        r"\\frac\s*{\\partial\s+[^}]+}\s*{\\partial\s+[^}]+}", " ", working
    )

    for match in re.finditer(r"(\\[a-zA-Z]+|[a-zA-Z])_\{([^}]+)}", working):
        base, subscript = match.group(1), match.group(2)
        base_name = _normalize_greek(base)
        if base_name is None:
            base_name = base if not base.startswith("\\") else None
        sub_name = _normalize_subscript(subscript)
        if base_name and sub_name:
            variables.add(f"{base_name}_{sub_name}")
    working = re.sub(r"(\\[a-zA-Z]+|[a-zA-Z])_\{[^}]+}", " ", working)

    for match in re.finditer(r"(\\[a-zA-Z]+|[a-zA-Z])\^\{[^}]+}", working):
        base = match.group(1)
        base_name = _normalize_greek(base)
        if base_name is None:
            base_name = base if not base.startswith("\\") else None
        if base_name:
            variables.add(base_name)
    working = re.sub(r"(\\[a-zA-Z]+|[a-zA-Z])\^\{[^}]+}", " ", working)

    for greek in re.findall(r"\\([a-zA-Z]+)", working):
        if greek in GREEK_LETTERS:
            variables.add(greek)

    for letter in re.findall(r"(?<!\\)(?<![A-Za-z])[A-Za-z](?![A-Za-z])", working):
        variables.add(letter)

    return variables


def filter_variables(vars: set[str]) -> set[str]:
    filtered = set()
    for var in vars:
        lowered = var.lower()
        if lowered in CONSTANTS:
            continue
        if lowered in OPERATORS:
            continue
        if lowered in LATEX_COMMANDS:
            continue
        filtered.add(var)
    return filtered


def parse_equation(latex: str) -> EquationInfo:
    try:
        cleaned = clean_mineru_artifacts(latex)
        raw_vars = extract_variables(cleaned)
        filtered = filter_variables(raw_vars)
        return EquationInfo(raw_latex=cleaned, variables=filtered, is_parseable=True)
    except Exception:
        return EquationInfo(raw_latex=latex, variables=set(), is_parseable=False)


def build_variable_cooccurrence(
    equations: list[tuple[str, EquationInfo]],
) -> list[tuple[str, str, int]]:
    var_to_eqs: defaultdict[str, list[str]] = defaultdict(list)
    for eq_id, info in equations:
        for var in info.variables:
            var_to_eqs[var].append(eq_id)

    pair_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    for eq_ids in var_to_eqs.values():
        unique_ids = sorted(set(eq_ids))
        for i in range(len(unique_ids)):
            for j in range(i + 1, len(unique_ids)):
                pair = (unique_ids[i], unique_ids[j])
                pair_counts[pair] += 1

    return [(a, b, count) for (a, b), count in pair_counts.items()]
