from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / 'data' / 'raw' / 'recommendations_data.csv'
MODEL_PATH = ROOT / 'ml' / 'models' / 'recommendations_model.joblib'


def main() -> None:
    df = pd.read_csv(DATA_PATH)

    required = {'user_id', 'category', 'item_id', 'rating', 'clicked'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')

    df['category'] = df['category'].astype('category').cat.codes
    features = df[['user_id', 'category', 'item_id']].copy()
    features['item_id'] = features['item_id'].astype('category').cat.codes
    y = df['clicked']

    X_train, X_test, y_train, y_test = train_test_split(
        features, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        max_depth=8,
        min_samples_leaf=2,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f'Model accuracy: {acc:.4f}')

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f'Model saved to {MODEL_PATH}')


if __name__ == '__main__':
    main()
