import os
import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from ml.feature_engineering import get_features_and_targets


def train_model():

    print("Loading data...")

    X, _, y_late_days = get_features_and_targets()

    # --------------------------------------------------
    # Only train on rentals that were actually late
    # --------------------------------------------------

    late_mask = y_late_days > 0

    X_late = X[late_mask].copy()
    y_late = y_late_days[late_mask].copy()

    print(
        f"Total rentals: {len(X)}"
    )

    print(
        f"Late rentals used for training: {len(X_late)}"
    )

    print("\nLate-day distribution:")

    print(
        y_late.describe()
    )

    categorical_features = [
        "category"
    ]

    numerical_features = [
        "rental_duration",
        "rental_rate",
        "customer_late_rate"
    ]

    # --------------------------------------------------
    # Preprocessing
    # --------------------------------------------------

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                categorical_features
            ),
            (
                "numerical",
                "passthrough",
                numerical_features
            )
        ]
    )

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    model = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor
            ),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=200,
                    max_depth=8,
                    min_samples_leaf=5,
                    random_state=42,
                    n_jobs=-1
                )
            )
        ]
    )

    # --------------------------------------------------
    # Train / test split
    # --------------------------------------------------

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X_late,
            y_late,
            test_size=0.2,
            random_state=42
        )
    )

    print("\nTraining Random Forest Regressor...")

    model.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------
    # Evaluation
    # --------------------------------------------------

    predictions = model.predict(
        X_test
    )

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    mse = mean_squared_error(
        y_test,
        predictions
    )

    rmse = mse ** 0.5

    r2 = r2_score(
        y_test,
        predictions
    )

    print("\n" + "=" * 40)
    print("EXPECTED LATE DAYS MODEL")
    print("=" * 40)

    print(
        f"MAE:  {mae:.4f}"
    )

    print(
        f"RMSE: {rmse:.4f}"
    )

    print(
        f"R²:   {r2:.4f}"
    )

    # --------------------------------------------------
    # Save model
    # --------------------------------------------------

    os.makedirs(
        "ml/models",
        exist_ok=True
    )

    model_path = (
        "ml/models/late_days.pkl"
    )

    joblib.dump(
        model,
        model_path
    )

    print(
        f"\nModel saved to: {model_path}"
    )


if __name__ == "__main__":
    train_model()
