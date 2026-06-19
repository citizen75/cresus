"""Shared portfolio/journal/order name normalization."""


def normalize_portfolio_name(name: str) -> str:
    """Normalize a portfolio/bot name to lowercase snake_case.

    Used consistently by Journal, Orders, and PortfolioManager so the same
    logical portfolio always maps to the same folder/file name.

    Examples:
        "Momentum cac" -> "momentum_cac"
        "PEA Gilles" -> "pea_gilles"
        "momentum_cac" -> "momentum_cac"
    """
    return name.lower().replace(" ", "_")
