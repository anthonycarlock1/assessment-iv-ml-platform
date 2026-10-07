# Loads file-path helpers, data tools, a random-forest model, and evaluation functions.
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# Locates the raw CSV and output model file relative to the project.
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / 'data' / 'raw' / 'fraud_assessment_dataset.csv'
MODEL_PATH = ROOT / 'ml' / 'models' / 'fraud_model.joblib'


def main() -> None:
    # Loads the CSV into a table.
    df = pd.read_csv(DATA_PATH)

    # Rejects input data that is missing required fields.
    required = {'amount', 'transaction_count', 'account_age_days', 'fraud'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')

    # Uses amount, transaction count, and account age to predict the fraud label.
    X = df[['amount', 'transaction_count', 'account_age_days']]
    y = df['fraud']

    # Holds out 20 percent for evaluation, with a repeatable random seed; classifiers keep the
    # class proportions.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Creates a random forest: many decision trees voting on a class or averaging a numeric value.
    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        max_depth=6,
        min_samples_leaf=2,
    )
    # Learns patterns from the training portion.
    model.fit(X_train, y_train)

    # Predicts held-out examples and prints MAE for forecasting or accuracy for classification.
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f'Model accuracy: {accuracy:.4f}')

    # Creates the model folder if needed and saves the trained object with joblib.
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f'Model saved to {MODEL_PATH}')


# Runs training only when the file is executed directly.
if __name__ == '__main__':
    main()
