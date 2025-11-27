import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os
from datetime import datetime

# --- CONFIGURATION ---
# Symbol for Gold Futures (GC=F) is used here for XAUUSD proxy, as XAUUSD itself isn't reliably available on yfinance
SYMBOL = 'GC=F'
# We are scheduled to run hourly, so we fetch hourly data.
INTERVAL = '1h'
PERIOD = '3d' # Fetch enough data for indicators (3 days of hourly data)

# --- CORE TRADING CLASS ---

class TradingBot:
    """
    A modular and professional class for handling data,
    calculating indicators, and generating trade signals.
    """
    def __init__(self, symbol, interval, period):
        self.symbol = symbol
        self.interval = interval
        self.period = period
        self.data = pd.DataFrame()
        print(f"Initialized TradingBot for {symbol} ({interval} interval).")

    def fetch_data(self):
        """Fetches historical OHLC data using yfinance."""
        try:
            print("Fetching data...")
            # Using auto_adjust=True to simplify the data
            ticker = yf.Ticker(self.symbol)
            self.data = ticker.history(interval=self.interval, period=self.period, auto_adjust=True)
            if self.data.empty:
                raise ValueError("Fetched data is empty. Check symbol and connection.")
            print(f"Data fetched successfully. Latest close: {self.data['Close'].iloc[-1]}")
        except Exception as e:
            print(f"Error fetching data: {e}")
            self.data = None

    def calculate_indicators(self):
        """Calculates advanced indicators using pandas_ta."""
        if self.data is None or self.data.empty:
            return

        print("Calculating technical indicators...")

        # 1. Relative Strength Index (RSI)
        self.data.ta.rsi(append=True)

        # 2. Moving Average Convergence Divergence (MACD)
        # Using default fast (12), slow (26), signal (9)
        self.data.ta.macd(append=True)

        # 3. Simple Moving Averages (for Trend Filter)
        self.data.ta.sma(length=50, append=True) # Short term trend
        self.data.ta.sma(length=200, append=True) # Long term trend

        # Rename MACD columns for easier access
        self.data = self.data.rename(columns={
            'MACD_12_26_9': 'MACD',
            'MACDH_12_26_9': 'MACD_H', # MACD Histogram
            'MACDS_12_26_9': 'MACD_S'  # MACD Signal Line
        })

    def generate_signal(self):
        """
        Implements a professional, multi-factor trading strategy.
        Strategy: Trend-Filtered RSI/MACD Crossover
        1. Trend Filter: Price must be above 200 SMA (long-term uptrend).
        2. Momentum Entry (RSI/MACD): MACD must cross above its signal line AND RSI must be rising and below 70.
        """
        if self.data is None or self.data.empty:
            print("Cannot generate signal: Data is missing.")
            return 'HOLD', None

        # Get the latest row of data
        latest = self.data.iloc[-1]
        previous = self.data.iloc[-2]
        
        # Ensure all required indicator columns exist
        required_cols = ['RSI_14', 'MACD', 'MACD_S', 'SMA_200']
        if not all(col in latest for col in required_cols):
             print(f"Missing required indicator data: {required_cols}")
             return 'HOLD', None
        
        # --- 1. Trend Filter ---
        is_uptrend = latest['Close'] > latest['SMA_200']
        
        # --- 2. Momentum & Crossover Conditions ---
        # MACD crosses above Signal Line (Bullish Crossover)
        is_macd_bullish_cross = (latest['MACD'] > latest['MACD_S']) and (previous['MACD'] <= previous['MACD_S'])
        
        # RSI condition: not overbought (below 70) and rising
        is_rsi_rising = latest['RSI_14'] > previous['RSI_14']
        is_rsi_safe = latest['RSI_14'] < 70
        
        # --- Final Signal Generation (Prioritizing BUY/SELL for simplicity) ---
        signal = 'HOLD'
        
        if is_uptrend and is_macd_bullish_cross and is_rsi_rising and is_rsi_safe:
            signal = 'BUY'
            reason = "STRONG BUY: Confirmed Uptrend (Price > SMA_200) + MACD Bullish Cross + Healthy RSI (< 70)."
        elif latest['Close'] < latest['SMA_200'] and latest['MACD'] < latest['MACD_S'] and latest['RSI_14'] > 50:
             # Example SELL condition: Downtrend (Price < SMA_200) and MACD Bearish, but not oversold
            signal = 'SELL'
            reason = "SELL: Confirmed Downtrend (Price < SMA_200) + MACD Bearish Signal."
        else:
            reason = "HOLD: Awaiting clearer trend or momentum signal."

        print(f"Current Price: {latest['Close']:.2f}, Signal: {signal}, Reason: {reason}")
        
        # Return the signal and the current price
        return signal, latest['Close'], reason

# --- MAIN EXECUTION ---

def run_trading_strategy():
    """Main function to execute the bot when run by GitHub Actions."""
    print(f"--- Trading Logic Execution Start: {datetime.now().isoformat()} ---")
    
    bot = TradingBot(SYMBOL, INTERVAL, PERIOD)
    bot.fetch_data()
    
    if bot.data is None or bot.data.empty:
        print("Exiting due to data fetching failure.")
        return

    bot.calculate_indicators()
    signal, price, reason = bot.generate_signal()
    
    # In a real-world deployed environment, this output could trigger a webhook
    # or an external API call to an exchange.
    
    print("\n--- FINAL ACTION REPORT ---")
    print(f"Asset: {SYMBOL}")
    print(f"Time: {bot.data.index[-1].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Price: {price:.2f}")
    print(f"Signal: {signal}")
    print(f"Reason: {reason}")
    print("---------------------------\n")

if __name__ == '__main__':
    # This block executes when the script is run directly
    run_trading_strategy()
