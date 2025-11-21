"""
Apply 5-point buffer to predictions automatically
"""

import pandas as pd
from config import PREDICTIONS_CSV

def apply_buffer(buffer_points=5):
    """Apply buffer to all predictions"""
    
    # Load predictions
    df = pd.read_csv(PREDICTIONS_CSV)
    
    # Apply buffer
    df['original_minimum'] = df['recommended_minimum']
    df['recommended_minimum'] = df['recommended_minimum'] - buffer_points
    
    # Save back
    df.to_csv(PREDICTIONS_CSV, index=False)
    
    # Also update dated file if it exists
    import os
    from datetime import datetime
    date_str = datetime.now().strftime('%Y-%m-%d')
    dated_file = PREDICTIONS_CSV.replace('.csv', f'_{date_str}.csv')
    
    if os.path.exists(dated_file):
        df.to_csv(dated_file, index=False)
    
    print(f"✓ Applied {buffer_points}-point buffer to {len(df)} predictions")
    print(f"\nExample:")
    print(df[['player_name', 'original_minimum', 'recommended_minimum']].head(5))

if __name__ == "__main__":
    apply_buffer(5)
