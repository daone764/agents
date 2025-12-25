"""
Polymarket Trading Bot - Desktop Launcher
Double-click to run the trading analysis and receive email report.
"""
import os
import sys

# Set up the environment
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def main():
    print("=" * 60)
    print("   POLYMARKET AUTONOMOUS TRADING BOT")
    print("=" * 60)
    print()
    
    try:
        from agents.trading.improved_trader import ImprovedTrader
        
        print("Starting market analysis...")
        print("This may take 1-2 minutes.\n")
        
        trader = ImprovedTrader()
        trader.run_analysis()
        
        print("\n" + "=" * 60)
        print("   ANALYSIS COMPLETE!")
        print("=" * 60)
        print()
        print("Check your email for the HTML report!")
        print("Reports also saved to: trading_report_*.html")
        print()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nPress Enter to close...")
    input()

if __name__ == "__main__":
    main()
