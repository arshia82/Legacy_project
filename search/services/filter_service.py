# FILE: myfita/apps/backend/search/services/filter_service.py

"""
FILTER SERVICE

Handles advanced filtering logic for search.
Provides filter validation, normalization, and dynamic filter options.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Count, Min, Max, Avg


@dataclass
class FilterOption:
    """Single filter option"""
    value: str
    label: str
    count: int = 0
    selected: bool = False


@dataclass
class FilterDefinition:
    """Filter definition with options"""
    name: str
    label: str
    type: str  # select, multi_select, range, boolean
    options: List[FilterOption] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None


class FilterService:
    """
    Service for managing search filters.
    
    Provides:
    - Filter validation
    - Dynamic filter options based on data
    - Filter normalization
    - Price range suggestions
    """
    
    # Standard filter definitions
    COACH_FILTERS = {
        "specialty": {
            "label": "تخصص",
            "type": "multi_select",
            "options": [
                ("weight_loss", "کاهش وزن"),
                ("muscle_gain", "عضله‌سازی"),
                ("strength", "قدرتی"),
                ("bodybuilding", "بدنسازی"),
                ("powerlifting", "پاورلیفتینگ"),
                ("crossfit", "کراسفیت"),
                ("calisthenics", "کلیستنیکس"),
                ("nutrition", "تغذیه"),
                ("competition_prep", "آمادگی مسابقه"),
                ("rehabilitation", "توانبخشی"),
                ("yoga", "یوگا"),
                ("pilates", "پیلاتس"),
            ]
        },
        "city": {
            "label": "شهر",
            "type": "select",
            "dynamic": True
        },
        "min_rating": {
            "label": "حداقل امتیاز",
            "type": "range",
            "min": 0,
            "max": 5,
            "step": 0.5
        },
        "price_range": {
            "label": "محدوده قیمت",
            "type": "range",
            "min": 0,
            "max": 10000000,
            "step": 100000
        },
        "experience_level": {
            "label": "سطح مناسب",
            "type": "multi_select",
            "options": [
                ("beginner", "مبتدی"),
                ("intermediate", "متوسط"),
                ("advanced", "پیشرفته"),
                ("professional", "حرفه‌ای"),
            ]
        },
        "gender": {
            "label": "جنسیت",
            "type": "select",
            "options": [
                ("male", "مرد"),
                ("female", "زن"),
            ]
        },
        "is_verified": {
            "label": "تایید شده",
            "type": "boolean"
        },
        "has_availability": {
            "label": "ظرفیت دارد",
            "type": "boolean"
        },
    }
    
    PROGRAM_FILTERS = {
        "category": {
            "label": "دسته‌بندی",
            "type": "multi_select",
            "options": [
                ("weight_loss", "کاهش وزن"),
                ("muscle_gain", "عضله‌سازی"),
                ("strength", "قدرتی"),
                ("endurance", "استقامت"),
                ("flexibility", "انعطاف‌پذیری"),
                ("competition_prep", "آمادگی مسابقه"),
                ("general_fitness", "تناسب اندام عمومی"),
                ("rehabilitation", "توانبخشی"),
                ("nutrition", "تغذیه"),
                ("hybrid", "ترکیبی"),
            ]
        },
        "difficulty": {
            "label": "سطح دشواری",
            "type": "multi_select",
            "options": [
                ("beginner", "مبتدی"),
                ("intermediate", "متوسط"),
                ("advanced", "پیشرفته"),
                ("professional", "حرفه‌ای"),
            ]
        },
        "price_range": {
            "label": "محدوده قیمت",
            "type": "range",
            "min": 0,
            "max": 10000000,
            "step": 100000
        },
        "duration": {
            "label": "مدت برنامه (هفته)",
            "type": "range",
            "min": 1,
            "max": 52,
            "step": 1
        },
        "min_rating": {
            "label": "حداقل امتیاز",
            "type": "range",
            "min": 0,
            "max": 5,
            "step": 0.5
        },
        "is_featured": {
            "label": "ویژه",
            "type": "boolean"
        },
        "is_bestseller": {
            "label": "پرفروش",
            "type": "boolean"
        },
        "has_discount": {
            "label": "تخفیف دار",
            "type": "boolean"
        },
    }
    
    def validate_filters(
        self,
        filters: Dict[str, Any],
        filter_type: str = "coach"
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate and normalize filters.
        
        Args:
            filters: Raw filter dict from request
            filter_type: "coach" or "program"
            
        Returns:
            Tuple of (validated_filters, error_messages)
        """
        
        definitions = self.COACH_FILTERS if filter_type == "coach" else self.PROGRAM_FILTERS
        validated = {}
        errors = []
        
        for key, value in filters.items():
            if key not in definitions:
                # Skip unknown filters
                continue
            
            definition = definitions[key]
            filter_def_type = definition.get("type")
            
            try:
                if filter_def_type == "boolean":
                    validated[key] = self._validate_boolean(value)
                
                elif filter_def_type == "select":
                    valid_options = [opt[0] for opt in definition.get("options", [])]
                    if definition.get("dynamic"):
                        # Dynamic options - accept any string
                        validated[key] = str(value)
                    elif value in valid_options:
                        validated[key] = value
                    else:
                        errors.append(f"Invalid value for {key}")
                
                elif filter_def_type == "multi_select":
                    valid_options = [opt[0] for opt in definition.get("options", [])]
                    values = value if isinstance(value, list) else [value]
                    validated_values = [v for v in values if v in valid_options]
                    if validated_values:
                        validated[key] = validated_values
                
                elif filter_def_type == "range":
                    min_val = definition.get("min", 0)
                    max_val = definition.get("max", float("inf"))
                    
                    if isinstance(value, dict):
                        # Range with min/max
                        if "min" in value:
                            validated[f"min_{key}"] = max(min_val, float(value["min"]))
                        if "max" in value:
                            validated[f"max_{key}"] = min(max_val, float(value["max"]))
                    else:
                        # Single value (minimum)
                        validated[f"min_{key}"] = max(min_val, float(value))
            
            except (ValueError, TypeError) as e:
                errors.append(f"Invalid value for {key}: {str(e)}")
        
        return validated, errors
    
    def _validate_boolean(self, value: Any) -> bool:
        """Validate boolean filter value"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    
    def get_filter_definitions(
        self,
        filter_type: str = "coach",
        include_counts: bool = False,
        queryset=None
    ) -> List[FilterDefinition]:
        """
        Get filter definitions with optional counts.
        
        Args:
            filter_type: "coach" or "program"
            include_counts: Whether to include option counts
            queryset: Optional queryset for counting
            
        Returns:
            List of FilterDefinition objects
        """
        
        definitions = self.COACH_FILTERS if filter_type == "coach" else self.PROGRAM_FILTERS
        result = []
        
        for name, config in definitions.items():
            filter_def = FilterDefinition(
                name=name,
                label=config["label"],
                type=config["type"]
            )
            
            if config["type"] in ("select", "multi_select"):
                options = []
                for value, label in config.get("options", []):
                    count = 0
                    if include_counts and queryset is not None:
                        # Count would be calculated based on queryset
                        pass
                    options.append(FilterOption(value=value, label=label, count=count))
                filter_def.options = options
            
            elif config["type"] == "range":
                filter_def.min_value = config.get("min", 0)
                filter_def.max_value = config.get("max", 100)
                filter_def.step = config.get("step", 1)
            
            result.append(filter_def)
        
        return result
    
    def get_price_suggestions(
        self,
        filter_type: str = "coach"
    ) -> List[Dict[str, Any]]:
        """
        Get price range suggestions.
        
        Returns common price brackets for quick filtering.
        """
        
        suggestions = [
            {"label": "رایگان", "min": 0, "max": 0},
            {"label": "تا ۵۰۰ هزار تومان", "min": 0, "max": 500000},
            {"label": "۵۰۰ هزار تا ۱ میلیون", "min": 500000, "max": 1000000},
            {"label": "۱ تا ۲ میلیون", "min": 1000000, "max": 2000000},
            {"label": "۲ تا ۵ میلیون", "min": 2000000, "max": 5000000},
            {"label": "بیش از ۵ میلیون", "min": 5000000, "max": None},
        ]
        
        return suggestions
    
    def build_filter_url_params(self, filters: Dict[str, Any]) -> str:
        """
        Build URL query string from filters.
        
        Args:
            filters: Validated filter dict
            
        Returns:
            URL query string
        """
        
        params = []
        
        for key, value in filters.items():
            if value is None:
                continue
            
            if isinstance(value, list):
                for v in value:
                    params.append(f"{key}={v}")
            elif isinstance(value, bool):
                params.append(f"{key}={'true' if value else 'false'}")
            else:
                params.append(f"{key}={value}")
        
        return "&".join(params)
    
    def parse_filter_url_params(self, query_string: str) -> Dict[str, Any]:
        """
        Parse URL query string to filters.
        
        Args:
            query_string: URL query string
            
        Returns:
            Filter dict
        """
        
        from urllib.parse import parse_qs
        
        parsed = parse_qs(query_string)
        filters = {}
        
        for key, values in parsed.items():
            if len(values) == 1:
                # Single value
                value = values[0]
                if value.lower() in ("true", "false"):
                    filters[key] = value.lower() == "true"
                else:
                    try:
                        filters[key] = int(value)
                    except ValueError:
                        try:
                            filters[key] = float(value)
                        except ValueError:
                            filters[key] = value
            else:
                # Multiple values (multi-select)
                filters[key] = values
        
        return filters