import pandas as pd


# ============================================================
# CONFIG
# ============================================================

CSV_FILE = "elasticity_results.csv"

df = pd.read_csv(CSV_FILE)


# ============================================================
# TOOL 4 — GET SIGNIFICANT CATEGORIES
# ============================================================

def get_significant_categories(alpha=0.05):
    """
    Return categories whose price elasticity is
    statistically significant.

    alpha:
        Significance level. Default = 0.05.
    """

    result = df[
        df["p_value"] < alpha
    ].copy()

    return result[
        [
            "category",
            "price_elasticity",
            "p_value",
            "ci_low_95",
            "ci_high_95",
            "interpretation"
        ]
    ].to_dict(orient="records")


# ============================================================
# TOOL 5 — RANK ELASTICITY
# ============================================================

def rank_elasticity(
    ascending=True,
    significant_only=False
):
    """
    Rank categories according to price elasticity.

    ascending=True:
        Lowest elasticity first.

    significant_only=True:
        Only statistically significant categories.
    """

    result = df.copy()

    if significant_only:
        result = result[
            result["p_value"] < 0.05
        ]

    result = result.sort_values(
        by="price_elasticity",
        ascending=ascending
    )

    return result[
        [
            "category",
            "price_elasticity",
            "p_value",
            "interpretation"
        ]
    ].to_dict(orient="records")


# ============================================================
# TOOL 6 — COMPARE CATEGORIES
# ============================================================

def compare_categories(
    category_1,
    category_2
):
    """
    Compare two categories based on their
    price elasticity results.
    """

    names = [
        category_1.strip().lower(),
        category_2.strip().lower()
    ]

    result = df[
        df["category"]
        .astype(str)
        .str.lower()
        .isin(names)
    ].copy()

    if len(result) != 2:

        found = result["category"].tolist()

        return {
            "error": "One or both categories were not found.",
            "found_categories": found
        }

    result = result.sort_values(
        by="price_elasticity"
    )

    comparison = []

    for _, row in result.iterrows():

        comparison.append({
            "category": row["category"],
            "price_elasticity": float(
                row["price_elasticity"]
            ),
            "p_value": float(
                row["p_value"]
            ),
            "ci_low_95": float(
                row["ci_low_95"]
            ),
            "ci_high_95": float(
                row["ci_high_95"]
            ),
            "interpretation": row["interpretation"]
        })

    return {
        "categories": comparison
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("ANALYSIS TOOLS TEST")
    print("=" * 70)


    # --------------------------------------------------------
    # TOOL 4
    # --------------------------------------------------------

    print("\n[Tool 4] Significant categories")

    significant = get_significant_categories()

    print(
        f"Found {len(significant)} significant categories."
    )

    for row in significant:

        print(
            f"{row['category']}: "
            f"elasticity={row['price_elasticity']}, "
            f"p-value={row['p_value']}"
        )


    # --------------------------------------------------------
    # TOOL 5
    # --------------------------------------------------------

    print("\n[Tool 5] Rank elasticity")

    ranked = rank_elasticity()

    for row in ranked[:5]:

        print(
            f"{row['category']}: "
            f"{row['price_elasticity']}"
        )


    # --------------------------------------------------------
    # TOOL 6
    # --------------------------------------------------------

    print("\n[Tool 6] Compare categories")

    comparison = compare_categories(
        "Sci-Fi",
        "Children"
    )

    print(comparison)


    print("\nAnalysis tools test completed successfully.")
