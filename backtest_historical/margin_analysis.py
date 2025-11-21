"""
Analyze prediction margins and buffer strategies
"""

import pandas as pd
import numpy as np
import sys


def analyze_margins(backtest_results_file):
    """
    Analyze how close predictions were and test buffer strategies
    """
    df = pd.read_csv(backtest_results_file)
    
    print("\n" + "="*80)
    print("PREDICTION MARGIN ANALYSIS")
    print("="*80)
    
    # Calculate margin (how many points off)
    df['margin'] = df['actual_pra'] - df['recommended_minimum']
    
    # Overall statistics
    print(f"\nTotal Predictions: {len(df)}")
    print(f"Current Win Rate: {df['hit'].mean()*100:.1f}%")
    print(f"\nMargin Statistics:")
    print(f"  Average Margin: {df['margin'].mean():.1f} points")
    print(f"  Median Margin: {df['margin'].median():.1f} points")
    print(f"  Std Dev: {df['margin'].std():.1f} points")
    print(f"\n  Best (furthest over): +{df['margin'].max():.1f} points")
    print(f"  Worst (furthest under): {df['margin'].min():.1f} points")
    
    # Distribution of margins
    print(f"\n{'='*80}")
    print("MARGIN DISTRIBUTION")
    print("="*80)
    
    bins = [
        (-float('inf'), -10, 'Lost by 10+ points'),
        (-10, -5, 'Lost by 5-10 points'),
        (-5, -2, 'Lost by 2-5 points'),
        (-2, 0, 'Lost by 0-2 points (close!)'),
        (0, 2, 'Won by 0-2 points (close!)'),
        (2, 5, 'Won by 2-5 points'),
        (5, 10, 'Won by 5-10 points'),
        (10, 20, 'Won by 10-20 points'),
        (20, float('inf'), 'Won by 20+ points')
    ]
    
    for min_val, max_val, label in bins:
        if min_val == -float('inf'):
            count = len(df[df['margin'] < max_val])
        elif max_val == float('inf'):
            count = len(df[df['margin'] >= min_val])
        else:
            count = len(df[(df['margin'] >= min_val) & (df['margin'] < max_val)])
        
        pct = (count / len(df)) * 100
        print(f"{label:30} {count:4d} picks ({pct:5.1f}%)")
    
    # Test buffer strategies
    print(f"\n{'='*80}")
    print("BUFFER STRATEGY TESTING")
    print("="*80)
    
    buffers = [0, 2, 3, 5, 7, 10]
    
    results = []
    
    for buffer in buffers:
        # Calculate win rate with buffer
        df[f'buffered_min_{buffer}'] = df['recommended_minimum'] - buffer
        df[f'hit_with_{buffer}_buffer'] = df['actual_pra'] >= df[f'buffered_min_{buffer}']
        
        total = len(df)
        wins = df[f'hit_with_{buffer}_buffer'].sum()
        win_rate = (wins / total) * 100
        
        # For high confidence only
        high_conf = df[df['meets_90_threshold']]
        if not high_conf.empty:
            hc_wins = high_conf[f'hit_with_{buffer}_buffer'].sum()
            hc_total = len(high_conf)
            hc_rate = (hc_wins / hc_total) * 100
        else:
            hc_rate = 0
        
        results.append({
            'buffer': buffer,
            'total_picks': total,
            'wins': wins,
            'win_rate': win_rate,
            'high_conf_rate': hc_rate
        })
    
    print("\n📊 ALL PREDICTIONS:")
    print(f"{'Buffer':<10} {'Wins':<10} {'Total':<10} {'Win Rate':<15}")
    print("-" * 50)
    for r in results:
        print(f"{r['buffer']:>3} pts    {r['wins']:<10} {r['total_picks']:<10} {r['win_rate']:>6.1f}%")
    
    print("\n🎯 HIGH CONFIDENCE (90%+) ONLY:")
    print(f"{'Buffer':<10} {'Win Rate':<15}")
    print("-" * 30)
    for r in results:
        print(f"{r['buffer']:>3} pts    {r['high_conf_rate']:>6.1f}%")
    
    # Show examples of picks that would have been saved by 5-point buffer
    print(f"\n{'='*80}")
    print("PICKS SAVED BY 5-POINT BUFFER (Lost without buffer, Won with buffer)")
    print("="*80)
    
    saved = df[(~df['hit']) & (df['hit_with_5_buffer'])]
    
    if not saved.empty:
        print(f"\nTotal picks saved: {len(saved)}")
        print("\nExamples:")
        print(saved[['player_name', 'recommended_minimum', 'actual_pra', 'margin', 
                    'confidence']].head(20).to_string(index=False))
    
    # Show picks that STILL lost with 5-point buffer
    print(f"\n{'='*80}")
    print("PICKS THAT STILL LOST WITH 5-POINT BUFFER")
    print("="*80)
    
    still_lost = df[~df['hit_with_5_buffer']]
    
    if not still_lost.empty:
        print(f"\nTotal still lost: {len(still_lost)}")
        print(f"Percentage: {(len(still_lost)/len(df)*100):.1f}%")
        print("\nWorst misses:")
        worst = still_lost.nsmallest(10, 'margin')
        print(worst[['player_name', 'recommended_minimum', 'buffered_min_5',
                    'actual_pra', 'margin']].to_string(index=False))
    
    # Save detailed analysis
    output_file = backtest_results_file.replace('.csv', '_margin_analysis.csv')
    
    # Keep relevant columns
    analysis_df = df[['date', 'player_name', 'season_avg', 'recommended_minimum', 
                     'actual_pra', 'margin', 'hit', 'confidence', 'meets_90_threshold',
                     'buffered_min_5', 'hit_with_5_buffer']]
    
    analysis_df.to_csv(output_file, index=False)
    print(f"\n✓ Detailed analysis saved to {output_file}")
    
    # Summary recommendations
    print(f"\n{'='*80}")
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    best_buffer = max(results, key=lambda x: x['high_conf_rate'])
    
    print(f"\n✅ BEST BUFFER: {best_buffer['buffer']} points")
    print(f"   Win Rate: {best_buffer['high_conf_rate']:.1f}% (high confidence)")
    print(f"   Total Win Rate: {best_buffer['win_rate']:.1f}% (all picks)")
    
    print(f"\n🎯 YOUR STRATEGY (5-point buffer):")
    buffer_5 = next(r for r in results if r['buffer'] == 5)
    print(f"   Win Rate: {buffer_5['high_conf_rate']:.1f}% (high confidence)")
    print(f"   Total Win Rate: {buffer_5['win_rate']:.1f}% (all picks)")
    print(f"   Picks Saved: {len(saved)} picks wouldn't have lost")
    
    print("\n" + "="*80)


def main():
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python margin_analysis.py BACKTEST_RESULTS_FILE")
        print("\nExample:")
        print("  python margin_analysis.py ../data/backtest/historical_results_2025-11-05_to_2025-11-19_backtest_results.csv")
        return
    
    results_file = sys.argv[1]
    analyze_margins(results_file)


if __name__ == "__main__":
    main()
