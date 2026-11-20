"""Deprecated: automated heuristics cannot create human review decisions."""


def main():
    raise RuntimeError(
        "This heuristic review tool is disabled because its output is not human-confirmed. "
        "Use interactive_human_review.py, web_human_review.py, or edit the review spreadsheet."
    )


if __name__ == "__main__":
    main()
