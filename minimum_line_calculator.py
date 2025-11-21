"""
Calculate intelligent minimum alternate lines for player props
"""

import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MinimumLineCalculator:
    def __init__(self):
        self.confidence_threshold = 0.90
        
    def calculate_realistic_minimum(self, player_stats, main_line):
        """
        Calculate a realistic minimum line that is:
        1. Lower than the main line (easier to hit)
        2. Still challenging (not a gimme)
        3. Based on actual performance data
        
        Parameters:
        - player_stats: dict with player's statistics
        - main_line: the main DraftKings line (e.g., 37.5)
        
        Returns:
        - recommended_minimum: realistic minimum line
        - confidence: confidence percentage
        - reasoning: explanation of the calculation
        """
        
        # Extract key stats
        season_avg = player_stats.get('pts_reb_ast_avg', 0)
        last_5_avg = player_stats.get('last_5_avg', season_avg)
        consistency = player_stats.get('consistency', 0.85)  # How consistent is the player
        
        # If no season average, can't calculate
        if season_avg == 0:
            return None, 0, "Insufficient data"
        
        # Calculate performance metrics
        recent_trend = last_5_avg / season_avg if season_avg > 0 else 1.0
        
        # Determine safety margin based on consistency
        # More consistent players = can go closer to average
        # Less consistent = need bigger cushion
        if consistency > 0.90:
            # Very consistent (like Jokic, Giannis)
            safety_margin = 0.10  # 10% below average
        elif consistency > 0.80:
            # Consistent (most stars)
            safety_margin = 0.15  # 15% below average
        else:
            # Less consistent
            safety_margin = 0.20  # 20% below average
        
        # Calculate base minimum (conservative)
        base_minimum = season_avg * (1 - safety_margin)
        
        # Adjust based on recent form
        if recent_trend > 1.05:
            # Hot streak - can be slightly more aggressive
            form_adjustment = 1.02
        elif recent_trend < 0.95:
            # Cold streak - be more conservative
            form_adjustment = 0.98
        else:
            # Normal form
            form_adjustment = 1.0
        
        recommended_minimum = base_minimum * form_adjustment
        
        # Round to nearest 0.5
        recommended_minimum = round(recommended_minimum * 2) / 2
        
        # Ensure it's lower than main line
        if recommended_minimum >= main_line:
            recommended_minimum = main_line - 2.5  # At least 2.5 points lower
        
        # Ensure it's not too low (no gimmes)
        min_acceptable = season_avg * 0.75  # Never go below 75% of average
        if recommended_minimum < min_acceptable:
            recommended_minimum = min_acceptable
            recommended_minimum = round(recommended_minimum * 2) / 2
        
        # Calculate confidence based on how much cushion we have
        cushion = season_avg - recommended_minimum
        cushion_percentage = cushion / season_avg
        
        # More cushion = higher confidence
        if cushion_percentage > 0.25:
            confidence = 0.95
        elif cushion_percentage > 0.20:
            confidence = 0.93
        elif cushion_percentage > 0.15:
            confidence = 0.91
        else:
            confidence = 0.89
        
        # Build reasoning
        reasoning = self._build_reasoning(
            season_avg, last_5_avg, recommended_minimum, 
            main_line, cushion, consistency
        )
        
        return recommended_minimum, confidence, reasoning
    
    def _build_reasoning(self, season_avg, last_5_avg, recommended_min, 
                        main_line, cushion, consistency):
        """Build human-readable reasoning"""
        parts = []
        
        # Average comparison
        parts.append(f"Season avg: {season_avg:.1f}")
        
        # Recent form
        if last_5_avg > season_avg * 1.05:
            parts.append(f"trending UP (L5: {last_5_avg:.1f})")
        elif last_5_avg < season_avg * 0.95:
            parts.append(f"trending down (L5: {last_5_avg:.1f})")
        else:
            parts.append(f"consistent (L5: {last_5_avg:.1f})")
        
        # Cushion
        parts.append(f"{cushion:.1f} pt cushion")
        
        # vs main line
        diff_from_main = main_line - recommended_min
        parts.append(f"{diff_from_main:.1f} pts below DK line")
        
        return " | ".join(parts)
    
    def calculate_consistency(self, game_log):
        """
        Calculate player consistency based on game log
        Returns value between 0-1 (1 = very consistent)
        """
        if game_log is None or len(game_log) < 5:
            return 0.85  # Default
        
        # Calculate coefficient of variation (lower = more consistent)
        std = game_log['pts_reb_ast'].std()
        mean = game_log['pts_reb_ast'].mean()
        
        if mean == 0:
            return 0.85
        
        cv = std / mean
        
        # Convert to consistency score (0-1)
        # CV of 0.1 = very consistent (0.95)
        # CV of 0.3 = less consistent (0.75)
        consistency = max(0.7, min(0.98, 1 - (cv * 2)))
        
        return consistency


def test_calculator():
    """Test the minimum line calculator"""
    calc = MinimumLineCalculator()
    
    # Test case 1: Steph Curry
    print("Test Case 1: Stephen Curry")
    print("-" * 50)
    curry_stats = {
        'pts_reb_ast_avg': 35.2,
        'last_5_avg': 36.8,
        'consistency': 0.88
    }
    main_line = 37.5
    
    min_line, confidence, reasoning = calc.calculate_realistic_minimum(
        curry_stats, main_line
    )
    
    print(f"DK Main Line: {main_line}")
    print(f"Season Average: {curry_stats['pts_reb_ast_avg']}")
    print(f"Recommended Minimum: {min_line}")
    print(f"Confidence: {confidence:.1%}")
    print(f"Reasoning: {reasoning}")
    
    # Test case 2: Role player
    print("\n\nTest Case 2: Role Player")
    print("-" * 50)
    role_player_stats = {
        'pts_reb_ast_avg': 22.5,
        'last_5_avg': 20.8,
        'consistency': 0.75
    }
    main_line = 24.5
    
    min_line, confidence, reasoning = calc.calculate_realistic_minimum(
        role_player_stats, main_line
    )
    
    print(f"DK Main Line: {main_line}")
    print(f"Season Average: {role_player_stats['pts_reb_ast_avg']}")
    print(f"Recommended Minimum: {min_line}")
    print(f"Confidence: {confidence:.1%}")
    print(f"Reasoning: {reasoning}")


if __name__ == "__main__":
    test_calculator()
