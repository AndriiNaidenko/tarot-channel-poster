import json
import random
from typing import List, Dict
import os

class TarotDeck:
    def __init__(self, cards_file: str = "data/tarot_cards.json"):
        # Get the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        full_path = os.path.join(project_root, cards_file)
        
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Full Tarot deck: 22 Major Arcana + 56 Minor Arcana = 78 cards
        self.cards = data['major_arcana'] + data.get('minor_arcana', [])
    
    def shuffle(self):
        random.shuffle(self.cards)
    
    def draw_card(self) -> Dict:
        """Draw one card"""
        self.shuffle()
        card = self.cards[0].copy()
        card['is_reversed'] = random.choice([True, False])
        return card
    
    def draw_cards(self, count: int) -> List[Dict]:
        """Draw N cards"""
        self.shuffle()
        cards = []
        for i in range(min(count, len(self.cards))):
            card = self.cards[i].copy()
            card['is_reversed'] = random.choice([True, False])
            card['position'] = i + 1
            cards.append(card)
        return cards
    
    def get_card_display(self, card: Dict) -> str:
        """Format card for display"""
        name = card['name_ru']
        reversed_text = " (Перевёрнутая)" if card.get('is_reversed') else ""
        return f"{name}{reversed_text}"
