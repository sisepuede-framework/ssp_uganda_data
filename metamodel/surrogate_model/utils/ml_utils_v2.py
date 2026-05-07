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
import warnings
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.multioutput import MultiOutputRegressor


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

        # NEW: track which features a given model expects (full or subset)
        self.model_features: dict[str, list[str]] = {}

        # store eval results for quick comparison
        self._eval_table: pd.DataFrame | None = None

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
            "gamma": [0.0, 0.1, 0.3],
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
    def _fit_xgb(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        name: str,
    ) -> xgb.XGBRegressor:
        """Internal: fit a single XGB model respecting log transform."""
        model = xgb.XGBRegressor(
            **self.best_params,
            random_state=self.random_state,
            tree_method="hist",
            objective="reg:squarederror",
            n_jobs=-1,
        )
        y_fit = np.log1p(y_train) if self._log_transform else y_train
        y_eval = np.log1p(y_val) if self._log_transform else y_val

        model.fit(
            X_train,
            y_fit,
            eval_set=[(X_val, y_eval)],
            verbose=False,
        )
        self.pipelines[name] = model
        self.model_features[name] = list(X_train.columns)
        return model

    # ------------------------------------------------------------------ #
    def train_models(self, log_transform: bool = False):
        """Fit XGB (with optional log1p) + baseline models (full feature set)."""
        if self.X_train is None:
            raise RuntimeError("Call preprocess() first.")
        self._log_transform = log_transform

        # 1) Full XGB
        self._fit_xgb(
            self.X_train, self.y_train, self.X_test, self.y_test, name="XGB"
        )

        # 2) Baselines / other models
        self.pipelines["MeanBaseline"] = Pipeline(
            [("model", DummyRegressor(strategy="mean"))]
        ).fit(self.X_train, self.y_train)
        self.model_features["MeanBaseline"] = list(self.X_train.columns)

        self.pipelines["MedianBaseline"] = Pipeline(
            [("model", DummyRegressor(strategy="median"))]
        ).fit(self.X_train, self.y_train)
        self.model_features["MedianBaseline"] = list(self.X_train.columns)

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
        self.model_features["RandomForest"] = list(self.X_train.columns)

        self.pipelines["ElasticNet"] = Pipeline(
            [
                ("scaler", StandardScaler(with_mean=True, with_std=True)),
                ("model", ElasticNet(random_state=self.random_state, max_iter=5000)),
            ]
        ).fit(self.X_train, self.y_train)
        self.model_features["ElasticNet"] = list(self.X_train.columns)

    # ------------------------------------------------------------------ #
    def _top_k_by_importance(self, k: int) -> list[str]:
        """
        Get top-k feature names from the already-trained full XGB model.
        Falls back to all features if k >= n_features.
        """
        if "XGB" not in self.pipelines:
            raise RuntimeError("Train the full XGB first.")
        model = self.pipelines["XGB"]
        importances = getattr(model, "feature_importances_", None)
        if importances is None:
            raise RuntimeError("XGB feature_importances_ not available.")
        feats = np.array(self.model_features["XGB"])
        k = min(k, len(feats))
        idx = np.argsort(importances)[-k:][::-1]
        return feats[idx].tolist()

    # ------------------------------------------------------------------ #
    def train_reduced_xgboosts(self, ks: list[int] = [10, 5]):
        """
        Train reduced XGB models using top-k features derived from the full XGB.
        Stores models as 'XGB_top{k}'.
        """
        if self.X_train is None or "XGB" not in self.pipelines:
            raise RuntimeError("Call train_models() to fit the full XGB first.")

        for k in ks:
            topk_feats = self._top_k_by_importance(k)
            Xtr_k = self.X_train[topk_feats]
            Xte_k = self.X_test[topk_feats]
            name = f"XGB_top{k}"
            self._fit_xgb(Xtr_k, self.y_train, Xte_k, self.y_test, name=name)
            print(f"Trained reduced model '{name}' with {len(topk_feats)} features.")

    # ------------------------------------------------------------------ #
    def _evaluate_single(self, name: str) -> dict:
        """Compute metrics for a single trained model."""
        est = self.pipelines[name]
        feats = self.model_features.get(name, list(self.X_test.columns))
        X = self.X_test[feats] if set(feats).issubset(self.X_test.columns) else self.X_test

        y_pred = est.predict(X)
        if name.startswith("XGB") and self._log_transform:
            y_pred = np.expm1(y_pred)

        mae = mean_absolute_error(self.y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(self.y_test, y_pred))
        r2 = r2_score(self.y_test, y_pred)
        denom = (np.abs(self.y_test) + np.abs(y_pred)) / 2
        smape = (np.mean(np.where(denom == 0, 0, np.abs(self.y_test - y_pred) / denom)) * 100)

        return {"Model": name, "MAE": mae, "RMSE": rmse, "R2": r2, "SMAPE": smape}

    # ------------------------------------------------------------------ #
    def evaluate_models(self):
        """Print MAE, RMSE, R², SMAPE for all models (on original scale)."""
        rows = []
        for name in self.pipelines.keys():
            rows.append(self._evaluate_single(name))
        self._eval_table = pd.DataFrame(rows).sort_values("MAE")
        for row in rows:
            print(
                f"{row['Model']:15s} → MAE: {row['MAE']:.4f}, RMSE: {row['RMSE']:.4f}, "
                f"R²: {row['R2']:.4f}, SMAPE: {row['SMAPE']:.1f}%"
            )
        return self._eval_table

    # ------------------------------------------------------------------ #
    def compare_xgb_variants(self, metric: str = "MAE") -> pd.DataFrame:
        """
        Return a table comparing full XGB and any XGB_top{k} models by metric.
        metric ∈ {'MAE','RMSE','R2','SMAPE'}
        """
        if self._eval_table is None:
            _ = self.evaluate_models()
        metric = metric.upper()
        if metric not in {"MAE", "RMSE", "R2", "SMAPE"}:
            raise ValueError("metric must be one of {'MAE','RMSE','R2','SMAPE'}")
        tbl = self._eval_table[self._eval_table["Model"].str.startswith("XGB")].copy()
        ascending = metric in {"MAE", "RMSE", "SMAPE"}  # lower is better
        return tbl.sort_values(metric, ascending=ascending)

    # ------------------------------------------------------------------ #
    def select_best_xgb(self, metric: str = "MAE") -> str:
        """
        Choose the best among XGB and XGB_top{k} variants by metric.
        Returns the model name.
        """
        tbl = self.compare_xgb_variants(metric=metric)
        best = tbl.iloc[0]["Model"]
        print(f"Best XGB variant by {metric}: {best}")
        return best

    # ------------------------------------------------------------------ #
    def cross_validate(self, cv_splits: int = 5, model_names: list[str] | None = None):
        """CV on training set. Honors feature subsets for reduced models."""
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
            feats = self.model_features.get(name, list(self.X_train.columns))
            Xcv = self.X_train[feats]

            y_cv = np.log1p(self.y_train) if (name.startswith("XGB") and self._log_transform) else self.y_train

            results = cross_validate(
                est,
                Xcv,
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
    def create_plots(self, model_name: str = "XGB"):
        """Residuals, Pred vs Actual, and top-4 feature importances (XGB only)."""
        if model_name not in self.pipelines:
            raise RuntimeError(f"Train {model_name} first.")

        model = self.pipelines[model_name]
        feats = self.model_features.get(model_name, list(self.X_test.columns))
        X_plot = self.X_test[feats]

        y_pred = model.predict(X_plot)
        if model_name.startswith("XGB") and self._log_transform:
            y_pred = np.expm1(y_pred)

        residuals = self.y_test - y_pred

        # Residuals & Pred vs Actual
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        axes[0].scatter(y_pred, residuals, alpha=0.6)
        axes[0].axhline(0, linestyle="--", color="k")
        axes[0].set_xlabel("Predicted")
        axes[0].set_ylabel("Residuals")
        axes[0].set_title(f"Residuals vs. Predicted ({model_name})")

        axes[1].scatter(y_pred, self.y_test, alpha=0.6)
        mn = float(min(np.min(y_pred), np.min(self.y_test)))
        mx = float(max(np.max(y_pred), np.max(self.y_test)))
        axes[1].plot([mn, mx], [mn, mx], "k--")
        axes[1].set_xlabel("Predicted")
        axes[1].set_ylabel("Actual")
        axes[1].set_title(f"Predicted vs. Actual ({model_name})")
        plt.tight_layout()
        plt.show()

        # Feature importances (top 4) — XGB only
        if model_name.startswith("XGB"):
            importances = getattr(model, "feature_importances_", None)
            if importances is not None:
                features = np.array(feats)
                idx = np.argsort(importances)[-4:][::-1]
                plt.figure(figsize=(8, 5))
                plt.barh(features[idx][::-1], importances[idx][::-1])
                plt.title(f"Top 4 Feature Importances ({model_name})")
                plt.tight_layout()
                plt.show()

    # ------------------------------------------------------------------ #
    def run(
        self,
        tune: bool = True,
        log_transform: bool = False,
        cv_splits: int = 5,
        create_plots: bool = True,
        train_reduced: bool = True,
        reduced_ks: list[int] = [10, 5],
    ):
        """End-to-end run including (optional) reduced-feature XGB variants."""
        self._log_transform = log_transform
        self.preprocess()
        if tune:
            self.tune_hyperparameters()
        self.train_models(log_transform=log_transform)
        if train_reduced:
            # derive top-k from the full XGB and train XGB_top10 / XGB_top5
            self.train_reduced_xgboosts(ks=reduced_ks)
        self.evaluate_models()
        self.cross_validate(cv_splits=cv_splits, model_names=[m for m in self.pipelines if m.startswith("XGB")])
        if create_plots:
            # plot for the best XGB variant by MAE
            best = self.select_best_xgb(metric="MAE")
            self.create_plots(model_name=best)
    
    # ------------------------------------------------------------------ #
    def predict(self, new_data: pd.DataFrame, model_name: str = "XGB") -> np.ndarray:
        """
        Predict target values for new observations using a trained model.
        Handles reduced-feature models by subsetting columns appropriately.
        """
        if model_name not in self.pipelines:
            raise ValueError(
                f"Model '{model_name}' not found. Available: {list(self.pipelines.keys())}"
            )

        model = self.pipelines[model_name]

        # Ensure required columns exist; subset & order for this model
        required_cols = self.model_features.get(model_name, list(self.X_train.columns))
        missing_cols = set(required_cols) - set(new_data.columns)
        if missing_cols:
            raise ValueError(f"Missing columns in new data for {model_name}: {missing_cols}")

        X_new = new_data[required_cols].copy()

        # Make predictions
        if model_name.startswith("XGB"):
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

            if self._log_transform:
                y_pred = np.expm1(y_pred)

        else:
            y_pred = model.predict(X_new)

        return y_pred


class XGBMultiOutputPipeline:
    """
    Lightweight multi-output regressor using only XGBoost (wrapped in MultiOutputRegressor).
    Prints only TEST metrics. Supports optional log1p/expm1 on targets.
    """
    def __init__(
        self,
        df: pd.DataFrame,
        targets: list[str],
        test_size: float = 0.2,
        random_state: int = 42,
    ):
        self.df = df
        self.targets = targets
        self.test_size = test_size
        self.random_state = random_state

        # train/test
        self.X_train = self.X_test = None
        self.y_train = self.y_test = None

        # best XGB params
        self.best_params: dict = {}
        # whether to log-transform all targets
        self._log_transform = False

        # the single pipeline we train/use
        self.pipeline: Pipeline | None = None

    # ---------- Core ----------
    def preprocess(self):
        X = self.df.drop(columns=self.targets)
        y = self.df[self.targets]
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state
        )

    def tune_hyperparameters(self, n_iter: int = 30, cv_splits: int = 5, verbose: int = 0):
        """Randomized search for XGBRegressor hyperparams (wrapped by MultiOutputRegressor)."""
        if self.X_train is None:
            raise RuntimeError("Call preprocess() first.")

        param_dist = {
            "estimator__n_estimators": [200, 500, 800, 1200],
            "estimator__learning_rate": [0.005, 0.01, 0.05, 0.1],
            "estimator__max_depth": [3, 5, 7, 9],
            "estimator__subsample": [0.6, 0.8, 1.0],
            "estimator__colsample_bytree": [0.5, 0.7, 1.0],
            "estimator__min_child_weight": [1, 3, 5, 10],
            "estimator__gamma": [0, 0.1, 0.3, 0.5],
        }

        base = xgb.XGBRegressor(
            random_state=self.random_state,
            tree_method="hist",
            n_jobs=-1,
        )
        mor = MultiOutputRegressor(base)
        pipe = Pipeline([("model", mor)])

        kf = KFold(n_splits=cv_splits, shuffle=True, random_state=self.random_state)
        y_tune = np.log1p(self.y_train) if self._log_transform else self.y_train

        search = RandomizedSearchCV(
            estimator=pipe,
            param_distributions={f"model__{k}": v for k, v in param_dist.items()},
            n_iter=n_iter,
            scoring="neg_mean_absolute_error",
            cv=kf,
            random_state=self.random_state,
            n_jobs=-1,
            verbose=verbose,
        )
        search.fit(self.X_train, y_tune)

        # store params without the "model__estimator__" prefix
        self.best_params = {
            k.replace("model__estimator__", ""): v for k, v in search.best_params_.items()
        }

    def train(self, log_transform: bool = False):
        """Fit the single XGB multi-output pipeline."""
        if self.X_train is None:
            raise RuntimeError("Call preprocess() first.")
        self._log_transform = log_transform

        xgb_base = xgb.XGBRegressor(
            **self.best_params,
            random_state=self.random_state,
            tree_method="hist",
            n_jobs=-1,
        )
        self.pipeline = Pipeline([("model", MultiOutputRegressor(xgb_base))])

        y_fit = np.log1p(self.y_train) if self._log_transform else self.y_train
        self.pipeline.fit(self.X_train, y_fit)

    # ---------- Evaluation / CV (TEST-only prints) ----------
    def _metrics(self, y_true: np.ndarray, y_pred: np.ndarray):
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        denom = (np.abs(y_true) + np.abs(y_pred)) / 2
        smape = np.mean(np.where(denom == 0, 0, np.abs(y_true - y_pred) / denom)) * 100
        return mae, rmse, r2, smape

    def evaluate_test(self):
        """Print TEST MAE, RMSE, R², SMAPE per target (no train metrics)."""
        if self.pipeline is None:
            raise RuntimeError("Call train() first.")

        y_pred = self.pipeline.predict(self.X_test)
        if self._log_transform:
            y_pred = np.expm1(y_pred)

        print("\n=== XGB (TEST results) ===")
        for i, tgt in enumerate(self.targets):
            y_true = self.y_test.values[:, i]
            mae, rmse, r2, smape = self._metrics(y_true, y_pred[:, i])
            print(f"{tgt:30s} → MAE: {mae:.4f} | RMSE: {rmse:.4f} | R²: {r2:.4f} | SMAPE: {smape:.1f}%")

    def cross_validate_per_target(self, cv_splits: int = 5):
        """
        For each target, run CV on X_train → y_train[target] and print TEST scores only.
        """
        if self.X_train is None:
            raise RuntimeError("Call preprocess() first.")

        scoring = {
            "MAE": "neg_mean_absolute_error",
            "RMSE": "neg_root_mean_squared_error",
            "R2": "r2",
        }
        kf = KFold(n_splits=cv_splits, shuffle=True, random_state=self.random_state)

        # Base pipeline (no refit here)
        xgb_base = xgb.XGBRegressor(
            **self.best_params,
            random_state=self.random_state,
            tree_method="hist",
            n_jobs=-1,
        )
        pipe = Pipeline([("model", MultiOutputRegressor(xgb_base))])

        print("\n=== Cross-Validation (TEST only) ===")
        for tgt in self.targets:
            y = self.y_train[[tgt]]  # keep 2D for MultiOutputRegressor
            if self._log_transform:
                y = np.log1p(y)

            results = cross_validate(
                pipe, self.X_train, y,
                cv=kf, scoring=scoring, return_train_score=False, n_jobs=-1
            )

            # Flip signs for neg_ metrics
            mae_mean = -results["test_MAE"].mean(); mae_std = results["test_MAE"].std()
            rmse_mean = -results["test_RMSE"].mean(); rmse_std = results["test_RMSE"].std()
            r2_mean = results["test_R2"].mean(); r2_std = results["test_R2"].std()

            print(
                f"{tgt:30s} → "
                f"MAE: {mae_mean:.4f} ± {mae_std:.4f} | "
                f"RMSE: {rmse_mean:.4f} ± {rmse_std:.4f} | "
                f"R²: {r2_mean:.4f} ± {r2_std:.4f}"
            )

    # ---------- Plots ----------
    def plot_feature_importances(self, top_n: int = 10):
        """Top-N importances per target from the XGB estimators."""
        if self.pipeline is None:
            raise RuntimeError("Call train() first.")
        mor = self.pipeline.named_steps["model"]
        feature_names = self.X_train.columns

        n_targets = len(self.targets)
        fig, axes = plt.subplots(n_targets, 1, figsize=(8, 4 * n_targets))
        if n_targets == 1:
            axes = [axes]

        for i, tgt in enumerate(self.targets):
            imp = mor.estimators_[i].feature_importances_
            idx = np.argsort(imp)[-top_n:][::-1]
            axes[i].barh(feature_names[idx][::-1], imp[idx][::-1])
            axes[i].set_title(f"Top {top_n} Importances for '{tgt}'")
            axes[i].set_xlabel("Importance")

        plt.tight_layout()
        plt.show()

    def plot_residuals(self):
        """Residual (true − pred) vs predicted for each target (TEST set)."""
        if self.pipeline is None:
            raise RuntimeError("Call train() first.")
        mor = self.pipeline.named_steps["model"]
        y_pred = mor.predict(self.X_test)
        if self._log_transform:
            y_pred = np.expm1(y_pred)
        residuals = self.y_test.values - y_pred

        n = len(self.targets)
        fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
        if n == 1:
            axes = [axes]

        for i, tgt in enumerate(self.targets):
            axes[i].scatter(y_pred[:, i], residuals[:, i], alpha=0.6)
            axes[i].axhline(0, color="k", linestyle="--")
            axes[i].set_xlabel("Predicted")
            axes[i].set_ylabel("Residual")
            axes[i].set_title(f"Residuals vs Predicted • {tgt}")

        plt.tight_layout()
        plt.show()

    def plot_actual_vs_predicted(self):
        """Actual vs predicted with 45° line (TEST set)."""
        if self.pipeline is None:
            raise RuntimeError("Call train() first.")
        mor = self.pipeline.named_steps["model"]
        y_pred = mor.predict(self.X_test)
        if self._log_transform:
            y_pred = np.expm1(y_pred)

        n = len(self.targets)
        fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
        if n == 1:
            axes = [axes]

        for i, tgt in enumerate(self.targets):
            y_true = self.y_test.values[:, i]
            mn, mx = min(y_true.min(), y_pred[:, i].min()), max(y_true.max(), y_pred[:, i].max())
            axes[i].scatter(y_true, y_pred[:, i], alpha=0.6)
            axes[i].plot([mn, mx], [mn, mx], "k--", linewidth=1)
            axes[i].set_xlabel("Actual")
            axes[i].set_ylabel("Predicted")
            axes[i].set_title(f"Actual vs Predicted • {tgt}")

        plt.tight_layout()
        plt.show()

    # ---------- Predict ----------
    def predict(self, df_new: pd.DataFrame) -> pd.DataFrame:
        """Predict all targets on df_new (must contain the same feature columns)."""
        if self.pipeline is None:
            raise RuntimeError("Call train() first.")
        X_new = df_new[self.X_train.columns]
        y_pred = self.pipeline.predict(X_new)
        if self._log_transform:
            y_pred = np.expm1(y_pred)
        return pd.DataFrame(y_pred, columns=self.targets, index=X_new.index)

    # ---------- Orchestrator ----------
    def run(
        self,
        tune: bool = True,
        log_transform: bool = False,
        cv_splits: int = 5,
        plot_figures: bool = True,
        verbose_search: int = 0,
    ):
        self._log_transform = log_transform
        self.preprocess()
        if tune:
            self.tune_hyperparameters(cv_splits=cv_splits, verbose=verbose_search)
        self.train(log_transform=log_transform)
        self.evaluate_test()
        if cv_splits and cv_splits > 1:
            self.cross_validate_per_target(cv_splits=cv_splits)
        if plot_figures:
            self.plot_feature_importances()
            self.plot_residuals()
            self.plot_actual_vs_predicted()
