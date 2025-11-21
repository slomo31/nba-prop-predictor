import sys

# Read the file
with open('main.py', 'r') as f:
    content = f.read()

# Check if main() exists
if 'def main():' not in content:
    # Find the if __name__ line
    if_name_pos = content.rfind('if __name__ == "__main__":')
    
    if if_name_pos > 0:
        # Insert main function before it
        main_function = '''

def main():
    """Main execution function"""
    system = NBAPropSystem()
    
    print("\\n" + "=" * 80)
    print("NBA PROP PREDICTOR SYSTEM")
    print("High-Confidence Player Prop Predictions (90%+ Win Rate)")
    print("=" * 80)
    
    if len(sys.argv) < 2:
        print("\\nUsage:")
        print("  python main.py update           - Update player stats and odds data")
        print("  python main.py train            - Train/retrain ML model")
        print("  python main.py predict          - Generate predictions")
        print("  python main.py backtest         - Run backtesting analysis")
        print("  python main.py full             - Run complete pipeline")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'update':
        system.update_data()
    
    elif command == 'train':
        system.train_model()
    
    elif command == 'predict':
        pred_df = system.make_predictions()
        system.display_predictions(pred_df)
    
    elif command == 'backtest':
        system.run_backtest()
    
    elif command == 'full':
        print("\\n[1/4] Updating data...")
        if not system.update_data():
            print("\\nData update failed. Continuing with existing data...")
        
        print("\\n[2/4] Training model...")
        if not system.train_model():
            print("\\nModel training failed. Exiting...")
            return
        
        print("\\n[3/4] Generating predictions...")
        pred_df = system.make_predictions()
        system.display_predictions(pred_df)
        
        print("\\n[4/4] Running backtest...")
        system.run_backtest()
    
    else:
        print(f"\\nUnknown command: {command}")
        print("Use 'python main.py' to see available commands")


'''
        
        content = content[:if_name_pos] + main_function + content[if_name_pos:]
        
        with open('main.py', 'w') as f:
            f.write(content)
        
        print("✓ Added main() function")
    else:
        print("✗ Could not find if __name__ line")
else:
    print("✓ main() function already exists")
