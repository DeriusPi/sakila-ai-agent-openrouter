import os
import pickle

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report
)

from tools.data.get_late_fee_data import get_late_fee_data


MODEL_PATH = "ml/models/late_return_model.pkl"


def build_training_dataset():
    """
    Build an ML dataset without target leakage.

    The customer_late_rate feature is calculated using
    previous rentals only.

    Target:
        is_late

    Features:
        rental_duration
        rental_rate
        category
        customer_late_rate
    """

    data = get_late_fee_data()

    if not data:
        raise ValueError("No rental data available.")

    df = pd.DataFrame(data)

    # Make sure rentals are ordered chronologically
    df = df.sort_values(
        by=["customer_id", "rental_date"]
    ).reset_index(drop=True)

    # --------------------------------------------------
    # Historical customer behavior
    # --------------------------------------------------

    # IMPORTANT:
    # shift(1) means the current rental is NOT included
    # when calculating the customer's historical behavior.
    #
    # Example:
    #
    # Rental 1 -> no previous history
    # Rental 2 -> based only on Rental 1
    # Rental 3 -> based only on Rental 1 + Rental 2
    #
    # This prevents target leakage.

    df["previous_rentals"] = (
        df.groupby("customer_id")
        .cumcount()
    )

    df["previous_late_rentals"] = (
        df.groupby("customer_id")["is_late"]
        .transform(
            lambda x: x.astype(int).shift(1).fillna(0).cumsum()
        )
    )

    df["customer_late_rate"] = (
        df["previous_late_rentals"]
        / df["previous_rentals"].replace(0, 1)
    )

    # For customers with no previous rental,
    # assume historical late rate = overall prior-neutral value.
    #
    # We use 0 here because there is no evidence of
    # previous late behavior.
    df.loc[
        df["previous_rentals"] == 0,
        "customer_late_rate"
    ] = 0.0

    # --------------------------------------------------
    # Features
    # --------------------------------------------------

    feature_columns = [
        "rental_duration",
        "rental_rate",
        "category",
        "customer_late_rate"
    ]

    X = df[feature_columns].copy()

    y = df["is_late"].astype(int)

    return X, y


def train_model():

    print("Loading data...")

    X, y = build_training_dataset()

    print(f"Training rows: {len(X)}")
    print(f"Features: {list(X.columns)}")

    print("\nChecking target distribution:")

    print(
        y.value_counts(
            normalize=True
        ).rename(
            {
                0: "On time",
                1: "Late"
            }
        )
    )

    # --------------------------------------------------
    # Train / test split
    # --------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    # --------------------------------------------------
    # Preprocessing
    # --------------------------------------------------

    numeric_features = [
        "rental_duration",
        "rental_rate",
        "customer_late_rate"
    ]

    categorical_features = [
        "category"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                StandardScaler(),
                numeric_features
            ),
            (
                "category",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                categorical_features
            )
        ]
    )

    # --------------------------------------------------
    # Logistic Regression
    # --------------------------------------------------

    model = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    random_state=42
                )
            )
        ]
    )

    print("\nTraining Logistic Regression...")

    model.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------
    # Evaluation
    # --------------------------------------------------

    y_pred = model.predict(X_test)

    y_probability = (
        model.predict_proba(X_test)[:, 1]
    )

    accuracy = accuracy_score(
        y_test,
        y_pred
    )

    precision = precision_score(
        y_test,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        y_pred,
        zero_division=0
    )

    auc = roc_auc_score(
        y_test,
        y_probability
    )

    print("\n==============================")
    print("MODEL PERFORMANCE")
    print("==============================")

    print(
        f"Accuracy:  {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall:    {recall:.4f}"
    )

    print(
        f"F1 Score:  {f1:.4f}"
    )

    print(
        f"ROC-AUC:   {auc:.4f}"
    )

    print("\nClassification Report:")

    print(
        classification_report(
            y_test,
            y_pred,
            zero_division=0
        )
    )

    # --------------------------------------------------
    # Save model
    # --------------------------------------------------

    os.makedirs(
        os.path.dirname(MODEL_PATH),
        exist_ok=True
    )

    with open(
        MODEL_PATH,
        "wb"
    ) as f:

        pickle.dump(
            model,
            f
        )

    print(
        f"\nModel saved to: {MODEL_PATH}"
    )

    return model


if __name__ == "__main__":
    train_model()
