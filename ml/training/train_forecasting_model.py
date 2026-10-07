# Loads file-path helpers, data tools, a random-forest model, and evaluation functions.
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

# Locates the raw CSV and output model file relative to the project.
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / 'data' / 'raw' / 'forecasting_data.csv'
MODEL_PATH = ROOT / 'ml' / 'models' / 'forecasting_model.joblib'


def main() -> None:
    # Loads the CSV into a table.
    df = pd.read_csv(DATA_PATH)

    # Rejects input data that is missing required fields.
    required = {'timestamp', 'value'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')

    # Builds newest-first lag features from time-sorted history.
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['lag_1'] = df['value'].shift(1)
    df['lag_2'] = df['value'].shift(2)
    df['lag_3'] = df['value'].shift(3)
    df = df.dropna().reset_index(drop=True)

    X = df[['lag_1', 'lag_2', 'lag_3']]
    y = df['value']

    # Holds out 20 percent for evaluation, with a repeatable random seed; classifiers keep the
    # class proportions.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Creates a random forest: many decision trees voting on a class or averaging a numeric value.
    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        max_depth=8,
    )
    # Learns patterns from the training portion.
    model.fit(X_train, y_train)

    # Predicts held-out examples and prints MAE for forecasting or accuracy for classification.
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    print(f'Model MAE: {mae:.4f}')

    # Creates the model folder if needed and saves the trained object with joblib.
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f'Model saved to {MODEL_PATH}')


# Runs training only when the file is executed directly.
if __name__ == '__main__':
    main()
