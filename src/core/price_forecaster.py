"""
Enhanced Price Forecasting Module
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from src.brokers.base import BrokerInterface

logger = logging.getLogger(__name__)


class PriceForecaster:
    """
    Enhanced price forecasting using multiple models and techniques
    """

    def __init__(self, broker_adapter: BrokerInterface) -> None:
        self.broker_adapter = broker_adapter
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}

    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare technical features for price prediction

        Args:
            data: OHLCV data with columns: open, high, low, close, volume

        Returns:
            DataFrame with engineered features
        """
        df = data.copy()

        # Price-based features
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        df["high_low_ratio"] = df["high"] / df["low"]
        df["close_open_ratio"] = df["close"] / df["open"]

        # Moving averages
        for window in [5, 10, 20, 50]:
            df[f"sma_{window}"] = df["close"].rolling(window=window).mean()
            df[f"ema_{window}"] = df["close"].ewm(span=window).mean()
            df[f"price_sma_{window}_ratio"] = df["close"] / df[f"sma_{window}"]

        # Volatility features
        df["volatility_10"] = df["returns"].rolling(window=10).std()
        df["volatility_20"] = df["returns"].rolling(window=20).std()

        # Technical indicators
        df["rsi"] = self._calculate_rsi(df["close"], 14)
        df["bb_upper"], df["bb_lower"] = self._calculate_bollinger_bands(df["close"], 20, 2)
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        # MACD
        df["macd"], df["macd_signal"] = self._calculate_macd(df["close"])
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

        # Volume features
        df["volume_sma_10"] = df["volume"].rolling(window=10).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma_10"]
        df["price_volume"] = df["close"] * df["volume"]

        # Momentum features
        for period in [5, 10, 20]:
            df[f"momentum_{period}"] = df["close"] / df["close"].shift(period) - 1

        # Lag features
        for lag in [1, 2, 3, 5]:
            df[f"close_lag_{lag}"] = df["close"].shift(lag)
            df[f"returns_lag_{lag}"] = df["returns"].shift(lag)
            df[f"volume_lag_{lag}"] = df["volume"].shift(lag)

        # Time-based features
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df["day_of_week"] = df["date"].dt.dayofweek
            df["day_of_month"] = df["date"].dt.day
            df["month"] = df["date"].dt.month
            df["quarter"] = df["date"].dt.quarter

        # Drop infinite and NaN values
        df = df.replace([np.inf, -np.inf], np.nan)
        return df.fillna(method="ffill").fillna(method="bfill")

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> tuple[pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, lower

    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal

    def train_model(
        self,
        symbol: str,
        data: pd.DataFrame,
        model_type: str = "random_forest",
        target_days: int = 1,
    ) -> dict[str, Any]:
        """
        Train a price prediction model for a symbol

        Args:
            symbol: Stock symbol
            data: Historical OHLCV data
            model_type: Type of model ('random_forest', 'linear_regression')
            target_days: Number of days ahead to predict

        Returns:
            Dictionary with model performance metrics
        """
        try:
            # Prepare features
            df_features = self.prepare_features(data)

            # Create target variable (future price)
            df_features[f"target_price_{target_days}d"] = df_features["close"].shift(-target_days)
            df_features[f"target_return_{target_days}d"] = df_features[f"target_price_{target_days}d"] / df_features["close"] - 1

            # Remove rows with NaN targets
            df_clean = df_features.dropna()

            if len(df_clean) < 50:
                msg = f"Insufficient data for training: {len(df_clean)} rows"
                raise ValueError(msg)

            # Select features for training
            feature_columns = [col for col in df_clean.columns if col not in ["date", "target_price_1d", "target_return_1d", "close"] and not col.startswith("target_")]

            X = df_clean[feature_columns]
            y = df_clean[f"target_return_{target_days}d"]  # Predict returns instead of absolute prices

            # Split data for training and validation
            split_idx = int(len(X) * 0.8)
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)

            # Train model
            if model_type == "random_forest":
                model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42,
                )
            elif model_type == "linear_regression":
                model = LinearRegression()
            else:
                msg = f"Unknown model type: {model_type}"
                raise ValueError(msg)

            model.fit(X_train_scaled, y_train)

            # Make predictions
            y_pred_train = model.predict(X_train_scaled)
            y_pred_val = model.predict(X_val_scaled)

            # Calculate metrics
            train_mse = mean_squared_error(y_train, y_pred_train)
            val_mse = mean_squared_error(y_val, y_pred_val)
            train_r2 = r2_score(y_train, y_pred_train)
            val_r2 = r2_score(y_val, y_pred_val)

            # Store model and scaler
            model_key = f"{symbol}_{model_type}_{target_days}d"
            self.models[model_key] = model
            self.scalers[model_key] = scaler

            # Feature importance (for random forest)
            if model_type == "random_forest":
                feature_importance = dict(zip(feature_columns, model.feature_importances_, strict=False))
                self.feature_importance[model_key] = feature_importance

            metrics = {
                "symbol": symbol,
                "model_type": model_type,
                "target_days": target_days,
                "train_mse": train_mse,
                "val_mse": val_mse,
                "train_r2": train_r2,
                "val_r2": val_r2,
                "feature_count": len(feature_columns),
                "training_samples": len(X_train),
                "validation_samples": len(X_val),
                "feature_importance": self.feature_importance.get(model_key, {}),
                "training_date": datetime.now(),
            }

            logger.info(f"Trained {model_type} model for {symbol}: Val R2={val_r2:.3f}, Val MSE={val_mse:.6f}")
            return metrics

        except Exception as e:
            logger.exception(f"Error training model for {symbol}: {e}")
            raise

    def predict_price(
        self,
        symbol: str,
        data: pd.DataFrame,
        model_type: str = "random_forest",
        target_days: int = 1,
    ) -> dict[str, Any]:
        """
        Predict future price for a symbol

        Args:
            symbol: Stock symbol
            data: Recent OHLCV data
            model_type: Type of model to use
            target_days: Number of days ahead to predict

        Returns:
            Dictionary with prediction results
        """
        try:
            model_key = f"{symbol}_{model_type}_{target_days}d"

            if model_key not in self.models:
                msg = f"No trained model found for {model_key}"
                raise ValueError(msg)

            model = self.models[model_key]
            scaler = self.scalers[model_key]

            # Prepare features
            df_features = self.prepare_features(data)

            # Get the latest row for prediction
            latest_data = df_features.iloc[-1:]

            # Select features (same as training)
            feature_columns = [col for col in df_features.columns if col not in ["date", "target_price_1d", "target_return_1d", "close"] and not col.startswith("target_")]

            X_latest = latest_data[feature_columns]

            # Handle missing values
            X_latest = X_latest.fillna(method="ffill").fillna(0)

            # Scale features
            X_scaled = scaler.transform(X_latest)

            # Make prediction
            predicted_return = model.predict(X_scaled)[0]
            current_price = data["close"].iloc[-1]
            predicted_price = current_price * (1 + predicted_return)

            # Calculate confidence based on model performance
            model_metrics = getattr(model, "_metrics", {})
            confidence = max(0, min(1, model_metrics.get("val_r2", 0.5)))

            prediction_result = {
                "symbol": symbol,
                "current_price": current_price,
                "predicted_price": predicted_price,
                "predicted_return": predicted_return,
                "predicted_change_percent": predicted_return * 100,
                "target_days": target_days,
                "confidence": confidence,
                "model_type": model_type,
                "prediction_date": datetime.now(),
                "model_key": model_key,
            }

            # Add feature importance if available
            if model_key in self.feature_importance:
                top_features = sorted(
                    self.feature_importance[model_key].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
                prediction_result["top_features"] = top_features

            return prediction_result

        except Exception as e:
            logger.exception(f"Error predicting price for {symbol}: {e}")
            raise

    def batch_predict(
        self,
        symbols: list[str],
        model_type: str = "random_forest",
        target_days: int = 1,
        min_data_points: int = 100,
    ) -> dict[str, dict[str, Any]]:
        """
        Make predictions for multiple symbols

        Args:
            symbols: List of stock symbols
            model_type: Type of model to use
            target_days: Number of days ahead to predict
            min_data_points: Minimum data points required

        Returns:
            Dictionary with predictions for each symbol
        """
        predictions = {}

        for symbol in symbols:
            try:
                # Get recent data for the symbol
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=200)  # Get enough data for features

                data = self.alpaca_client.stock.history.get_stock_data(
                    symbol=symbol,
                    start=str(start_date),
                    end=str(end_date),
                    timeframe="1d",
                )

                if len(data) < min_data_points:
                    logger.warning(f"Insufficient data for {symbol}: {len(data)} points")
                    continue

                # Check if model exists, if not train it
                model_key = f"{symbol}_{model_type}_{target_days}d"
                if model_key not in self.models:
                    logger.info(f"Training new model for {symbol}")
                    self.train_model(symbol, data, model_type, target_days)

                # Make prediction
                prediction = self.predict_price(symbol, data, model_type, target_days)
                predictions[symbol] = prediction

            except Exception as e:
                logger.exception(f"Error in batch prediction for {symbol}: {e}")
                predictions[symbol] = {"error": str(e), "symbol": symbol}

        return predictions

    def get_forecast_signals(
        self,
        predictions: dict[str, dict[str, Any]],
        min_confidence: float = 0.6,
        min_return_threshold: float = 0.03,
    ) -> list[dict[str, Any]]:
        """
        Convert price predictions to trading signals

        Args:
            predictions: Dictionary of price predictions
            min_confidence: Minimum confidence threshold
            min_return_threshold: Minimum expected return threshold (3%)

        Returns:
            List of trading signals
        """
        signals = []

        for symbol, prediction in predictions.items():
            if "error" in prediction:
                continue

            confidence = prediction.get("confidence", 0)
            predicted_return = prediction.get("predicted_return", 0)

            if confidence < min_confidence:
                continue

            # Generate buy signal for positive predictions
            if predicted_return > min_return_threshold:
                signals.append(
                    {
                        "symbol": symbol,
                        "strategy_name": "price_forecast",
                        "signal_type": "buy",
                        "strength": min(1.0, predicted_return / 0.1),  # Scale by 10% max return
                        "confidence": confidence,
                        "price": prediction["current_price"],
                        "timestamp": datetime.now(),
                        "metadata": {
                            "predicted_price": prediction["predicted_price"],
                            "predicted_return": predicted_return,
                            "target_days": prediction["target_days"],
                            "model_type": prediction["model_type"],
                        },
                    }
                )

            # Generate sell signal for negative predictions
            elif predicted_return < -min_return_threshold:
                signals.append(
                    {
                        "symbol": symbol,
                        "strategy_name": "price_forecast",
                        "signal_type": "sell",
                        "strength": min(1.0, abs(predicted_return) / 0.1),
                        "confidence": confidence,
                        "price": prediction["current_price"],
                        "timestamp": datetime.now(),
                        "metadata": {
                            "predicted_price": prediction["predicted_price"],
                            "predicted_return": predicted_return,
                            "target_days": prediction["target_days"],
                            "model_type": prediction["model_type"],
                        },
                    }
                )

        # Sort signals by strength * confidence
        signals.sort(key=lambda s: s["strength"] * s["confidence"], reverse=True)

        return signals

    def retrain_models(
        self,
        symbols: list[str],
        model_type: str = "random_forest",
        target_days: int = 1,
    ) -> dict[str, dict[str, Any]]:
        """
        Retrain models for symbols with fresh data

        Args:
            symbols: List of symbols to retrain
            model_type: Type of model to train
            target_days: Number of days ahead to predict

        Returns:
            Dictionary with training results
        """
        results = {}

        for symbol in symbols:
            try:
                # Get fresh data
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=500)  # Get more data for better training

                data = self.alpaca_client.stock.history.get_stock_data(
                    symbol=symbol,
                    start=str(start_date),
                    end=str(end_date),
                    timeframe="1d",
                )

                # Train model
                metrics = self.train_model(symbol, data, model_type, target_days)
                results[symbol] = metrics

            except Exception as e:
                logger.exception(f"Error retraining model for {symbol}: {e}")
                results[symbol] = {"error": str(e), "symbol": symbol}

        return results

    def get_model_performance_summary(self) -> dict[str, Any]:
        """Get summary of all trained models' performance"""
        summary = {
            "total_models": len(self.models),
            "models_by_type": {},
            "average_performance": {},
            "model_details": [],
        }

        for model_key, model in self.models.items():
            parts = model_key.split("_")
            symbol = parts[0]
            model_type = "_".join(parts[1:-1])
            target_days = parts[-1]

            # Count by type
            if model_type not in summary["models_by_type"]:
                summary["models_by_type"][model_type] = 0
            summary["models_by_type"][model_type] += 1

            # Model details
            metrics = getattr(model, "_metrics", {})
            summary["model_details"].append(
                {
                    "symbol": symbol,
                    "model_type": model_type,
                    "target_days": target_days,
                    "val_r2": metrics.get("val_r2", 0),
                    "val_mse": metrics.get("val_mse", 0),
                }
            )

        return summary
