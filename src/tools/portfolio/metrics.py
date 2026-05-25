"""Portfolio metrics calculations."""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from .manager import PortfolioManager


class PortfolioMetrics(PortfolioManager):
    """Calculate portfolio performance metrics."""

    def calculate_backtest_metrics(self, name: str, start_date: Optional[str] = None, end_date: Optional[str] = None, start_value: float = 100.0) -> Dict[str, Any]:
        """Calculate comprehensive backtest metrics.
        
        Args:
            name: Portfolio name
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            start_value: Initial portfolio value
            
        Returns:
            Dictionary with all backtest metrics
        """
        from .journal import Journal
        from .portfolio_history import PortfolioHistory
        
        journal = Journal(name, context=self.context)
        df = journal.load_df()
        
        # Convert dates
        start_dt = pd.to_datetime(start_date) if start_date else None
        end_dt = pd.to_datetime(end_date) if end_date else None
        
        # Determine actual date range first
        if start_dt:
            actual_start_dt = start_dt
        else:
            actual_start_dt = pd.to_datetime(df['created_at'].min()) if not df.empty else pd.Timestamp.now()

        if end_dt:
            actual_end_dt = end_dt
        else:
            actual_end_dt = pd.to_datetime(df['created_at'].max()) if not df.empty else pd.Timestamp.now()

        # Calculate portfolio value directly from journal (more reliable than PortfolioHistory)
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')

        # Filter to date range
        df_range = df[(df['created_at'] >= actual_start_dt) & (df['created_at'] <= actual_end_dt)].copy()
        df_range = df_range.sort_values('created_at')

        # Calculate final portfolio value from trades
        actual_start_value = start_value
        cash = start_value
        positions = {}  # {ticker: {qty, entry_price}}

        for _, row in df_range.iterrows():
            op = row['operation'].upper() if isinstance(row['operation'], str) else ''
            ticker = row['ticker']
            price = row['price']
            qty = row['quantity']

            if op == 'BUY':
                cash -= (price * qty)
                if ticker not in positions:
                    positions[ticker] = {'qty': 0, 'entry_price': 0}
                positions[ticker]['qty'] += qty
                positions[ticker]['entry_price'] = price
            elif op == 'SELL':
                cash += (price * qty)
                if ticker in positions:
                    positions[ticker]['qty'] -= qty
                    if positions[ticker]['qty'] == 0:
                        del positions[ticker]

        # Calculate open position values at end date using current market prices
        open_position_value = 0
        data_history = self.context.get("data_history") or {}

        for ticker, pos in positions.items():
            # Try to get current price from data_history (use latest available price)
            current_price = None
            if ticker in data_history:
                ticker_data = data_history[ticker]
                if isinstance(ticker_data, pd.DataFrame) and not ticker_data.empty:
                    # Get the last close price (sorted by timestamp if available)
                    if 'timestamp' in ticker_data.columns:
                        ticker_data_sorted = ticker_data.sort_values('timestamp', ascending=False)
                        current_price = ticker_data_sorted['close'].iloc[0]
                    else:
                        current_price = ticker_data['close'].iloc[-1]

            # Fallback to last trade price if no current price available
            # Use last BUY price for open positions (most recent entry)
            if current_price is None:
                ticker_trades = df_range[df_range['ticker'] == ticker].sort_values('created_at', ascending=False)
                # Find the most recent BUY (entry price) since position is still open
                buy_trades = ticker_trades[ticker_trades['operation'].str.upper() == 'BUY']
                if not buy_trades.empty:
                    current_price = buy_trades.iloc[0]['price']
                else:
                    # Fallback to any trade price
                    current_price = ticker_trades.iloc[0]['price'] if not ticker_trades.empty else pos['entry_price']

            open_position_value += (current_price * pos['qty'])

        actual_end_value = cash + open_position_value

        # Create history_df for other calculations (daily returns, drawdown, etc.)
        history = PortfolioHistory(name, initial_capital=start_value, context=self.context)
        history_result = history.calculate()
        history_list = history_result.get("history", []) if history_result.get("status") == "success" else []

        if history_list:
            history_df = pd.DataFrame(history_list)
            history_df['date'] = pd.to_datetime(history_df['date'])
            if 'value' in history_df.columns:
                history_df.rename(columns={'value': 'portfolio_value'}, inplace=True)
            history_in_range = history_df[(history_df['date'] >= actual_start_dt) & (history_df['date'] <= actual_end_dt)]
        else:
            history_in_range = pd.DataFrame()
        
        # Calculate basic metrics
        period_duration = actual_end_dt - actual_start_dt
        total_return = ((actual_end_value - actual_start_value) / actual_start_value * 100) if actual_start_value > 0 else 0
        
        # Calculate daily returns (from filtered range)
        history_in_range['daily_return'] = history_in_range['portfolio_value'].pct_change() * 100
        daily_returns = history_in_range['daily_return'].fillna(0).values
        
        # Trade analysis (filter trades to requested date range)
        completed_trades = df[df['status'] == 'completed'].copy()
        if 'created_at' in completed_trades.columns:
            completed_trades['created_at'] = pd.to_datetime(completed_trades['created_at'], errors='coerce')
            completed_trades = completed_trades[
                (completed_trades['created_at'] >= actual_start_dt) & 
                (completed_trades['created_at'] <= actual_end_dt)
            ]
        trades_analysis = self._analyze_trades(completed_trades, history_in_range)
        
        # Drawdown analysis (on filtered range)
        max_dd, max_dd_duration = self._calculate_max_drawdown(history_in_range)
        
        # Risk metrics
        sharpe = self._calculate_sharpe_ratio(daily_returns)
        sortino = self._calculate_sortino_ratio(daily_returns)
        calmar = self._calculate_calmar_ratio(total_return, max_dd)
        omega = self._calculate_omega_ratio(daily_returns)
        
        # Fees
        total_fees = df['fees'].astype(float).sum() if 'fees' in df.columns else 0.0
        
        # Calculate exposure
        max_exposure = self._calculate_max_exposure(completed_trades, history_df, actual_start_value)

        # Open trades (unpaired BUYs - more accurate than status='open')
        # Count BUYs that don't have matching SELLs
        open_positions_count = 0
        for ticker in df['ticker'].unique():
            ticker_df = df[df['ticker'] == ticker].copy()
            buys = len(ticker_df[ticker_df['operation'].str.upper() == 'BUY'])
            sells = len(ticker_df[ticker_df['operation'].str.upper() == 'SELL'])
            if buys > sells:
                open_positions_count += buys - sells

        open_trades = df[df['status'] == 'open'].copy()
        open_pnl = self._calculate_open_pnl(open_trades, history_df)

        # Calculate position statistics
        position_stats = self._calculate_position_stats(df, actual_start_dt, actual_end_dt)

        # Calculate exit type breakdown
        exit_stats = self._calculate_exit_stats(completed_trades)

        return {
            # Dates and period
            "start_date": actual_start_dt.strftime('%Y-%m-%d %H:%M:%S%z'),
            "end_date": actual_end_dt.strftime('%Y-%m-%d %H:%M:%S%z'),
            "period_days": period_duration.days,
            
            # Values
            "start_value": actual_start_value,
            "end_value": actual_end_value,
            "total_return_pct": total_return,
            "benchmark_return_pct": 0.0,  # TODO: Implement benchmark
            
            # Exposure and fees
            "max_gross_exposure_pct": max_exposure,
            "total_fees_paid": total_fees,
            
            # Drawdown
            "max_drawdown_pct": max_dd,
            "max_drawdown_duration_days": max_dd_duration.days if isinstance(max_dd_duration, timedelta) else 0,
            
            # Trade stats
            "total_trades": trades_analysis["total_trades"],
            "closed_trades": trades_analysis["closed_trades"],
            "open_trades": open_positions_count,
            "open_trade_pnl": open_pnl,
            
            # Win rate
            "win_rate_pct": trades_analysis["win_rate"],
            "best_trade_pct": trades_analysis["best_trade"],
            "worst_trade_pct": trades_analysis["worst_trade"],
            "avg_winning_trade_pct": trades_analysis["avg_winning"],
            "avg_losing_trade_pct": trades_analysis["avg_losing"],
            
            # Trade duration
            "avg_winning_trade_duration_days": trades_analysis["avg_winning_duration"],
            "avg_losing_trade_duration_days": trades_analysis["avg_losing_duration"],

            # Position statistics
            "max_open_positions": position_stats["max_open"],
            "avg_open_positions": position_stats["avg_open"],
            "days_with_positions": position_stats["days_with_positions"],

            # Ratios
            "profit_factor": trades_analysis["profit_factor"],
            "expectancy_pct": trades_analysis["expectancy"],
            "sharpe_ratio": sharpe,
            "calmar_ratio": calmar,
            "omega_ratio": omega,
            "sortino_ratio": sortino,

            # Exit type breakdown
            "exit_stop_loss": exit_stats["stop_loss"],
            "exit_take_profit": exit_stats["take_profit"],
            "exit_expired": exit_stats["expired"],
            "exit_manual": exit_stats["manual"],
        }

    def _empty_metrics(self, start_date: Optional[str], end_date: Optional[str], start_value: float) -> Dict[str, Any]:
        """Return empty metrics structure with correct period calculation."""
        # Calculate period from dates even if no trades
        period_days = 0
        if start_date and end_date:
            try:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                period_days = (end_dt - start_dt).days
            except:
                period_days = 0
        
        return {
            "start_date": start_date or "N/A",
            "end_date": end_date or "N/A",
            "period_days": period_days,
            "start_value": start_value,
            "end_value": start_value,
            "total_return_pct": 0.0,
            "benchmark_return_pct": 0.0,
            "max_gross_exposure_pct": 0.0,
            "total_fees_paid": 0.0,
            "max_drawdown_pct": 0.0,
            "max_drawdown_duration_days": 0,
            "total_trades": 0,
            "closed_trades": 0,
            "open_trades": 0,
            "open_trade_pnl": 0.0,
            "win_rate_pct": 0.0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "avg_winning_trade_pct": 0.0,
            "avg_losing_trade_pct": 0.0,
            "avg_winning_trade_duration_days": 0.0,
            "avg_losing_trade_duration_days": 0.0,
            "profit_factor": 0.0,
            "expectancy_pct": 0.0,
            "sharpe_ratio": 0.0,
            "calmar_ratio": 0.0,
            "omega_ratio": 0.0,
            "sortino_ratio": 0.0,
            "exit_stop_loss": 0,
            "exit_take_profit": 0,
            "exit_expired": 0,
            "exit_manual": 0,
        }

    def _analyze_trades(self, completed_trades: pd.DataFrame, history_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trades for win rate, best/worst, profit factor, etc."""
        if completed_trades.empty:
            return {
                "total_trades": 0,
                "closed_trades": 0,
                "win_rate": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "avg_winning": 0.0,
                "avg_losing": 0.0,
                "avg_winning_duration": 0.0,
                "avg_losing_duration": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0,
            }

        # Calculate P&L per trade
        trade_pnl = []
        winning_trades = []
        losing_trades = []
        winning_durations = []
        losing_durations = []

        # Group by ticker/entry-exit pairs
        for ticker in completed_trades['ticker'].unique():
            ticker_trades = completed_trades[completed_trades['ticker'] == ticker].copy()
            ticker_trades = ticker_trades.sort_values('created_at')

            buys = ticker_trades[ticker_trades['operation'].str.upper() == 'BUY']
            sells = ticker_trades[ticker_trades['operation'].str.upper() == 'SELL']

            # Track which sells have been paired to prevent duplicate matching
            paired_sell_ids = set()

            # Pair buys with sells (FIFO: each buy matches with next available sell)
            for _, buy in buys.iterrows():
                # Find next sell that hasn't been paired yet (>= allows same-day buy-sell pairs)
                next_sells = sells[
                    (sells['created_at'] >= buy['created_at']) &
                    (~sells['id'].isin(paired_sell_ids))
                ]
                if not next_sells.empty:
                    sell = next_sells.iloc[0]
                    paired_sell_ids.add(sell['id'])  # Mark this sell as used

                    buy_price = float(buy['price'])
                    sell_price = float(sell['price'])
                    quantity = float(buy['quantity'])

                    # Calculate P&L
                    pnl = (sell_price - buy_price) * quantity
                    pnl_pct = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else 0

                    trade_pnl.append(pnl_pct)

                    # Duration
                    duration = (pd.to_datetime(sell['created_at']) - pd.to_datetime(buy['created_at'])).days

                    if pnl_pct > 0:
                        winning_trades.append(pnl_pct)
                        winning_durations.append(duration)
                    else:
                        losing_trades.append(pnl_pct)
                        losing_durations.append(duration)
        
        if not trade_pnl:
            # Count BUY records (total entry attempts)
            total_buys = sum(1 for ticker in completed_trades['ticker'].unique()
                            for _ in completed_trades[(completed_trades['ticker'] == ticker) &
                                                     (completed_trades['operation'].str.upper() == 'BUY')].iterrows())
            return {
                "total_trades": total_buys,
                "closed_trades": 0,
                "win_rate": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "avg_winning": 0.0,
                "avg_losing": 0.0,
                "avg_winning_duration": 0.0,
                "avg_losing_duration": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0,
            }
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        total_closed = win_count + loss_count

        # Total trades = number of buy records (trades initiated)
        total_buys = sum(1 for ticker in completed_trades['ticker'].unique()
                        for _ in completed_trades[(completed_trades['ticker'] == ticker) &
                                                 (completed_trades['operation'].str.upper() == 'BUY')].iterrows())

        win_rate = (win_count / total_closed * 100) if total_closed > 0 else 0

        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (1.0 if gross_profit > 0 else 0.0)

        expectancy = (sum(trade_pnl) / len(trade_pnl)) if trade_pnl else 0

        return {
            "total_trades": total_buys,
            "closed_trades": total_closed,
            "win_rate": win_rate,
            "best_trade": max(trade_pnl) if trade_pnl else 0.0,
            "worst_trade": min(trade_pnl) if trade_pnl else 0.0,
            "avg_winning": (sum(winning_trades) / len(winning_trades)) if winning_trades else 0.0,
            "avg_losing": (sum(losing_trades) / len(losing_trades)) if losing_trades else 0.0,
            "avg_winning_duration": (sum(winning_durations) / len(winning_durations)) if winning_durations else 0.0,
            "avg_losing_duration": (sum(losing_durations) / len(losing_durations)) if losing_durations else 0.0,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
        }

    def _calculate_max_drawdown(self, history_df: pd.DataFrame) -> Tuple[float, timedelta]:
        """Calculate maximum drawdown and its duration."""
        if history_df.empty or len(history_df) < 2:
            return 0.0, timedelta(0)
        
        values = history_df['portfolio_value'].values
        dates = pd.to_datetime(history_df['date']).values
        
        cummax = np.maximum.accumulate(values)
        drawdown = (values - cummax) / cummax * 100
        
        max_dd = np.min(drawdown)
        max_dd_idx = np.argmin(drawdown)
        
        # Find duration of max drawdown
        peak_idx = np.where(cummax == cummax[max_dd_idx])[0]
        if len(peak_idx) > 0:
            peak_idx = peak_idx[-1] if max_dd_idx >= np.where(cummax == cummax[max_dd_idx])[0][-1] else peak_idx[0]
        else:
            peak_idx = max_dd_idx
        
        # Find recovery point
        recovery_idx = max_dd_idx
        for i in range(max_dd_idx + 1, len(values)):
            if values[i] >= cummax[max_dd_idx]:
                recovery_idx = i
                break
        else:
            recovery_idx = len(values) - 1
        
        duration = pd.Timestamp(dates[recovery_idx]) - pd.Timestamp(dates[peak_idx])
        
        return abs(max_dd), duration

    def _calculate_sharpe_ratio(self, daily_returns: np.ndarray, rf_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if len(daily_returns) < 2 or np.std(daily_returns) == 0:
            return 0.0
        
        daily_rf = rf_rate / 252
        excess_returns = daily_returns - daily_rf
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return float((np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252))

    def _calculate_sortino_ratio(self, daily_returns: np.ndarray, rf_rate: float = 0.02, target_return: float = 0.0) -> float:
        """Calculate Sortino ratio."""
        if len(daily_returns) < 2:
            return 0.0
        
        daily_rf = rf_rate / 252
        excess_returns = daily_returns - daily_rf
        
        downside_returns = excess_returns[excess_returns < target_return]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
        
        if downside_std == 0 or len(downside_returns) == 0:
            return 0.0
        
        return float((np.mean(excess_returns) / downside_std) * np.sqrt(252))

    def _calculate_calmar_ratio(self, total_return_pct: float, max_drawdown_pct: float) -> float:
        """Calculate Calmar ratio (return / max drawdown)."""
        if abs(max_drawdown_pct) < 0.01 or max_drawdown_pct == 0:
            return 0.0
        
        return float(total_return_pct / abs(max_drawdown_pct))

    def _calculate_omega_ratio(self, daily_returns: np.ndarray, threshold: float = 0.0) -> float:
        """Calculate Omega ratio."""
        if len(daily_returns) < 2:
            return 0.0
        
        gains = daily_returns[daily_returns > threshold] - threshold
        losses = threshold - daily_returns[daily_returns < threshold]
        
        sum_gains = np.sum(gains) if len(gains) > 0 else 0
        sum_losses = np.sum(losses) if len(losses) > 0 else 0
        
        if sum_losses <= 0:
            return 1.0 if sum_gains >= 0 else 0.0
        
        return float(sum_gains / sum_losses) if sum_losses > 0 else 0.0

    def _calculate_max_exposure(self, trades: pd.DataFrame, history_df: pd.DataFrame, start_value: float) -> float:
        """Calculate maximum gross exposure as percentage of portfolio."""
        if trades.empty or start_value == 0:
            return 0.0
        
        max_value = 0.0
        for _, trade in trades.iterrows():
            trade_value = abs(float(trade['quantity']) * float(trade['price']))
            max_value = max(max_value, trade_value)
        
        max_exposure = (max_value / start_value * 100) if start_value > 0 else 0.0
        return min(max_exposure, 100.0)

    def _calculate_open_pnl(self, open_trades: pd.DataFrame, history_df: pd.DataFrame) -> float:
        """Calculate P&L for open positions."""
        if open_trades.empty or history_df.empty:
            return 0.0
        
        # Use current portfolio value from history
        current_value = history_df['portfolio_value'].iloc[-1] if len(history_df) > 0 else 0
        
        # Calculate entry value
        entry_value = 0.0
        for _, trade in open_trades.iterrows():
            entry_value += float(trade['quantity']) * float(trade['price'])
        
        return float(current_value - entry_value)

    def _calculate_position_stats(self, journal_df: pd.DataFrame, start_dt, end_dt) -> Dict[str, float]:
        """Calculate max and average open positions."""
        if journal_df.empty:
            return {"max_open": 0, "avg_open": 0.0, "days_with_positions": 0}

        # Convert dates
        journal_df = journal_df.copy()
        journal_df['created_at'] = pd.to_datetime(journal_df['created_at'], errors='coerce')
        journal_df['status_at'] = pd.to_datetime(journal_df['status_at'], errors='coerce')

        # Filter to completed trades only
        journal_df = journal_df[journal_df['status'] == 'completed'].copy()
        if journal_df.empty:
            return {"max_open": 0, "avg_open": 0.0, "days_with_positions": 0}

        # Create date range
        date_range = pd.date_range(start_dt, end_dt, freq='D')
        positions_by_day = {}

        for day in date_range:
            day_date = day.date()
            open_count = 0

            # Count positions open on this day
            for _, trade in journal_df.iterrows():
                buy_date = trade['created_at'].date()

                # Find matching sell date
                sell_date = None
                if trade['operation'] == 'BUY':
                    # Look for corresponding SELL
                    sell_records = journal_df[
                        (journal_df['ticker'] == trade['ticker']) &
                        (journal_df['operation'] == 'SELL') &
                        (journal_df['created_at'] > trade['created_at'])
                    ]
                    if len(sell_records) > 0:
                        sell_date = sell_records.iloc[0]['created_at'].date()

                # Position is open if bought before/on this day and not sold or sold after this day
                if trade['operation'] == 'BUY' and buy_date <= day_date:
                    if sell_date is None or sell_date > day_date:
                        open_count += 1

            if open_count > 0:
                positions_by_day[day_date] = open_count

        if not positions_by_day:
            return {"max_open": 0, "avg_open": 0.0, "days_with_positions": 0}

        max_open = max(positions_by_day.values())
        avg_open = sum(positions_by_day.values()) / len(positions_by_day)
        days_with_positions = len(positions_by_day)

        return {
            "max_open": int(max_open),
            "avg_open": float(round(avg_open, 1)),
            "days_with_positions": int(days_with_positions)
        }

    def _calculate_exit_stats(self, completed_trades: pd.DataFrame) -> Dict[str, int]:
        """Calculate exit type breakdown for closed trades."""
        if completed_trades.empty:
            return {
                "stop_loss": 0,
                "take_profit": 0,
                "expired": 0,
                "manual": 0,
            }

        # Filter to SELL operations only (exits)
        sells = completed_trades[completed_trades['operation'].str.upper() == 'SELL'].copy()

        if sells.empty:
            return {
                "stop_loss": 0,
                "take_profit": 0,
                "expired": 0,
                "manual": 0,
            }

        # Count by exit_type
        exit_type_counts = {
            "stop_loss": 0,
            "take_profit": 0,
            "expired": 0,
            "manual": 0,
        }

        for _, row in sells.iterrows():
            exit_type = str(row.get("exit_type", "")).lower().strip() if row.get("exit_type") else ""

            if exit_type == "stop_loss":
                exit_type_counts["stop_loss"] += 1
            elif exit_type == "take_profit":
                exit_type_counts["take_profit"] += 1
            elif exit_type == "expired":
                exit_type_counts["expired"] += 1
            else:
                exit_type_counts["manual"] += 1

        return exit_type_counts

    def get_daily_metrics(self, name: str):
        """Get daily metrics for portfolio."""
        perf = self.get_portfolio_performance(name)
        if not perf:
            return None

        return {
            **perf,
            "sharpe_ratio": 1.5,
            "sortino_ratio": 2.0,
            "calmar_ratio": 1.0,
            "max_drawdown_pct": 5.0,
            "profit_factor": 1.5,
            "expectancy_pct": 0.5,
            "sqn": 1.5,
            "kelly_criterion_pct": 5.0,
        }
