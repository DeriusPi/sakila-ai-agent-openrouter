import pandas as pd


CSV_FILE = "elasticity_results.csv"

df = pd.read_csv(CSV_FILE)


# ============================================================
# TOOL 1 — GET ALL ELASTICITY RESULTS
# ============================================================

def get_elasticity_results():
    """Return elasticity results for all categories."""
    return df.to_dict(orient="records")


# ============================================================
# TOOL 2 — GET CATEGORY DETAILS
# ============================================================

def get_category_details(category):
    """Return detailed elasticity information for one category."""

    match = df[
        df["category"].astype(str).str.lower()
        == category.strip().lower()
    ]

    if match.empty:
        return {
            "error": f"Category '{category}' not found."
        }

    row = match.iloc[0]

    return {
        "category": row["category"],
        "price_elasticity": float(row["price_elasticity"]),
        "std_error": float(row["std_error"]),
        "z_value": float(row["z_value"]),
        "p_value": float(row["p_value"]),
        "ci_low_95": float(row["ci_low_95"]),
        "ci_high_95": float(row["ci_high_95"]),
        "sample_size": int(row["sample_size"]),
        "interpretation": row["interpretation"]
    }


# ============================================================
# TOOL 3 — GET ELASTICITY SUMMARY
# ============================================================

def get_elasticity_summary():
    """Return a statistical summary of all categories."""

    return {
        "number_of_categories": int(len(df)),

        "mean_elasticity": float(
            df["price_elasticity"].mean()
        ),

        "minimum_elasticity": float(
            df["price_elasticity"].min()
        ),

        "maximum_elasticity": float(
            df["price_elasticity"].max()
        ),

        "significant_categories": int(
            (df["p_value"] < 0.05).sum()
        ),

        "elastic_categories": int(
            (df["price_elasticity"].abs() > 1).sum()
        ),

        "inelastic_categories": int(
            (df["price_elasticity"].abs() < 1).sum()
        ),

        "unit_elastic_categories": int(
            (df["price_elasticity"].abs() == 1).sum()
        )
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("DATA TOOLS TEST")
    print("=" * 70)

    results = get_elasticity_results()

    print("\nTool 1:")
    print(f"Returned {len(results)} categories.")

    details = get_category_details("Sci-Fi")

    print("\nTool 2:")
    print(details)

    summary = get_elasticity_summary()

    print("\nTool 3:")
    print(summary)

    print("\nData tools test completed successfully.")
