"""
solver.py — CSP Backtracking Solver for Cryptarithmetic Puzzles
Fast coefficient-based solver with optional explanation trace capture.
"""

import time


def parse_puzzle(word1: str, word2: str, result: str):
    words = [w.strip().upper() for w in [word1, word2, result]]
    for w in words:
        if not w.isalpha():
            raise ValueError(f"Invalid word: '{w}'. Only letters are allowed.")
    all_letters = set()
    for w in words:
        all_letters.update(w)
    unique_letters = sorted(all_letters)
    if len(unique_letters) > 10:
        raise ValueError(f"Too many unique letters ({len(unique_letters)}). Max is 10.")
    leading_letters = {w[0] for w in words if w}
    return words, unique_letters, leading_letters


def format_solution(words: list, assignment: dict) -> dict:
    if assignment is None:
        return None
    mapping_str = "   ".join(f"{ch} = {assignment[ch]}" for ch in sorted(assignment))
    def word_to_num(w):
        return int("".join(str(assignment[c]) for c in w))
    nums = [word_to_num(w) for w in words]
    addend_strs = " + ".join(str(n) for n in nums[:-1])
    eq_str = f"{addend_strs} = {nums[-1]}"
    return {
        "mapping": mapping_str,
        "equation": " + ".join(words[:-1]) + " = " + words[-1],
        "numeric_equation": eq_str,
        "mapping_dict": assignment,
        "numbers": nums,
    }


def solve_cryptarithm(word1: str, word2: str, result_word: str,
                      capture_trace: bool = False):
    """
    Main solver using CSP backtracking with:
    - Coefficient-based forward checking (sum-pruning)
    - Most-constrained variable ordering
    - Optional trace capture for Explanation panel

    Returns: (assignment_dict, elapsed_sec, nodes_explored, error_str, trace_steps)
    """
    start_time = time.perf_counter()
    trace = [] if capture_trace else None

    try:
        words, unique_letters, leading_letters = parse_puzzle(word1, word2, result_word)
    except ValueError as e:
        return None, 0.0, 0, str(e), []

    n = len(unique_letters)
    letter_index = {ch: i for i, ch in enumerate(unique_letters)}

    # Encode equation as: sum(coeff[i] * digit[i]) == 0
    coefficients = [0] * n
    for word in words[:-1]:
        for pos, ch in enumerate(reversed(word)):
            coefficients[letter_index[ch]] += 10 ** pos
    for pos, ch in enumerate(reversed(words[-1])):
        coefficients[letter_index[ch]] -= 10 ** pos

    no_lead_zero = {letter_index[ch] for ch in leading_letters}
    nodes_explored = [0]
    step_counter = [0]

    def var_priority(i):
        ch = unique_letters[i]
        freq = sum(w.count(ch) for w in words)
        is_leading = ch in leading_letters
        return (-abs(coefficients[i]), -freq, is_leading)

    ordered_vars = sorted(range(n), key=var_priority)
    assignment = [-1] * n
    used_digits = [False] * 10

    MAX_TRACE = 150  # cap trace lines for display

    def backtrack(var_pos, partial_sum):
        nodes_explored[0] += 1

        if var_pos == n:
            if partial_sum == 0:
                if capture_trace:
                    trace.append({
                        "type": "solution",
                        "msg": "✓  Equation verified — valid solution found!",
                        "step": step_counter[0],
                    })
                return True
            return False

        var = ordered_vars[var_pos]
        coeff = coefficients[var]
        ch = unique_letters[var]
        is_no_zero = var in no_lead_zero

        for digit in range(0 if not is_no_zero else 1, 10):
            if used_digits[digit]:
                continue

            step_counter[0] += 1
            assignment[var] = digit
            used_digits[digit] = True
            new_sum = partial_sum + coeff * digit

            do_trace = capture_trace and len(trace) < MAX_TRACE

            if do_trace:
                trace.append({
                    "type": "assign",
                    "letter": ch,
                    "digit": digit,
                    "step": step_counter[0],
                    "msg": (f"Step {step_counter[0]:>3}:  Assign  {ch} = {digit}   "
                            f"coeff={coeff:+d}   partial_sum={new_sum:+d}"),
                })

            remaining_vars = [ordered_vars[j] for j in range(var_pos + 1, n)]
            if remaining_vars:
                remaining_digits = [d for d in range(10) if not used_digits[d]]
                min_possible = new_sum
                max_possible = new_sum
                pruned = False

                for rv in remaining_vars:
                    c = coefficients[rv]
                    is_nz = rv in no_lead_zero
                    avail = [d for d in remaining_digits if not (is_nz and d == 0)]
                    if not avail:
                        pruned = True
                        break
                    if c > 0:
                        min_possible += c * min(avail)
                        max_possible += c * max(avail)
                    else:
                        min_possible += c * max(avail)
                        max_possible += c * min(avail)

                if pruned or not (min_possible <= 0 <= max_possible):
                    if do_trace:
                        trace.append({
                            "type": "prune",
                            "letter": ch,
                            "digit": digit,
                            "step": step_counter[0],
                            "msg": (f"       ↳ Pruned  {ch}={digit}  "
                                    f"range [{min_possible:+d}…{max_possible:+d}] "
                                    f"cannot reach 0"),
                        })
                    used_digits[digit] = False
                    assignment[var] = -1
                    continue

                if backtrack(var_pos + 1, new_sum):
                    return True
            else:
                if new_sum == 0:
                    return True

            if do_trace:
                trace.append({
                    "type": "backtrack",
                    "letter": ch,
                    "digit": digit,
                    "step": step_counter[0],
                    "msg": f"       ↳ Backtrack  {ch}={digit}  — dead end",
                })

            used_digits[digit] = False
            assignment[var] = -1

        return False

    found = backtrack(0, 0)
    elapsed = time.perf_counter() - start_time

    if capture_trace and step_counter[0] > MAX_TRACE:
        trace.append({
            "type": "info",
            "msg": f"  … {nodes_explored[0] - MAX_TRACE} more nodes not shown …",
            "step": 9999,
        })

    if not found:
        if capture_trace:
            trace.append({
                "type": "no_solution",
                "msg": "✗  Search exhausted — no valid assignment exists.",
                "step": step_counter[0],
            })
        return None, elapsed, nodes_explored[0], None, trace or []

    result_map = {ch: assignment[i] for i, ch in enumerate(unique_letters)}
    return result_map, elapsed, nodes_explored[0], None, trace or []