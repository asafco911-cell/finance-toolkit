from safe_calculator import safe_calculate


def check(name, expression, should_work):
    result = safe_calculate(expression)
    blocked = result.startswith("Error:")

    ok = (blocked != should_work)
    status = "PASS" if ok else "FAIL"

    print(f"[{status}] {name}")
    print(f"       Input:  {expression}")
    print(f"       Output: {result}\n")


if __name__ == "__main__":
    print("=== Legitimate arithmetic (must work) ===\n")

    check("Simple division",   "10053 / 2100",        should_work=True)
    check("Multiple ops",      "(100 - 20) * 3 + 5",  should_work=True)
    check("Decimals",          "52017 / 43978",       should_work=True)
    check("Negative numbers",  "-500 + 200",          should_work=True)
    check("Small power",       "2 ** 10",             should_work=True)

    print("=== Malicious input (must be blocked) ===\n")

    check("OS command execution", "__import__('os').system('dir')",  should_work=False)
    check("File read",            "open('.env').read()",             should_work=False)
    check("Builtin access",       "eval('1+1')",                     should_work=False)
    check("DoS via huge power",   "9 ** 999999999",                  should_work=False)
    check("Attribute access",     "(1).__class__.__bases__",         should_work=False)

    print("=== Malformed input (must fail gracefully) ===\n")

    check("Division by zero",  "100 / 0",     should_work=False)
    check("Broken syntax",     "10 + + * 3",  should_work=False)