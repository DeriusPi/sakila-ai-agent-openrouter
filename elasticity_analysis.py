import mysql.connector
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from getpass import getpass


# ============================================================
# 1. DATABASE CONNECTION
# ============================================================

print("=== SAKILA PRICE ELASTICITY ANALYSIS ===")

password = getpass("MySQL password: ")

conn = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password=password,
    database="sakila"
)

print("MySQL connection: OK")


# ============================================================
# 2. BUILD ANALYTICAL DATASET DIRECTLY FROM SAKILA
# ============================================================

query = """
SELECT
    f.film_id,
    f.title,
    c.name AS category,
    f.rental_rate,
    f.length,
    f.rating,

    COUNT(r.rental_id) AS total_rentals,
    COUNT(DISTINCT i.inventory_id) AS inventory_copies

FROM film f

JOIN film_category fc
    ON f.film_id = fc.film_id

JOIN category c
    ON fc.category_id = c.category_id

LEFT JOIN inventory i
    ON f.film_id = i.film_id

LEFT JOIN rental r
    ON i.inventory_id = r.inventory_id

GROUP BY
    f.film_id,
    f.title,
    c.name,
    f.rental_rate,
    f.length,
    f.rating
"""

df = pd.read_sql(query, conn)

conn.close()

print(f"Films loaded: {len(df)}")


# ============================================================
# 3. CREATE DEMAND VARIABLE
# ============================================================

# Demand proxy:
# number of rentals per available inventory copy

df["inventory_copies"] = df["inventory_copies"].replace(0, np.nan)

df["rentals_per_copy"] = (
    df["total_rentals"] /
    df["inventory_copies"]
)


# ============================================================
# 4. CREATE LOG VARIABLES
# ============================================================

# Remove observations that cannot be logged

df = df[
    (df["rental_rate"] > 0) &
    (df["rentals_per_copy"] > 0) &
    (df["length"] > 0)
].copy()

df["ln_price"] = np.log(df["rental_rate"])
df["ln_demand"] = np.log(df["rentals_per_copy"])


print(f"Usable observations: {len(df)}")
print(f"Categories: {df['category'].nunique()}")


# ============================================================
# 5. RUN POOLED OLS
# ============================================================

formula = """
ln_demand ~
ln_price * C(category)
+ length
+ C(rating)
"""

model = smf.ols(
    formula=formula,
    data=df
).fit(
    cov_type="HC3"
)


# ============================================================
# 6. DISPLAY MODEL RESULTS
# ============================================================

print("\n" + "=" * 70)
print("POOLED OLS RESULTS")
print("=" * 70)

print(model.summary())

print(
    f"\nR-squared: {model.rsquared:.4f}"
)

print(
    f"Adjusted R-squared: {model.rsquared_adj:.4f}"
)


# ============================================================
# 7. CALCULATE CATEGORY-SPECIFIC ELASTICITY
# ============================================================

def classify(elasticity, p_value):

    if p_value >= 0.05:
        return "Not significant"

    if abs(elasticity) > 1:
        return "Elastic"

    if abs(elasticity) < 1:
        return "Inelastic"

    return "Unit elastic"


params = model.params
covariance = model.cov_params()

parameter_names = list(params.index)

categories = sorted(
    df["category"].dropna().unique()
)

results = []


for category in categories:

    interaction = (
        f"ln_price:C(category)[T.{category}]"
    )

    # --------------------------------------------------------
    # Elasticity:
    #
    # Baseline category:
    #       beta_price
    #
    # Other categories:
    #       beta_price + beta_interaction
    # --------------------------------------------------------

    if interaction in parameter_names:

        elasticity = (
            params["ln_price"]
            + params[interaction]
        )

        # Variance of beta1 + beta2
        variance = (
            covariance.loc["ln_price", "ln_price"]
            + covariance.loc[interaction, interaction]
            + 2 * covariance.loc[
                "ln_price",
                interaction
            ]
        )

    else:

        elasticity = params["ln_price"]

        variance = covariance.loc[
            "ln_price",
            "ln_price"
        ]

    std_error = np.sqrt(max(variance, 0))

    # --------------------------------------------------------
    # Test:
    #
    # H0: category-specific elasticity = 0
    # --------------------------------------------------------

    z_value = elasticity / std_error

    from scipy.stats import norm

    p_value = 2 * (
        1 - norm.cdf(abs(z_value))
    )

    # --------------------------------------------------------
    # 95% confidence interval
    # --------------------------------------------------------

    ci_low = (
        elasticity
        - 1.96 * std_error
    )

    ci_high = (
        elasticity
        + 1.96 * std_error
    )

    # --------------------------------------------------------
    # Sample size
    # --------------------------------------------------------

    sample_size = int(
        (df["category"] == category).sum()
    )

    # --------------------------------------------------------
    # Interpretation
    # --------------------------------------------------------

    interpretation = classify(
        elasticity,
        p_value
    )

    results.append({
        "category": category,
        "elasticity": elasticity,
        "std_error": std_error,
        "z_value": z_value,
        "p_value": p_value,
        "ci_low_95": ci_low,
        "ci_high_95": ci_high,
        "sample_size": sample_size,
        "interpretation": interpretation
    })


# ============================================================
# 8. CREATE RESULT TABLE
# ============================================================

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    "elasticity"
).reset_index(drop=True)


# Round numbers for presentation

for column in [
    "elasticity",
    "std_error",
    "z_value",
    "p_value",
    "ci_low_95",
    "ci_high_95"
]:
    results_df[column] = results_df[column].round(4)


# ============================================================
# 9. DISPLAY ELASTICITY RESULTS
# ============================================================

print("\n" + "=" * 70)
print("PRICE ELASTICITY BY CATEGORY")
print("=" * 70)

print(
    results_df.to_string(index=False)
)


# ============================================================
# 10. SUMMARY
# ============================================================

significant = (
    results_df["p_value"] < 0.05
)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(
    f"Statistically significant categories: "
    f"{significant.sum()}/{len(results_df)}"
)

print("\nInterpretation rule:")
print("p >= 0.05  -> Not significant")
print("p < 0.05 and |elasticity| > 1 -> Elastic")
print("p < 0.05 and |elasticity| < 1 -> Inelastic")
print("p < 0.05 and |elasticity| = 1 -> Unit elastic")


# ============================================================
# 11. SAVE RESULT TABLE
# ============================================================

output_file = "elasticity_results.csv"

results_df.to_csv(
    output_file,
    index=False
)

print(
    f"\nResults saved to: {output_file}"
)
