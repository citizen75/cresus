"""Analyze feature importance and correlations to understand high IC."""

import pandas as pd
import numpy as np
from scipy.stats import spearmanr, pearsonr
from typing import Dict, Any, Optional
from core.agent import Agent


class FeatureAnalysis(Agent):
	"""Analyze which features drive the high IC."""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Analyze feature importance and correlations with label.

		Args:
			input_data: Dict with trained model and data

		Returns:
			Feature analysis results
		"""
		if input_data is None:
			input_data = {}

		import pickle
		from pathlib import Path

		data_history = self.context.get("data_history") or {}
		strategy_name = self.context.get("strategy_name") or "unknown"

		if not data_history:
			return {
				"status": "error",
				"message": "No data_history in context"
			}

		self.logger.info("[FEATURE_ANALYSIS] Analyzing feature importance")

		# Build dataset
		rows = []
		exclude_cols = {"timestamp", "ticker", "Dividends", "Stock Splits"}

		for ticker, df in data_history.items():
			if df is None or len(df) < 6:
				continue

			df_asc = df.sort_values("timestamp").reset_index(drop=True)
			feature_cols = [c for c in df_asc.columns if c not in exclude_cols]

			for i in range(len(df_asc) - 5):
				cur_close = df_asc.iloc[i].get("close")
				fut_close = df_asc.iloc[i + 5].get("close")

				if pd.isna(cur_close) or pd.isna(fut_close) or cur_close == 0:
					continue

				label = (fut_close - cur_close) / cur_close
				row = {col: df_asc.iloc[i][col] for col in feature_cols}
				row["label"] = label
				rows.append(row)

		if not rows:
			return {"status": "error", "message": "No data"}

		df = pd.DataFrame(rows).fillna(0)
		feature_cols = [c for c in df.columns if c != "label"]

		# Load trained model
		model_path = Path.home() / '.cresus' / 'db' / 'models' / 'watchlist_ranking' / f'{strategy_name}_lgb.pkl'

		results = {
			"status": "success",
			"output": {}
		}

		# 1. Feature importance from LightGBM
		if model_path.exists():
			try:
				with open(model_path, 'rb') as f:
					model = pickle.load(f)

				importances = model.feature_importance(importance_type='gain')
				feature_importance = list(zip(feature_cols, importances))
				feature_importance.sort(key=lambda x: x[1], reverse=True)

				self.logger.info("[FEATURE_ANALYSIS] Top 10 features by importance:")
				top_features = feature_importance[:10]
				for feat, imp in top_features:
					self.logger.info(f"  {feat}: {imp:.4f}")

				results["output"]["lgbm_importance"] = top_features
			except Exception as e:
				self.logger.warning(f"Could not load model: {e}")

		# 2. Correlation with label (Spearman and Pearson)
		self.logger.info("[FEATURE_ANALYSIS] Computing feature-label correlations")
		correlations = []

		for feat in feature_cols:
			try:
				spear_corr, spear_p = spearmanr(df[feat], df["label"])
				pear_corr, pear_p = pearsonr(df[feat], df["label"])

				correlations.append({
					"feature": feat,
					"spearman": float(spear_corr) if not np.isnan(spear_corr) else 0.0,
					"pearson": float(pear_corr) if not np.isnan(pear_corr) else 0.0,
				})
			except Exception as e:
				pass

		# Sort by absolute Spearman correlation
		correlations.sort(key=lambda x: abs(x["spearman"]), reverse=True)

		self.logger.info("[FEATURE_ANALYSIS] Top 15 features by Spearman correlation with label:")
		for i, corr in enumerate(correlations[:15]):
			self.logger.info(f"  {i+1}. {corr['feature']}: spearman={corr['spearman']:.4f}, pearson={corr['pearson']:.4f}")

		results["output"]["correlations"] = correlations[:20]

		# 3. Identify potentially problematic features
		self.logger.info("[FEATURE_ANALYSIS] Analyzing for circular dependencies")
		problematic = []

		for corr in correlations[:10]:
			feat = corr["feature"]
			spear = abs(corr["spearman"])

			# Features highly correlated with returns might be problematic
			if spear > 0.5:
				problematic.append(f"  - {feat}: |spearman|={spear:.4f} (VERY HIGH)")
			elif spear > 0.3:
				problematic.append(f"  - {feat}: |spearman|={spear:.4f} (HIGH)")

		if problematic:
			self.logger.warning("[FEATURE_ANALYSIS] Features with suspiciously high correlation:")
			for p in problematic:
				self.logger.warning(p)
			results["output"]["warnings"] = problematic
		else:
			self.logger.info("[FEATURE_ANALYSIS] No extremely high feature-label correlations found")

		# 4. Check if momentum/volatility features explain the IC
		momentum_features = [c for c in feature_cols if 'roc' in c.lower() or 'momentum' in c.lower() or 'mom' in c.lower()]
		trend_features = [c for c in feature_cols if 'trend' in c.lower() or 'adx' in c.lower() or 'ema' in c.lower()]

		if momentum_features:
			mom_corrs = [c for c in correlations if c["feature"] in momentum_features]
			avg_mom_corr = np.mean([abs(c["spearman"]) for c in mom_corrs])
			self.logger.info(f"[FEATURE_ANALYSIS] Momentum features avg |spearman|: {avg_mom_corr:.4f}")
			results["output"]["momentum_avg_correlation"] = float(avg_mom_corr)

		return results
