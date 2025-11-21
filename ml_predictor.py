"""
Machine Learning module for predicting player prop outcomes
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
import xgboost as xgb
import joblib
from datetime import datetime
import logging
from config import (
    PLAYER_STATS_CSV, PREDICTIONS_CSV, MODELS_DIR,
    CONFIDENCE_THRESHOLD, MIN_SAMPLES_FOR_TRAINING,
    FEATURE_COLUMNS, TARGET_COLUMN, TEST_SIZE, RANDOM_STATE
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PropPredictor:
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.model_path = f"{MODELS_DIR}/prop_model.pkl"
        self.scaler_path = f"{MODELS_DIR}/scaler.pkl"
        
    def prepare_training_data(self, historical_df):
        """
        Prepare data for training
        Requires historical game data with actual outcomes
        """
        # Filter out rows with missing critical data
        required_cols = ['points', 'rebounds', 'assists', 'line', 'hit_line']
        df = historical_df.dropna(subset=required_cols)
        
        if len(df) < MIN_SAMPLES_FOR_TRAINING:
            logger.error(f"Insufficient training data: {len(df)} samples (need {MIN_SAMPLES_FOR_TRAINING})")
            return None, None
        
        # Create features
        df = self.engineer_features(df)
        
        # Define feature columns dynamically based on available data
        available_features = [col for col in FEATURE_COLUMNS if col in df.columns]
        
        if not available_features:
            logger.error("No valid features available for training")
            return None, None
        
        X = df[available_features]
        y = df[TARGET_COLUMN]
        
        # Handle any remaining NaN values - fill with 0
        X = X.fillna(0)
        
        # Remove any infinite values
        X = X.replace([np.inf, -np.inf], 0)
        
        logger.info(f"Prepared {len(X)} samples with {len(available_features)} features")
        self.feature_columns = available_features
        
        return X, y
    
    def engineer_features(self, df):
        """Create additional features for the model"""
        # Calculate combined stat average
        if all(col in df.columns for col in ['points', 'rebounds', 'assists']):
            df['pts_reb_ast_avg'] = df['points'] + df['rebounds'] + df['assists']
        
        # Calculate how far above/below line
        if 'pts_reb_ast_avg' in df.columns and 'line' in df.columns:
            df['over_under_margin'] = df['pts_reb_ast_avg'] - df['line']
        
        # Home/away encoding
        if 'home_away' in df.columns:
            df['home_away'] = df['home_away'].map({'home': 1, 'away': 0})
        
        # Recent form features (last 5 games)
        for stat in ['points', 'rebounds', 'assists']:
            last_5_col = f'{stat}_last_5'
            if last_5_col not in df.columns and stat in df.columns:
                df[last_5_col] = df.groupby('player_name')[stat].transform(
                    lambda x: x.rolling(5, min_periods=1).mean()
                )
        
        # Fill any created NaN values
        for col in df.columns:
            if df[col].dtype in ['float64', 'int64']:
                df[col] = df[col].fillna(df[col].mean())
        
        return df
    
    def train_model(self, X, y):
        """Train ensemble of models"""
        # Clean any remaining NaN values
        X = X.fillna(0)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
        )
        
        # Fill any NaN in splits
        X_train = X_train.fillna(0)
        X_test = X_test.fillna(0)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Replace any NaN that might have been introduced by scaling
        X_train_scaled = np.nan_to_num(X_train_scaled, nan=0.0, posinf=0.0, neginf=0.0)
        X_test_scaled = np.nan_to_num(X_test_scaled, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Train multiple models
        models_config = {
            'random_forest': RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=RANDOM_STATE,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=RANDOM_STATE
            ),
            'xgboost': xgb.XGBClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=RANDOM_STATE,
                eval_metric='logloss'
            )
        }
        
        results = {}
        
        for model_name, model in models_config.items():
            logger.info(f"Training {model_name}...")
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            auc = roc_auc_score(y_test, y_pred_proba)
            
            results[model_name] = {
                'model': model,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'auc': auc
            }
            
            logger.info(f"{model_name} - Accuracy: {accuracy:.3f}, Precision: {precision:.3f}, Recall: {recall:.3f}, AUC: {auc:.3f}")
        
        # Select best model based on AUC
        best_model_name = max(results, key=lambda x: results[x]['auc'])
        best_model = results[best_model_name]['model']
        
        logger.info(f"Best model: {best_model_name} with AUC: {results[best_model_name]['auc']:.3f}")
        
        self.models['best'] = best_model
        self.models['all'] = {k: v['model'] for k, v in results.items()}
        
        # Save model and scaler
        self.save_model()
        
        return results
    
    def predict(self, X):
        """Make predictions with confidence scores"""
        if 'best' not in self.models:
            logger.error("No trained model available")
            return None, None
        
        # Ensure features match training
        X = X[self.feature_columns]
        X = X.fillna(0)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Handle any NaN from scaling
        X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Get predictions from best model
        predictions = self.models['best'].predict(X_scaled)
        probabilities = self.models['best'].predict_proba(X_scaled)[:, 1]
        
        return predictions, probabilities
    
    def predict_high_confidence(self, player_data_df, line):
        """
        Predict high-confidence plays (>90% probability)
        """
        # Prepare features
        df = player_data_df.copy()
        df['line'] = line
        
        # Create target placeholder (will be predicted)
        df['hit_line'] = 0
        
        # Engineer features
        df = self.engineer_features(df)
        
        # Get features
        available_features = [col for col in self.feature_columns if col in df.columns]
        X = df[available_features]
        
        # Predict
        predictions, probabilities = self.predict(X)
        
        if predictions is None:
            return None
        
        # Filter for high confidence
        high_conf_mask = probabilities >= CONFIDENCE_THRESHOLD
        
        results = pd.DataFrame({
            'player': df.index,
            'predicted_hit': predictions,
            'confidence': probabilities,
            'line': line,
            'high_confidence': high_conf_mask
        })
        
        return results[results['high_confidence']]
    
    def save_model(self):
        """Save trained model and scaler"""
        joblib.dump(self.models, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        joblib.dump(self.feature_columns, f"{MODELS_DIR}/features.pkl")
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load trained model and scaler"""
        try:
            self.models = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            self.feature_columns = joblib.load(f"{MODELS_DIR}/features.pkl")
            logger.info("Model loaded successfully")
            return True
        except FileNotFoundError:
            logger.warning("No saved model found")
            return False
    
    def get_feature_importance(self):
        """Get feature importance from the best model"""
        if 'best' not in self.models:
            return None
        
        model = self.models['best']
        
        if hasattr(model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            return importance_df
        
        return None


def create_synthetic_training_data():
    """
    Create synthetic training data for initial model training
    This simulates historical player performance data
    """
    np.random.seed(42)
    n_samples = 1000
    
    # Generate base statistics
    points_avg = np.random.uniform(8, 30, n_samples)
    rebounds_avg = np.random.uniform(2, 12, n_samples)
    assists_avg = np.random.uniform(1, 10, n_samples)
    
    data = {
        'player_name': [f'Player_{i%50}' for i in range(n_samples)],
        'games_played': np.random.randint(10, 82, n_samples),
        'minutes_avg': np.random.uniform(20, 38, n_samples),
        'points_avg': points_avg,
        'rebounds_avg': rebounds_avg,
        'assists_avg': assists_avg,
        'points_last_5': points_avg + np.random.normal(0, 2, n_samples),
        'rebounds_last_5': rebounds_avg + np.random.normal(0, 1, n_samples),
        'assists_last_5': assists_avg + np.random.normal(0, 1, n_samples),
        'home_away': np.random.choice([0, 1], n_samples),
        'days_rest': np.random.randint(0, 5, n_samples),
        'opponent_def_rating': np.random.uniform(95, 120, n_samples),
        'usage_rate': np.random.uniform(0.15, 0.35, n_samples),
        'true_shooting_pct': np.random.uniform(0.45, 0.65, n_samples),
    }
    
    df = pd.DataFrame(data)
    
    # Calculate combined averages
    df['pts_reb_ast_avg'] = df['points_avg'] + df['rebounds_avg'] + df['assists_avg']
    
    # Set line slightly below average (to create realistic betting lines)
    df['line'] = df['pts_reb_ast_avg'] - np.random.uniform(0, 3, n_samples)
    
    # Generate actual performance with some variance
    df['points'] = df['points_avg'] + np.random.normal(0, 4, n_samples)
    df['rebounds'] = df['rebounds_avg'] + np.random.normal(0, 2, n_samples)
    df['assists'] = df['assists_avg'] + np.random.normal(0, 2, n_samples)
    
    # Ensure no negative values
    df['points'] = df['points'].clip(lower=0)
    df['rebounds'] = df['rebounds'].clip(lower=0)
    df['assists'] = df['assists'].clip(lower=0)
    
    # Calculate actual total
    df['actual_total'] = df['points'] + df['rebounds'] + df['assists']
    
    # Determine if line was hit
    df['hit_line'] = (df['actual_total'] >= df['line']).astype(int)
    
    # Replace any NaN or inf values with 0
    df = df.fillna(0)
    df = df.replace([np.inf, -np.inf], 0)
    
    return df


if __name__ == "__main__":
    predictor = PropPredictor()
    
    # For initial training, create synthetic data
    print("Creating training data...")
    train_df = create_synthetic_training_data()
    
    print(f"Training data shape: {train_df.shape}")
    print(f"Hit rate: {train_df['hit_line'].mean():.2%}")
    
    # Prepare and train
    print("\nPreparing features...")
    X, y = predictor.prepare_training_data(train_df)
    
    if X is not None:
        print("\nTraining models...")
        results = predictor.train_model(X, y)
        
        print("\nTraining completed!")
        print("\nFeature importance:")
        importance = predictor.get_feature_importance()
        if importance is not None:
            print(importance.head(10))
