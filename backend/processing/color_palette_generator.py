"""
Professional color palette generation based on seasonal color analysis
Provides personalized, confidence-inspiring color recommendations
"""

import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ColorPaletteGenerator:
    """
    Generate professional color palettes using seasonal color analysis
    """
    
    # Seasonal color palettes based on professional color theory
    SEASONAL_PALETTES = {
        'spring': {
            'characteristics': 'Warm, bright, clear colors',
            'description': 'Spring coloring has warm undertones with bright, clear colors',
            'best_colors': [
                {'hex': '#FF6B6B', 'name': 'Coral', 'reason': 'Warm and energizing', 'category': 'accent'},
                {'hex': '#FFD93D', 'name': 'Golden Yellow', 'reason': 'Bright and cheerful', 'category': 'accent'},
                {'hex': '#6BCB77', 'name': 'Fresh Green', 'reason': 'Natural and vibrant', 'category': 'neutral'},
                {'hex': '#4D96FF', 'name': 'Clear Blue', 'reason': 'Bright and fresh', 'category': 'primary'},
                {'hex': '#FF8C42', 'name': 'Peach', 'reason': 'Warm and flattering', 'category': 'accent'},
                {'hex': '#A8E6CF', 'name': 'Mint Green', 'reason': 'Soft and fresh', 'category': 'neutral'},
                {'hex': '#FFB6C1', 'name': 'Light Pink', 'reason': 'Delicate and warm', 'category': 'accent'},
                {'hex': '#87CEEB', 'name': 'Sky Blue', 'reason': 'Clear and bright', 'category': 'primary'},
            ],
            'neutrals': [
                {'hex': '#F5E6D3', 'name': 'Warm Beige', 'reason': 'Soft neutral base'},
                {'hex': '#D4A574', 'name': 'Camel', 'reason': 'Warm versatile neutral'},
                {'hex': '#FAEBD7', 'name': 'Antique White', 'reason': 'Soft warm white'},
                {'hex': '#8B7355', 'name': 'Taupe', 'reason': 'Warm neutral brown'},
            ],
            'avoid': ['Black', 'Dark Brown', 'Burgundy', 'Navy'],
            'metals': ['Gold', 'Rose Gold'],
        },
        'summer': {
            'characteristics': 'Cool, soft, muted colors',
            'description': 'Summer coloring has cool undertones with soft, muted colors',
            'best_colors': [
                {'hex': '#B4A7D6', 'name': 'Lavender', 'reason': 'Soft and elegant', 'category': 'primary'},
                {'hex': '#87CEEB', 'name': 'Powder Blue', 'reason': 'Cool and calming', 'category': 'primary'},
                {'hex': '#FFB6C1', 'name': 'Rose Pink', 'reason': 'Soft and romantic', 'category': 'accent'},
                {'hex': '#98D8C8', 'name': 'Seafoam', 'reason': 'Cool and refreshing', 'category': 'neutral'},
                {'hex': '#E6E6FA', 'name': 'Periwinkle', 'reason': 'Soft cool blue', 'category': 'primary'},
                {'hex': '#DDA0DD', 'name': 'Plum', 'reason': 'Muted cool purple', 'category': 'accent'},
                {'hex': '#F0E68C', 'name': 'Soft Yellow', 'reason': 'Muted warm accent', 'category': 'accent'},
                {'hex': '#D8BFD8', 'name': 'Thistle', 'reason': 'Soft cool purple', 'category': 'neutral'},
            ],
            'neutrals': [
                {'hex': '#C0C0C0', 'name': 'Silver Gray', 'reason': 'Cool elegant neutral'},
                {'hex': '#E6E6FA', 'name': 'Soft White', 'reason': 'Cool white base'},
                {'hex': '#A9A9A9', 'name': 'Cool Gray', 'reason': 'Versatile cool neutral'},
                {'hex': '#778899', 'name': 'Slate Gray', 'reason': 'Sophisticated cool gray'},
            ],
            'avoid': ['Orange', 'Bright Yellow', 'Black', 'Rust'],
            'metals': ['Silver', 'White Gold', 'Platinum'],
        },
        'autumn': {
            'characteristics': 'Warm, rich, earthy colors',
            'description': 'Autumn coloring has warm undertones with rich, earthy tones',
            'best_colors': [
                {'hex': '#8B4513', 'name': 'Saddle Brown', 'reason': 'Rich and warm', 'category': 'neutral'},
                {'hex': '#DAA520', 'name': 'Goldenrod', 'reason': 'Warm golden tone', 'category': 'accent'},
                {'hex': '#CD853F', 'name': 'Peru', 'reason': 'Warm earthy brown', 'category': 'neutral'},
                {'hex': '#556B2F', 'name': 'Olive Green', 'reason': 'Rich earthy green', 'category': 'primary'},
                {'hex': '#B8860B', 'name': 'Dark Goldenrod', 'reason': 'Deep warm gold', 'category': 'accent'},
                {'hex': '#A0522D', 'name': 'Sienna', 'reason': 'Warm reddish brown', 'category': 'neutral'},
                {'hex': '#D2691E', 'name': 'Chocolate', 'reason': 'Rich warm brown', 'category': 'primary'},
                {'hex': '#BC8F8F', 'name': 'Rosy Brown', 'reason': 'Warm muted rose', 'category': 'accent'},
            ],
            'neutrals': [
                {'hex': '#8B7355', 'name': 'Warm Taupe', 'reason': 'Earthy warm neutral'},
                {'hex': '#D2B48C', 'name': 'Tan', 'reason': 'Warm beige neutral'},
                {'hex': '#F5DEB3', 'name': 'Wheat', 'reason': 'Soft warm neutral'},
                {'hex': '#A0522D', 'name': 'Sienna', 'reason': 'Rich warm brown'},
            ],
            'avoid': ['Black', 'Bright Pink', 'Icy Blue', 'Pure White'],
            'metals': ['Gold', 'Bronze', 'Copper'],
        },
        'winter': {
            'characteristics': 'Cool, bright, clear colors',
            'description': 'Winter coloring has cool undertones with bright, clear, bold colors',
            'best_colors': [
                {'hex': '#000000', 'name': 'True Black', 'reason': 'Bold and dramatic', 'category': 'neutral'},
                {'hex': '#FFFFFF', 'name': 'Pure White', 'reason': 'Crisp and clean', 'category': 'neutral'},
                {'hex': '#FF0000', 'name': 'True Red', 'reason': 'Bold and striking', 'category': 'accent'},
                {'hex': '#0000FF', 'name': 'Royal Blue', 'reason': 'Deep cool blue', 'category': 'primary'},
                {'hex': '#FF1493', 'name': 'Hot Pink', 'reason': 'Bold cool pink', 'category': 'accent'},
                {'hex': '#8B008B', 'name': 'Dark Magenta', 'reason': 'Rich cool purple', 'category': 'primary'},
                {'hex': '#4B0082', 'name': 'Indigo', 'reason': 'Deep cool purple', 'category': 'primary'},
                {'hex': '#00CED1', 'name': 'Dark Turquoise', 'reason': 'Bright cool blue', 'category': 'accent'},
            ],
            'neutrals': [
                {'hex': '#000000', 'name': 'Black', 'reason': 'Classic cool neutral'},
                {'hex': '#FFFFFF', 'name': 'White', 'reason': 'Pure cool white'},
                {'hex': '#708090', 'name': 'Slate Gray', 'reason': 'Cool sophisticated gray'},
                {'hex': '#2F4F4F', 'name': 'Dark Slate Gray', 'reason': 'Deep cool gray'},
            ],
            'avoid': ['Orange', 'Gold', 'Beige', 'Warm Browns'],
            'metals': ['Silver', 'Platinum', 'White Gold'],
        }
    }
    
    def determine_season(
        self, 
        skin_tone_ita: float, 
        undertone: str,
        skin_lab: Dict[str, float]
    ) -> str:
        """
        Determine color season based on skin characteristics
        
        Args:
            skin_tone_ita: ITA value
            undertone: 'warm', 'cool', or 'neutral'
            skin_lab: LAB color values
        
        Returns:
            Season: 'spring', 'summer', 'autumn', or 'winter'
        """
        L = skin_lab['L']
        
        # Light vs Dark (based on L value)
        is_light = L > 60
        
        # Warm vs Cool (based on undertone)
        is_warm = undertone == 'warm'
        is_cool = undertone == 'cool'
        
        # Determine season
        if is_light and is_warm:
            season = 'spring'
        elif is_light and is_cool:
            season = 'summer'
        elif not is_light and is_warm:
            season = 'autumn'
        elif not is_light and is_cool:
            season = 'winter'
        else:  # neutral
            # Use ITA to decide
            if skin_tone_ita > 28:  # Very light
                season = 'summer'
            elif skin_tone_ita > -30:  # Light to medium
                season = 'spring'
            else:  # Dark
                season = 'autumn'
        
        logger.info(f"Determined season: {season} (ITA={skin_tone_ita:.1f}, undertone={undertone})")
        
        return season
    
    def generate_palette(
        self,
        season: str,
        skin_tone_ita: float,
        undertone: str
    ) -> Dict:
        """
        Generate personalized color palette
        
        Args:
            season: Color season
            skin_tone_ita: ITA value
            undertone: Undertone type
        
        Returns:
            Complete palette with recommendations
        """
        if season not in self.SEASONAL_PALETTES:
            logger.warning(f"Unknown season {season}, defaulting to neutral")
            season = 'summer'
        
        palette_data = self.SEASONAL_PALETTES[season]
        
        # Add styling tips for each color
        best_colors = []
        for color in palette_data['best_colors']:
            enhanced_color = color.copy()
            enhanced_color['how_to_wear'] = self._get_styling_tips(color, season)
            enhanced_color['occasions'] = self._get_occasions(color)
            best_colors.append(enhanced_color)
        
        return {
            'season': season,
            'characteristics': palette_data['characteristics'],
            'description': palette_data['description'],
            'best_colors': best_colors,
            'neutrals': palette_data['neutrals'],
            'avoid': palette_data['avoid'],
            'metals': palette_data['metals'],
            'confidence': self._calculate_palette_confidence(season, undertone)
        }
    
    def _get_styling_tips(self, color: Dict, season: str) -> str:
        """Generate styling tips for a color"""
        tips = {
            'primary': f"Perfect as a main color for dresses, suits, or statement pieces. Pair with {self.SEASONAL_PALETTES[season]['metals'][0].lower()} jewelry.",
            'accent': f"Great for accessories, scarves, or accent pieces. Use to add pops of color to neutral outfits.",
            'neutral': f"Versatile base color for everyday wear. Pairs well with all your best colors."
        }
        
        return tips.get(color.get('category', 'neutral'), "Versatile color for your wardrobe.")
    
    def _get_occasions(self, color: Dict) -> List[str]:
        """Get appropriate occasions for a color"""
        category = color.get('category', 'neutral')
        
        occasions = {
            'primary': ['formal events', 'business meetings', 'important occasions'],
            'accent': ['casual outings', 'date night', 'social events'],
            'neutral': ['everyday wear', 'work', 'versatile occasions']
        }
        
        return occasions.get(category, ['any occasion'])
    
    def _calculate_palette_confidence(self, season: str, undertone: str) -> float:
        """
        Calculate confidence in palette recommendation
        """
        # Base confidence
        confidence = 0.8
        
        # Increase if undertone matches season
        season_undertones = {
            'spring': 'warm',
            'summer': 'cool',
            'autumn': 'warm',
            'winter': 'cool'
        }
        
        if season_undertones.get(season) == undertone:
            confidence += 0.15
        
        return min(confidence, 1.0)
