# Loads file-path helpers, data tools, a random-forest model, and evaluation functions.
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# Locates the raw CSV and output model file relative to the project.
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / 'data' / 'raw' / 'recommendations_data.csv'
MODEL_PATH = ROOT / 'ml' / 'models' / 'recommendations_model.joblib'


def main() -> None:
    # Loads the CSV into a table.
    df = pd.read_csv(DATA_PATH)

    # Rejects input data that is missing required fields.
    required = {'user_id', 'category', 'item_id', 'rating', 'clicked'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')

    # Converts category/item names to numeric codes and uses clicked as the target.
    df['category'] = df['category'].astype('category').cat.codes
    features = df[['user_id', 'category', 'item_id']].copy()
    features['item_id'] = features['item_id'].astype('category').cat.codes
    y = df['clicked']

    # Holds out 20 percent for evaluation, with a repeatable random seed; classifiers keep the
    # class proportions.
    X_train, X_test, y_train, y_test = train_test_split(
        features, y, test_size=0.2, random_state=42, stratify=y
    )

    # Creates a random forest: many decision trees voting on a class or averaging a numeric value.
    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        max_depth=8,
        min_samples_leaf=2,
    )
    # Learns patterns from the training portion.
    model.fit(X_train, y_train)

    # Predicts held-out examples and prints MAE for forecasting or accuracy for classification.
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f'Model accuracy: {acc:.4f}')

    # Creates the model folder if needed and saves the trained object with joblib.
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f'Model saved to {MODEL_PATH}')


# Runs training only when the file is executed directly.
if __name__ == '__main__':
    main()
