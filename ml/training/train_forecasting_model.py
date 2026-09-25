from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / 'data' / 'raw' / 'forecasting_data.csv'
MODEL_PATH = ROOT / 'ml' / 'models' / 'forecasting_model.joblib'


def main() -> None:
    df = pd.read_csv(DATA_PATH)

    required = {'timestamp', 'value'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')

    df = df.sort_values('timestamp').reset_index(drop=True)
    df['lag_1'] = df['value'].shift(1)
    df['lag_2'] = df['value'].shift(2)
    df['lag_3'] = df['value'].shift(3)
    df = df.dropna().reset_index(drop=True)

    X = df[['lag_1', 'lag_2', 'lag_3']]
    y = df['value']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        max_depth=8,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    print(f'Model MAE: {mae:.4f}')

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f'Model saved to {MODEL_PATH}')


if __name__ == '__main__':
    main()
