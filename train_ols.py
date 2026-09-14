import mysql.connector
import pandas as pd
import statsmodels.formula.api as smf


# 1. Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="0913348843a",
    database="sakila"
)

print("Kết nối MySQL thành công!")


# 2. Load elasticity dataset
query = """
SELECT
    film_id,
    title,
    category,
    rental_rate,
    rentals_per_copy,
    length,
    rating,
    ln_price,
    ln_demand
FROM elasticity_dataset
"""

df = pd.read_sql(query, conn)

conn.close()

print(f"Loaded {len(df)} observations")


# 3. Log-log OLS with category interactions
model = smf.ols(
    "ln_demand ~ ln_price * C(category) + length + C(rating)",
    data=df
).fit(cov_type="HC3")


# 4. Print regression results
print("\n===== OLS RESULTS =====")
print(model.summary())


