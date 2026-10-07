# Brings in the libraries, shared code, and test or runtime settings needed below.
import os
from pathlib import Path
import joblib
import pandas as pd
from apps.services.common.sagemaker_adapter import get_runtime_adapter

ROOT = Path(__file__).resolve().parents[3]

# Keeps model loading and feature preparation separate from HTTP handling.
class InferenceEngine:
    """Model loading and feature transformation, independent of HTTP handling."""
    # Stores the provider/model path and injected adapter. Local mode loads the artifact and
    # recommendation catalog; failed loading makes readiness fail.
    def __init__(self, service, provider=None, model_path=None, adapter=None):
        self.service = service
        self.provider = provider or os.getenv('MODEL_PROVIDER', 'local')
        self.path = Path(model_path or os.getenv('MODEL_PATH', str(ROOT / 'ml/models' / f'{service}_model.joblib')))
        self.adapter = adapter or get_runtime_adapter(service)
        self.model = None
        self.catalog = None
        if self.provider == 'local':
            try:
                self.model = joblib.load(self.path)
                if service == 'recommendations':
                    data_path = os.getenv('RECOMMENDATIONS_CATALOG_PATH', str(ROOT / 'data/raw/recommendations_data.csv'))
                    self.catalog = pd.read_csv(data_path)
                    self.categories = sorted(self.catalog.category.unique())
                    self.items = sorted(self.catalog.item_id.unique())
            except Exception:
                # Keep process live so /ready can expose unavailable artifacts.
                self.model = None

    # Checks remote endpoint/region configuration, or whether the local model was loaded.
    def ready(self):
        if self.provider == 'sagemaker':
            return self.adapter.is_configured()
        return self.provider == 'local' and self.model is not None

    # In SageMaker mode, invokes AWS and labels the result remote. In local mode, prepares fraud
    # fields, iterates forecast lags, or ranks recommendation candidates by probability.
    def predict(self, payload):
        if self.provider == 'sagemaker':
            return {**self.adapter.invoke(payload), 'provider': 'sagemaker'}
        # Uses the model’s class prediction and probability of the fraud class.
        if self.service == 'fraud':
            features = pd.DataFrame([payload], columns=['amount', 'transaction_count', 'account_age_days'])
            label = int(self.model.predict(features)[0])
            score = self.model.predict_proba(features)[0][list(self.model.classes_).index(1)]
            result = {'prediction': 'fraud' if label == 1 else 'legitimate', 'risk_score': round(float(score), 4)}
        # Reverses the latest history into lag 1/2/3, pads short history, and appends each new
        # forecast before predicting again.
        elif self.service == 'forecasting':
            history = list(payload['values'])
            forecast = []
            for _ in range(payload['periods']):
                lags = list(reversed(history[-3:]))
                lags += [history[0]] * (3 - len(lags))
                features = pd.DataFrame([lags], columns=['lag_1', 'lag_2', 'lag_3'])
                value = float(self.model.predict(features)[0])
                forecast.append(round(value, 2))
                history.append(value)
            result = {'forecast': forecast, 'periods': payload['periods']}
        else:
            category = payload['category']
            if category not in self.categories:
                raise ValueError('Unknown category; choose: ' + ', '.join(self.categories))
            # Filters the catalog by category, scores candidate items, sorts highest probability
            # first, and returns up to the requested limit.
            candidates = sorted(self.catalog.loc[self.catalog.category == category, 'item_id'].unique())
            features = pd.DataFrame([{'user_id': payload['user_id'], 'category': self.categories.index(category),
                'item_id': self.items.index(item)} for item in candidates])
            scores = self.model.predict_proba(features)[:, list(self.model.classes_).index(1)]
            ranked = sorted(zip(candidates, scores), key=lambda pair: (-float(pair[1]), pair[0]))
            result = {'user_id': payload['user_id'], 'recommendations': [
                {'item_id': item, 'category': category, 'score': round(float(score), 4)}
                for item, score in ranked[:payload['limit']]]}
        return {**result, 'model': f'{self.service}-model-v1', 'provider': 'local'}
