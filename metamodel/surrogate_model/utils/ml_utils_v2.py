import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xgboost as xgb

from sklearn.model_selection import (
    train_test_split,
    RandomizedSearchCV,
    KFold,
    cross_validate,
)
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


class EmissionsPredictionPipeline:
    def __init__(
        self,
        df: pd.DataFrame,
        target: str,
        test_size: float = 0.2,
        random_state: int = 42,
    ):
        self.df = df
        self.target = target
        self.test_size = test_size
        self.random_state = random_state

        self.X_train = self.X_test = None
        self.y_train = self.y_test = None

        self.best_params: dict = {}
        self._log_transform = False  # only applies to XGB
        self.pipelines: dict[str, object] = {}  # estimators or pipelines

        # for reproducibility
        np.random.seed(self.random_state)

    # ------------------------------------------------------------------ #
    def preprocess(self):
        """Split train/test. Assumes df is already cleaned externally."""
        X = self.df.drop(columns=[self.target])
        y = self.df[self.target]
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state
        )

    # ------------------------------------------------------------------ #
    def tune_hyperparameters(self, n_iter: int = 30, cv_splits: int = 5):
        """Randomized search for XGB; uses log1p(y) if self._log_transform is True."""
        param_dist = {
            "n_estimators": [200, 400, 800, 1200],
            "learning_rate": [0.005, 0.01, 0.03, 0.1],
            "max_depth": [3, 5, 7, 9],
            "subsample": [0.6, 0.8, 1.0],
            "colsample_bytree": [0.5, 0.8, 1.0],
            "min_child_weight": [1, 3, 5, 10],
            "reg_alpha": [0.0, 0.001, 0.01, 0.1],
            "reg_lambda": [0.1, 1.0, 5.0, 10.0],
            "gamma": [0.0, 0.1, 0.3],  # optional
        }

        xgb_pipe = Pipeline(
            [
                (
                    "model",
                    xgb.XGBRegressor(
                        random_state=self.random_state,
                        tree_method="hist",
                        objective="reg:squarederror",
                        n_jobs=-1,
                    ),
                )
            ]
        )

        kf = KFold(
            n_splits=cv_splits, shuffle=True, random_state=self.random_state
        )

        search = RandomizedSearchCV(
            estimator=xgb_pipe,
            param_distributions={f"model__{k}": v for k, v in param_dist.items()},
            n_iter=n_iter,
            scoring="neg_mean_absolute_error",
            cv=kf,
            random_state=self.random_state,
            n_jobs=-1,
            verbose=1,
        )

        y_tune = np.log1p(self.y_train) if self._log_transform else self.y_train
        search.fit(self.X_train, y_tune)
        self.best_params = {
            k.replace("model__", ""): v for k, v in search.best_params_.items()
        }
        print("Best XGB hyperparameters:", self.best_params)

    # ------------------------------------------------------------------ #
    def train_models(self, log_transform: bool = False):
        """Fit XGB (with optional log1p target) + baseline models."""
        if self.X_train is None:
            raise RuntimeError("Call preprocess() first.")
        self._log_transform = log_transform

        # 1) XGBoost (fit with early stopping on a holdout eval_set)
        xgb_model = xgb.XGBRegressor(
            **self.best_params,
            random_state=self.random_state,
            tree_method="hist",
            objective="reg:squarederror",
            n_jobs=-1,
        )
        y_fit_xgb = np.log1p(self.y_train) if self._log_transform else self.y_train
        eval_y = np.log1p(self.y_test) if self._log_transform else self.y_test
        xgb_model.fit(
            self.X_train,
            y_fit_xgb,
            eval_set=[(self.X_test, eval_y)],
            # early_stopping_rounds=100,
            verbose=False,
        )
        self.pipelines["XGB"] = xgb_model  # store estimator directly

        # 2) Baselines / other models
        self.pipelines["MeanBaseline"] = Pipeline(
            [("model", DummyRegressor(strategy="mean"))]
        ).fit(self.X_train, self.y_train)

        self.pipelines["MedianBaseline"] = Pipeline(
            [("model", DummyRegressor(strategy="median"))]
        ).fit(self.X_train, self.y_train)

        self.pipelines["RandomForest"] = Pipeline(
            [
                (
                    "model",
                    RandomForestRegressor(
                        random_state=self.random_state,
                        n_jobs=-1,
                        n_estimators=500,
                    ),
                )
            ]
        ).fit(self.X_train, self.y_train)

        self.pipelines["ElasticNet"] = Pipeline(
            [
                ("scaler", StandardScaler(with_mean=True, with_std=True)),
                ("model", ElasticNet(random_state=self.random_state, max_iter=5000)),
            ]
        ).fit(self.X_train, self.y_train)

    # ------------------------------------------------------------------ #
    def evaluate_models(self):
        """Print MAE, RMSE, R², SMAPE for all models (on original scale)."""
        for name, est in self.pipelines.items():
            y_pred = est.predict(self.X_test)
            if name == "XGB" and self._log_transform:
                y_pred = np.expm1(y_pred)

            mae = mean_absolute_error(self.y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(self.y_test, y_pred))
            r2 = r2_score(self.y_test, y_pred)

            denom = (np.abs(self.y_test) + np.abs(y_pred)) / 2
            smape = (np.mean(np.where(denom == 0, 0, np.abs(self.y_test - y_pred) / denom)) * 100)

            print(
                f"{name:15s} → MAE: {mae:.4f}, RMSE: {rmse:.4f}, "
                f"R²: {r2:.4f}, SMAPE: {smape:.1f}%"
            )

    # ------------------------------------------------------------------ #
    def cross_validate(self, cv_splits: int = 5, model_names: list[str] | None = None):
        """CV on training set. For XGB, uses log1p(y) if enabled (no early stopping in CV)."""
        if model_names is None:
            model_names = list(self.pipelines.keys())

        scoring = {
            "MAE": "neg_mean_absolute_error",
            "R2": "r2",
            "RMSE": "neg_root_mean_squared_error",
        }
        kf = KFold(
            n_splits=cv_splits, shuffle=True, random_state=self.random_state
        )

        for name in model_names:
            est = self.pipelines[name]
            y_cv = np.log1p(self.y_train) if (name == "XGB" and self._log_transform) else self.y_train

            results = cross_validate(
                est,
                self.X_train,
                y_cv,
                cv=kf,
                scoring=scoring,
                n_jobs=-1,
                return_train_score=False,
            )

            print(f"\n=== CV Results for {name} ===")
            for label, scorer in scoring.items():
                vals = results[f"test_{label}"]
                mean = vals.mean()
                std = vals.std()
                if isinstance(scorer, str) and scorer.startswith("neg_"):
                    mean, std = -mean, std
                print(f"{label}: {mean:.4f} ± {std:.4f}")

    # ------------------------------------------------------------------ #
    def create_plots(self):
        """Residuals, Pred vs Actual, and top-4 feature importances (XGB only)."""
        if "XGB" not in self.pipelines:
            raise RuntimeError("Train XGB first.")

        model = self.pipelines["XGB"]
        y_pred = model.predict(self.X_test)
        if self._log_transform:
            y_pred = np.expm1(y_pred)

        residuals = self.y_test - y_pred

        # Residuals & Pred vs Actual
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        axes[0].scatter(y_pred, residuals, alpha=0.6)
        axes[0].axhline(0, linestyle="--", color="k")
        axes[0].set_xlabel("Predicted")
        axes[0].set_ylabel("Residuals")
        axes[0].set_title("Residuals vs. Predicted")

        axes[1].scatter(y_pred, self.y_test, alpha=0.6)
        mn = float(min(np.min(y_pred), np.min(self.y_test)))
        mx = float(max(np.max(y_pred), np.max(self.y_test)))
        axes[1].plot([mn, mx], [mn, mx], "k--")
        axes[1].set_xlabel("Predicted")
        axes[1].set_ylabel("Actual")
        axes[1].set_title("Predicted vs. Actual")
        plt.tight_layout()
        plt.show()

        # Feature importances (top 4)
        importances = model.feature_importances_
        features = np.array(self.X_train.columns)
        idx = np.argsort(importances)[-4:][::-1]

        plt.figure(figsize=(8, 5))
        plt.barh(features[idx][::-1], importances[idx][::-1])
        plt.title("Top 4 Feature Importances (XGB)")
        plt.tight_layout()
        plt.show()

    # ------------------------------------------------------------------ #
    def run(
        self,
        tune: bool = True,
        log_transform: bool = False,
        cv_splits: int = 5,
        create_plots: bool = True,
    ):
        """End-to-end run."""
        self._log_transform = log_transform
        self.preprocess()
        if tune:
            self.tune_hyperparameters()
        self.train_models(log_transform=log_transform)
        self.evaluate_models()
        self.cross_validate(cv_splits=cv_splits)
        if create_plots:
            self.create_plots()
    
    def predict(self, new_data: pd.DataFrame, model_name: str = "XGB") -> np.ndarray:
        """
        Predict target values for new observations using a trained model.

        Parameters
        ----------
        new_data : pd.DataFrame
            New data with the same columns and preprocessing as training data.
        model_name : str, default="XGB"
            Which trained model to use ("XGB", "RandomForest", "ElasticNet", etc.).

        Returns
        -------
        np.ndarray
            Predicted values on the original target scale.
        """
        if model_name not in self.pipelines:
            raise ValueError(
                f"Model '{model_name}' not found. Available: {list(self.pipelines.keys())}"
            )

        model = self.pipelines[model_name]

        # Ensure column order and names match training data
        X_new = new_data.copy()
        missing_cols = set(self.X_train.columns) - set(X_new.columns)
        if missing_cols:
            raise ValueError(f"Missing columns in new data: {missing_cols}")

        # Reorder columns to match training
        X_new = X_new[self.X_train.columns]

        # Make predictions
        if model_name == "XGB":
            # Respect early stopping best_iteration if available
            if hasattr(model, "best_iteration") and model.best_iteration is not None:
                try:
                    y_pred = model.predict(
                        X_new, iteration_range=(0, model.best_iteration + 1)
                    )
                except TypeError:
                    y_pred = model.predict(
                        X_new, ntree_limit=model.best_iteration + 1
                    )
            else:
                y_pred = model.predict(X_new)

            # Apply inverse log-transform if needed
            if self._log_transform:
                y_pred = np.expm1(y_pred)

        else:
            y_pred = model.predict(X_new)

        return y_pred

