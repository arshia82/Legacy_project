# FILE: myfita/apps/backend/matching/services/scoring_service.py

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ScoreComponent:
    """Individual score component"""
    name: str
    weight: float
    raw_score: float  # 0-1
    weighted_score: float
    reason: Optional[str] = None


@dataclass
class DetailedScore:
    """Detailed scoring breakdown"""
    total_score: Decimal
    max_possible: Decimal
    percentage: Decimal
    components: List[ScoreComponent]
    top_reasons: List[str]


class ScoringService:
    """
    Centralized scoring logic for matching.
    Separated for testability and future ML integration.
    
    This service can be swapped with ML-based scoring in Phase 2
    without changing the matching service interface.
    """
    
    # Default weights (can be overridden)
    DEFAULT_WEIGHTS = {
        "specialty": 35,
        "location": 20,
        "price": 15,
        "experience": 10,
        "rating": 10,
        "activity": 5,
        "gender": 5,
    }
    
    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize with custom weights if provided.
        
        Args:
            weights: Dict of component name to weight value
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.max_score = sum(self.weights.values())
    
    def calculate_total(self, components: Dict[str, float]) -> DetailedScore:
        """
        Calculate total score from component scores.
        
        Args:
            components: Dict of component name to raw score (0-1)
            
        Returns:
            DetailedScore with breakdown
        """
        
        score_components = []
        total = 0
        reasons = []
        
        for name, raw_score in components.items():
            weight = self.weights.get(name, 0)
            weighted = raw_score * weight
            total += weighted
            
            component = ScoreComponent(
                name=name,
                weight=weight,
                raw_score=raw_score,
                weighted_score=weighted
            )
            score_components.append(component)
        
        # Sort by weighted score for top reasons
        score_components.sort(key=lambda x: x.weighted_score, reverse=True)
        
        return DetailedScore(
            total_score=Decimal(str(round(total, 2))),
            max_possible=Decimal(str(self.max_score)),
            percentage=Decimal(str(round((total / self.max_score) * 100, 1))),
            components=score_components,
            top_reasons=reasons
        )
    
    def normalize_score(self, score: float, min_val: float, max_val: float) -> float:
        """
        Normalize a value to 0-1 range.
        
        Args:
            score: Raw score value
            min_val: Minimum expected value
            max_val: Maximum expected value
            
        Returns:
            Normalized score between 0 and 1
        """
        if max_val == min_val:
            return 0.5
        
        normalized = (score - min_val) / (max_val - min_val)
        return max(0, min(1, normalized))
    
    def calculate_text_similarity(
        self,
        text1: str,
        text2: str,
        keywords: List[str] = None
    ) -> float:
        """
        Calculate simple text similarity score.
        Used for matching specialties, goals, etc.
        
        Args:
            text1: First text
            text2: Second text
            keywords: Optional list of important keywords to weight higher
            
        Returns:
            Similarity score between 0 and 1
        """
        
        if not text1 or not text2:
            return 0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0
        
        # Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        base_similarity = len(intersection) / len(union) if union else 0
        
        # Boost for keyword matches
        if keywords:
            keyword_set = set(k.lower() for k in keywords)
            keyword_matches = intersection & keyword_set
            keyword_boost = len(keyword_matches) * 0.1
            base_similarity = min(1, base_similarity + keyword_boost)
        
        return base_similarity
    
    def calculate_range_fit(
        self,
        value: float,
        target_min: float,
        target_max: float,
        tolerance: float = 0.2
    ) -> float:
        """
        Calculate how well a value fits within a target range.
        
        Args:
            value: Value to check
            target_min: Minimum acceptable value
            target_max: Maximum acceptable value
            tolerance: How much outside range is still acceptable (0-1)
            
        Returns:
            Fit score between 0 and 1
        """
        
        if target_min <= value <= target_max:
            return 1.0
        
        # Calculate distance from range
        if value < target_min:
            distance = target_min - value
            range_size = target_max - target_min if target_max > target_min else target_min
        else:
            distance = value - target_max
            range_size = target_max - target_min if target_max > target_min else target_max
        
        # Score based on distance relative to tolerance
        tolerance_amount = range_size * tolerance
        if distance <= tolerance_amount:
            return 1 - (distance / tolerance_amount) * 0.5
        
        return max(0, 0.5 - (distance - tolerance_amount) / range_size)
    
    def apply_decay(
        self,
        score: float,
        days_old: int,
        half_life_days: int = 30
    ) -> float:
        """
        Apply time decay to a score.
        Used for activity/freshness scoring.
        
        Args:
            score: Original score
            days_old: How many days old
            half_life_days: Days until score is halved
            
        Returns:
            Decayed score
        """
        import math
        
        decay_factor = math.pow(0.5, days_old / half_life_days)
        return score * decay_factor
    
    def combine_scores(
        self,
        scores: List[Tuple[float, float]],
        method: str = "weighted_average"
    ) -> float:
        """
        Combine multiple scores into one.
        
        Args:
            scores: List of (score, weight) tuples
            method: Combination method ("weighted_average", "max", "min", "product")
            
        Returns:
            Combined score
        """
        
        if not scores:
            return 0
        
        if method == "weighted_average":
            total_weight = sum(w for _, w in scores)
            if total_weight == 0:
                return 0
            return sum(s * w for s, w in scores) / total_weight
        
        elif method == "max":
            return max(s for s, _ in scores)
        
        elif method == "min":
            return min(s for s, _ in scores)
        
        elif method == "product":
            result = 1
            for s, _ in scores:
                result *= s
            return result
        
        return 0