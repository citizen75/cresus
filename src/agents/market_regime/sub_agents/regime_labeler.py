"""Regime labeling using unsupervised clustering."""

from typing import Any, Dict, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from core.agent import Agent


class RegimeLabelerAgent(Agent):
	"""Create unsupervised training labels via KMeans, map to named regimes.

	Reads from context:
		features_df: feature matrix
		regime_config: n_regimes

	Writes to context:
		labels_series: pd.Series of regime IDs
		cluster_stats: Dict describing each cluster
		cluster_to_regime_map: Dict mapping cluster IDs to regime names
	"""

	REGIME_NAMES = {
		0: "Strong_Bull",
		1: "Weak_Bull",
		2: "Neutral_Sideways",
		3: "Weak_Bear",
		4: "Strong_Bear",
		5: "Crisis_Volatile",
	}

	def __init__(self, name: str = "RegimeLabelerAgent"):
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Run KMeans, map clusters to regimes."""
		if input_data is None:
			input_data = {}

		features_df = self.context.get("features_df")
		regime_config = self.context.get("regime_config") or {}
		n_regimes = regime_config.get("n_regimes", 6)

		if features_df is None or features_df.empty:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No features_df in context"
			}

		try:
			# Drop NaN rows
			features_clean = features_df.dropna()
			if len(features_clean) < n_regimes:
				return {
					"status": "error",
					"input": input_data,
					"output": {},
					"message": f"Not enough clean data rows ({len(features_clean)}) for {n_regimes} regimes"
				}

			# Standardize features
			scaler = StandardScaler()
			X_scaled = scaler.fit_transform(features_clean)

			# Run KMeans
			kmeans = KMeans(n_clusters=n_regimes, random_state=42, n_init=10)
			raw_labels = kmeans.fit_predict(X_scaled)

			# Compute cluster statistics
			cluster_stats = {}
			for c in range(n_regimes):
				mask = raw_labels == c
				if mask.any():
					cluster_stats[c] = {
						"n_samples": mask.sum(),
						"feature_means": features_clean[mask].mean().to_dict(),
						"centroid": kmeans.cluster_centers_[c].tolist(),
					}

			# Map clusters to semantic regimes
			regime_labels = self._map_clusters_to_regimes(
				raw_labels, features_clean, cluster_stats, n_regimes
			)

			# Create time-aligned series (keeping original index)
			labels_series = pd.Series(index=features_df.index, data=np.nan, dtype=float)
			labels_series.loc[features_clean.index] = regime_labels

			# Store in context
			self.context.set("labels_series", labels_series)
			self.context.set("cluster_stats", cluster_stats)

			self.logger.info(f"Created {n_regimes} regime labels from {len(features_clean)} samples")

			# Compute distribution
			regime_dist = {}
			for regime_id, regime_name in self.REGIME_NAMES.items():
				count = (regime_labels == regime_id).sum() if regime_id < n_regimes else 0
				regime_dist[f"{regime_id}_{regime_name}"] = int(count)

			return {
				"status": "success",
				"input": input_data,
				"output": {
					"n_samples_labeled": len(regime_labels),
					"n_regimes": n_regimes,
					"regime_distribution": regime_dist,
				},
				"message": f"Created regime labels for {len(regime_labels)} samples"
			}

		except Exception as e:
			self.logger.exception(f"Error in regime labeling: {e}")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Regime labeling failed: {str(e)}"
			}

	def _map_clusters_to_regimes(
		self,
		raw_labels: np.ndarray,
		features_df: pd.DataFrame,
		cluster_stats: Dict,
		n_regimes: int
	) -> np.ndarray:
		"""Map KMeans cluster IDs to semantic regime IDs."""
		cluster_scores = {}

		for c in range(n_regimes):
			means = cluster_stats[c]["feature_means"]

			# Extract key features with fallbacks
			breadth_sma50 = means.get("breadth_above_sma50", 0.5)
			momentum_ret = means.get("momentum_factor_return", 0)
			avg_atr_norm = means.get("avg_atr_norm", 0.01)
			dispersion = means.get("dispersion", 0.01)
			cross_corr = means.get("cross_correlation", 0.3)

			# Compute composite scores
			bull_score = breadth_sma50 + momentum_ret - avg_atr_norm
			bear_score = -breadth_sma50 - momentum_ret + avg_atr_norm
			vol_score = avg_atr_norm + dispersion + cross_corr
			chop_score = 1 - abs(breadth_sma50 - 0.5) * 2

			cluster_scores[c] = {
				"bull": bull_score,
				"bear": bear_score,
				"vol": vol_score,
				"chop": chop_score,
			}

		# Rank clusters and assign regimes
		cluster_to_regime = {}

		# Regime 5 (Crisis): highest vol score
		vol_scores = [(c, cluster_scores[c]["vol"]) for c in range(n_regimes)]
		vol_scores.sort(key=lambda x: x[1], reverse=True)
		crisis_cluster = vol_scores[0][0]
		cluster_to_regime[crisis_cluster] = 5

		# Regime 0 (Strong Bull): highest bull score (excluding crisis)
		bull_scores = [
			(c, cluster_scores[c]["bull"])
			for c in range(n_regimes)
			if c != crisis_cluster
		]
		bull_scores.sort(key=lambda x: x[1], reverse=True)
		strong_bull = bull_scores[0][0]
		cluster_to_regime[strong_bull] = 0

		# Regime 1 (Weak Bull): second highest bull score
		if len(bull_scores) > 1:
			weak_bull = bull_scores[1][0]
			cluster_to_regime[weak_bull] = 1
		else:
			weak_bull = -1

		# Regime 4 (Strong Bear): highest bear score
		bear_scores = [
			(c, cluster_scores[c]["bear"])
			for c in range(n_regimes)
			if c not in [crisis_cluster, strong_bull, weak_bull]
		]
		if bear_scores:
			bear_scores.sort(key=lambda x: x[1], reverse=True)
			strong_bear = bear_scores[0][0]
			cluster_to_regime[strong_bear] = 4

			# Regime 3 (Weak Bear): second highest bear score
			if len(bear_scores) > 1:
				weak_bear = bear_scores[1][0]
				cluster_to_regime[weak_bear] = 3

		# Regime 2 (Neutral): remaining clusters
		for c in range(n_regimes):
			if c not in cluster_to_regime:
				cluster_to_regime[c] = 2

		self.context.set("cluster_to_regime_map", cluster_to_regime)

		# Apply mapping to create regime labels
		regime_labels = np.array([cluster_to_regime[raw_labels[i]] for i in range(len(raw_labels))])

		return regime_labels
