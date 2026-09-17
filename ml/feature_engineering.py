import pandas as pd
import numpy as np

from tools.data.get_late_fee_data import get_late_fee_data


def load_training_data():
    """
    Load rental-level data and prepare ML features.
    """

    data = get_late_fee_data()
    df = pd.DataFrame(data)

    # Customer historical late rate
    customer_stats = (
        df.groupby("customer_id")
        .agg(
            customer_total_rentals=("rental_id", "count"),
            customer_late_rentals=("is_late", "sum")
        )
        .reset_index()
    )

    customer_stats["customer_late_rate"] = (
        customer_stats["customer_late_rentals"]
        / customer_stats["customer_total_rentals"]
    )

    # Avoid leakage:
    # use historical/customer-level behavior as a feature.
    df = df.merge(
        customer_stats[
            [
                "customer_id",
                "customer_late_rate"
            ]
        ],
        on="customer_id",
        how="left"
    )

    # Basic features
    df["rental_rate"] = df["rental_rate"].astype(float)
    df["rental_duration"] = df["rental_duration"].astype(float)

    df["actual_rental_days"] = (
        df["return_date"] - df["rental_date"]
    ).dt.total_seconds() / 86400

    df["late_days"] = np.maximum(
        df["actual_rental_days"]
        - df["rental_duration"],
        0
    )

    df["is_late"] = (
        df["late_days"] > 0
    ).astype(int)

    return df


def get_features_and_targets():

    df = load_training_data()

    feature_columns = [
        "rental_duration",
        "rental_rate",
        "category",
        "customer_late_rate"
    ]

    X = df[feature_columns].copy()

    y_probability = df["is_late"]

    y_late_days = df["late_days"]

    return (
        X,
        y_probability,
        y_late_days
    )


if __name__ == "__main__":

    X, y_probability, y_late_days = (
        get_features_and_targets()
    )

    print("Features:")
    print(X.head())

    print("\nFeature columns:")
    print(X.columns.tolist())

    print("\nLate probability target:")
    print(y_probability.value_counts())

    print("\nLate days target:")
    print(y_late_days.describe())
