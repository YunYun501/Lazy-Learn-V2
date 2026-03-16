from app.services.latex_parser import (
    EquationInfo,
    build_variable_cooccurrence,
    clean_mineru_artifacts,
    extract_variables,
    filter_variables,
    parse_equation,
)


def test_clean_strips_dollar_delimiters():
    assert clean_mineru_artifacts("$$\\omega$$") == "\\omega"


def test_extract_greek_letters():
    assert extract_variables("\\omega_{c}") == {"omega_c"}


def test_extract_subscripted():
    assert extract_variables("T_{s}") == {"T_s"}


def test_filter_removes_constants():
    assert filter_variables({"e", "x"}) == {"x"}


def test_filter_removes_operators():
    assert filter_variables({"sin", "theta"}) == {"theta"}


def test_parse_equation_full():
    info = parse_equation("$$\\omega_{c} = \\sqrt{g/y}$$")
    assert info.is_parseable is True
    assert info.variables == {"omega_c", "g", "y"}


def test_parse_partial_derivative():
    info = parse_equation("\\frac{\\partial f}{\\partial x}")
    assert info.variables == {"f", "x"}


def test_unparseable_returns_empty():
    info = parse_equation(None)
    assert info.is_parseable is False
    assert info.variables == set()


def test_cooccurrence_detects_shared():
    eqs = [
        (
            "eq1",
            EquationInfo(raw_latex="a", variables={"omega_c", "x"}, is_parseable=True),
        ),
        ("eq2", EquationInfo(raw_latex="b", variables={"omega_c"}, is_parseable=True)),
        ("eq3", EquationInfo(raw_latex="c", variables={"y"}, is_parseable=True)),
    ]
    pairs = build_variable_cooccurrence(eqs)
    assert ("eq1", "eq2", 1) in pairs or ("eq2", "eq1", 1) in pairs
