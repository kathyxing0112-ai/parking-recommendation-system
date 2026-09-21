"""Recommendation Model.

Walking-skeleton participant standing in for the local language model recorded
in docs/environment.md and docs/adr/0001-initial-toolchain.md. Calls 9 and 10 of
docs/walking-skeleton.md. No real model call is made in this increment.
"""


def compose_recommendation_explanation(ranked_options: list) -> str:
    """Stub: return a hard-coded explanation of the right shape."""
    return (
        "LOT-1 is recommended based on current availability and walking "
        "distance to the destination."
    )
