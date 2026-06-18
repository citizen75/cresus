"""Technical indicators management commands."""

import pandas as pd
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


class IndicatorsCommands:
    """Technical indicators management command handlers."""

    def __init__(self):
        """Initialize indicators command handler."""
        pass

    def handle(self, args: str):
        """Handle indicators commands."""
        args_str = str(args).strip() if args else ""

        if not args_str:
            self._show_help()
            return

        parts = args_str.split()
        cmd = parts[0] if parts else None

        if cmd == "list":
            self._handle_list()
        elif cmd == "show":
            self._handle_show(parts[1:] if len(parts) > 1 else [])
        elif cmd == "calc":
            self._handle_calc(parts[1:] if len(parts) > 1 else [])
        else:
            console.print(f"[red]✗[/red] Unknown command: {cmd}")
            console.print("Try: indicators list|show|calc")

    def _show_help(self):
        """Show help for indicators commands."""
        table = Table(title="Indicators Management Commands", box=box.ROUNDED)
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        table.add_row("indicators list", "List all available indicators")
        table.add_row("indicators show <name>", "Show indicator definition (e.g., ema_20, rsi_14, ema_20_chgpct_5)")
        table.add_row("indicators calc <indicator> <ticker> [start_date]", "Calculate indicator for ticker")
        table.add_row("indicators calc <indicator> <file.csv>", "Calculate indicator from CSV file")
        console.print(table)

    def _handle_list(self):
        """List all available indicators."""
        try:
            from tools.indicators.indicators import get_registered_indicator
            from tools.indicators import parser

            # Get all registered indicator names
            registered = set()

            # Check common indicator patterns
            indicator_patterns = [
                "rsi", "ema", "sma", "macd", "roc", "adx", "atr",
                "bb", "bb_lower", "bb_middle", "bb_upper",
                "ha", "sha", "hama",
                "ad", "obv", "mfi", "cmf", "vratio", "vwap", "volume_sma",
                "chgpct", "chglog", "ema_chgpct",
                "pivot"
            ]

            # Organize by category
            categories = {
                "Momentum": ["rsi", "macd", "roc"],
                "Trend": ["ema", "sma", "adx", "hama", "sha", "ha", "ema_chgpct"],
                "Volatility": ["atr", "bb", "bb_lower", "bb_middle", "bb_upper"],
                "Volume": ["ad", "obv", "mfi", "cmf", "vratio", "vwap", "volume_sma"],
                "Change": ["chgpct", "chglog"],
                "Support/Resistance": ["pivot"],
            }

            for category, indicators in categories.items():
                table = Table(title=f"[bold]{category} Indicators[/bold]", box=box.ROUNDED)
                table.add_column("Indicator", style="cyan")
                table.add_column("Syntax Pattern")

                for indicator in indicators:
                    if indicator == "rsi":
                        table.add_row("RSI", "rsi_<period> (e.g., rsi_14, rsi_7)")
                    elif indicator == "ema":
                        table.add_row("EMA", "ema_<period> (e.g., ema_20, ema_50)")
                    elif indicator == "ema_chgpct":
                        table.add_row("EMA % Change", "ema_<ema_period>_chgpct_<change_period> (e.g., ema_20_chgpct_5)")
                    elif indicator == "sma":
                        table.add_row("SMA", "sma_<period> (e.g., sma_50, sma_200)")
                    elif indicator == "macd":
                        table.add_row("MACD", "macd_<fast>_<slow>_<signal> (e.g., macd_12_26_9)")
                    elif indicator == "roc":
                        table.add_row("ROC", "roc_<period> (e.g., roc_12, roc_5)")
                    elif indicator == "adx":
                        table.add_row("ADX", "adx_<period> (e.g., adx_14)")
                    elif indicator == "atr":
                        table.add_row("ATR", "atr_<period> (e.g., atr_14)")
                    elif indicator == "bb":
                        table.add_row("Bollinger Bands", "bb_<period>_<std> (e.g., bb_20_2)")
                    elif indicator == "bb_lower":
                        table.add_row("BB Lower", "bb_lower_<period>_<std> (e.g., bb_lower_20_2)")
                    elif indicator == "bb_middle":
                        table.add_row("BB Middle", "bb_middle_<period>_<std> (e.g., bb_middle_20_2)")
                    elif indicator == "bb_upper":
                        table.add_row("BB Upper", "bb_upper_<period>_<std> (e.g., bb_upper_20_2)")
                    elif indicator == "ha":
                        table.add_row("Heikin Ashi", "ha, ha_open, ha_close, ha_high, ha_low, ha_green, ha_red")
                    elif indicator == "sha":
                        table.add_row("Smooth HA", "sha_<period>, sha_<period>_close, sha_<period>_green, sha_<period>_red")
                    elif indicator == "hama":
                        table.add_row("Hull MA", "hama_<period> (e.g., hama_20)")
                    elif indicator == "ad":
                        table.add_row("Accumulation/Distribution", "ad")
                    elif indicator == "obv":
                        table.add_row("On-Balance Volume", "obv")
                    elif indicator == "mfi":
                        table.add_row("Money Flow Index", "mfi_<period> (e.g., mfi_14)")
                    elif indicator == "cmf":
                        table.add_row("Chaikin Money Flow", "cmf_<period> (e.g., cmf_20)")
                    elif indicator == "vratio":
                        table.add_row("Volume Ratio", "vratio_<period> (e.g., vratio_20)")
                    elif indicator == "vwap":
                        table.add_row("VWAP", "vwap")
                    elif indicator == "volume_sma":
                        table.add_row("Volume SMA", "volume_sma_<period> (e.g., volume_sma_20)")
                    elif indicator == "chgpct":
                        table.add_row("Change %", "chgpct_<period> (e.g., chgpct_1, chgpct_5, chgpct_30)")
                    elif indicator == "chglog":
                        table.add_row("Log Change", "chglog_<period> (e.g., chglog_1)")
                    elif indicator == "pivot":
                        table.add_row("Pivot Points", "pivot_classic, pivot_fibonacci, pivot_woodie")

                console.print(table)

        except Exception as e:
            console.print(f"[red]✗[/red] Error listing indicators: {e}")

    def _handle_show(self, parts: List[str]):
        """Show indicator definition."""
        if not parts:
            console.print("[red]✗[/red] Usage: indicators show <name>")
            console.print("Examples: indicators show ema_20")
            console.print("          indicators show rsi_14")
            console.print("          indicators show ema_20_chgpct_5")
            return

        indicator_name = parts[0]

        # Define indicator documentation
        doc_map = {
            "rsi": {
                "name": "RSI (Relative Strength Index)",
                "description": "Momentum oscillator measuring speed and magnitude of price changes",
                "range": "0-100",
                "formula": "RSI = 100 - (100 / (1 + RS))\nRS = Average Gain / Average Loss (over period)",
                "syntax": "rsi_<period>",
                "examples": ["rsi_14", "rsi_7"],
                "interpretation": "< 30: Oversold, > 70: Overbought",
            },
            "ema": {
                "name": "EMA (Exponential Moving Average)",
                "description": "Trend-following indicator with more weight on recent prices",
                "formula": "EMA = (Close - EMA[previous]) × multiplier + EMA[previous]\nmultiplier = 2 / (period + 1)",
                "syntax": "ema_<period>",
                "examples": ["ema_20", "ema_50", "ema_200"],
                "interpretation": "Price above EMA: Uptrend, Price below EMA: Downtrend",
            },
            "ema_chgpct": {
                "name": "EMA % Change (EMA Percentage Change)",
                "description": "Percentage change of an EMA over a specified number of days",
                "formula": "Change% = ((EMA - EMA[change_period days ago]) / EMA[change_period days ago]) * 100",
                "syntax": "ema_<ema_period>_chgpct_<change_period>",
                "examples": ["ema_20_chgpct_5", "ema_50_chgpct_10", "ema_10_chgpct_3"],
                "interpretation": "Positive: EMA rising, Negative: EMA falling",
            },
            "sma": {
                "name": "SMA (Simple Moving Average)",
                "description": "Average of closing prices over a specified number of periods",
                "formula": "SMA = Sum(Close[period]) / period",
                "syntax": "sma_<period>",
                "examples": ["sma_50", "sma_200"],
                "interpretation": "Price crossing above SMA: Bullish signal, Below: Bearish signal",
            },
            "macd": {
                "name": "MACD (Moving Average Convergence Divergence)",
                "description": "Trend-following momentum indicator",
                "formula": "MACD = EMA(12) - EMA(26)\nSignal = EMA(MACD, 9)",
                "syntax": "macd_<fast>_<slow>_<signal>",
                "examples": ["macd_12_26_9"],
                "interpretation": "MACD > Signal: Bullish, MACD < Signal: Bearish",
            },
            "roc": {
                "name": "ROC (Rate of Change)",
                "description": "Momentum indicator measuring rate of price change",
                "formula": "ROC = ((Close - Close[period]) / Close[period]) * 100",
                "syntax": "roc_<period>",
                "examples": ["roc_12", "roc_5"],
                "interpretation": "Positive ROC: Momentum, Negative ROC: Declining momentum",
            },
            "adx": {
                "name": "ADX (Average Directional Index)",
                "description": "Measures trend strength (not direction)",
                "range": "0-100",
                "formula": "Combines +DI and -DI over a smoothed period",
                "syntax": "adx_<period>",
                "examples": ["adx_14"],
                "interpretation": "> 25: Strong trend, < 20: Weak trend, 20-25: Neutral",
            },
            "atr": {
                "name": "ATR (Average True Range)",
                "description": "Measures market volatility",
                "formula": "ATR = SMA(True Range, period)\nTrue Range = Max(High - Low, |High - Close[previous]|, |Low - Close[previous]|)",
                "syntax": "atr_<period>",
                "examples": ["atr_14"],
                "interpretation": "Higher ATR: Greater volatility, Lower ATR: Lower volatility",
            },
            "bb": {
                "name": "Bollinger Bands",
                "description": "Volatility bands plotted above and below a moving average",
                "formula": "Middle = SMA(period)\nUpper = Middle + (std * std_dev)\nLower = Middle - (std * std_dev)",
                "syntax": "bb_<period>_<std>, bb_upper_<period>_<std>, bb_middle_<period>_<std>, bb_lower_<period>_<std>",
                "examples": ["bb_20_2", "bb_upper_20_2"],
                "interpretation": "Price near upper band: Overbought, Near lower band: Oversold",
            },
            "chgpct": {
                "name": "Change % (Percentage Change)",
                "description": "Percentage change of closing price over a period",
                "formula": "Change% = ((Close - Close[period]) / Close[period]) * 100",
                "syntax": "chgpct_<period>",
                "examples": ["chgpct_1", "chgpct_5", "chgpct_30"],
                "interpretation": "Shows momentum and rate of price change",
            },
        }

        # Try to match indicator name
        matched_indicator = None
        for key in doc_map.keys():
            if indicator_name.startswith(key):
                matched_indicator = key
                break

        if not matched_indicator:
            console.print(f"[red]✗[/red] Indicator not found: {indicator_name}")
            console.print("[yellow]Hint:[/yellow] Try 'indicators list' to see all available indicators")
            return

        doc = doc_map[matched_indicator]

        # Display indicator documentation
        panel = Panel(
            Text(f"{doc['name']}", justify="center", style="bold cyan"),
            style="cyan",
            title=indicator_name,
        )
        console.print(panel)

        console.print(f"\n[bold]Description:[/bold] {doc['description']}")

        if "range" in doc:
            console.print(f"[bold]Range:[/bold] {doc['range']}")

        console.print(f"\n[bold]Formula:[/bold]\n{doc['formula']}")
        console.print(f"\n[bold]Syntax:[/bold] {doc['syntax']}")
        console.print(f"\n[bold]Examples:[/bold]")
        for example in doc['examples']:
            console.print(f"  • {example}")

        console.print(f"\n[bold]Interpretation:[/bold] {doc['interpretation']}")

    def _handle_calc(self, parts: List[str]):
        """Calculate indicator for ticker."""
        if len(parts) < 2:
            console.print("[red]✗[/red] Usage: indicators calc <indicator> <ticker> [start_date]")
            console.print("Examples: indicators calc ema_20 AAPL")
            console.print("          indicators calc rsi_14 AAPL 2024-01-01")
            return

        indicator_name = parts[0]
        ticker = parts[1]
        start_date = parts[2] if len(parts) > 2 else None

        try:
            from tools.indicators import calculate
            from tools.data.core import DataHistory
            import pandas as pd

            console.print(f"[cyan]Calculating {indicator_name} for {ticker}...[/cyan]")

            # Load data
            dh = DataHistory(ticker)
            df = dh.get_all()

            if df.empty:
                console.print(f"[red]✗[/red] No data available for {ticker}")
                return

            # Filter by start_date if provided
            if start_date:
                df = df[df['timestamp'] >= start_date]

            if df.empty:
                console.print(f"[red]✗[/red] No data available from {start_date}")
                return

            # Calculate indicator
            result = calculate([indicator_name], df)

            if indicator_name not in result:
                console.print(f"[red]✗[/red] Indicator {indicator_name} calculation failed")
                return

            values = result[indicator_name]

            # Display results
            table = Table(title=f"{indicator_name} for {ticker}", box=box.ROUNDED)
            table.add_column("Date", style="cyan")
            table.add_column("Value", style="green", justify="right")

            # Show last 20 values
            for i, (date, value) in enumerate(zip(df['timestamp'].tail(20), values.tail(20))):
                date_str = pd.to_datetime(date).strftime('%Y-%m-%d')
                if pd.isna(value):
                    value_str = "[yellow]N/A[/yellow]"
                else:
                    value_str = f"{value:.2f}"
                table.add_row(date_str, value_str)

            console.print(table)

            # Summary statistics
            stats = values.dropna()
            if len(stats) > 0:
                console.print(f"\n[bold]Statistics:[/bold]")
                console.print(f"  Count: {len(stats)}")
                console.print(f"  Mean:  {stats.mean():.2f}")
                console.print(f"  Min:   {stats.min():.2f}")
                console.print(f"  Max:   {stats.max():.2f}")
                console.print(f"  Last:  {stats.iloc[-1]:.2f}")

        except Exception as e:
            console.print(f"[red]✗[/red] Error calculating indicator: {e}")
