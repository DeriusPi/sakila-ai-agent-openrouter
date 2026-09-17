import os
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
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

from ml.feature_engineering import get_features_and_targets


def train_model():

    print("Loading data...")

    X, y_probability, _ = get_features_and_targets()

    print(
        f"Training rows: {len(X)}"
    )

    categorical_features = [
        "category"
    ]

    numerical_features = [
        "rental_duration",
        "rental_rate",
        "customer_late_rate"
    ]

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

    model = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000
                )
            )
        ]
    )

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y_probability,
            test_size=0.2,
            random_state=42,
            stratify=y_probability
        )
    )

    print("\nTraining Logistic Regression...")

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    print("\n" + "=" * 40)
    print("LATE PROBABILITY MODEL")
    print("=" * 40)

    print(
        f"Accuracy:  "
        f"{accuracy_score(y_test, predictions):.4f}"
    )

    print(
        f"Precision: "
        f"{precision_score(y_test, predictions):.4f}"
    )

    print(
        f"Recall:    "
        f"{recall_score(y_test, predictions):.4f}"
    )

    print(
        f"F1 Score:  "
        f"{f1_score(y_test, predictions):.4f}"
    )

    print(
        f"ROC-AUC:   "
        f"{roc_auc_score(y_test, probabilities):.4f}"
    )

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions
        )
    )

    os.makedirs(
        "ml/models",
        exist_ok=True
    )

    model_path = (
        "ml/models/late_probability.pkl"
    )

    joblib.dump(
        model,
        model_path
    )

    print(
        f"Model saved to: {model_path}"
    )


if __name__ == "__main__":
    train_model()
