# ai_agent.py

from typing import List, Optional
from tiles import Tile
from collections import defaultdict
import random
from yaku_evaluator import YakuEvaluator

class AIAgent:
    def __init__(self, evaluator: YakuEvaluator):
        self.evaluator = evaluator

    def choose_discard(self, hand: List[Tile], discards: List[Tile]) -> Optional[Tile]:
        """
        AIが捨てる牌を選択します。簡易的な戦略として、最も不要な牌を捨てます。
        """
        try:
            # 各牌の不要度を評価
            tile_scores = defaultdict(int)
            for tile in hand:
                score = self.evaluate_tile(hand, tile)
                tile_scores[tile.name] = score

            # 最も不要な牌を選択
            sorted_tiles = sorted(hand, key=lambda x: tile_scores[x.name], reverse=True)
            chosen_tile = sorted_tiles[0]
            hand.remove(chosen_tile)
            discards.append(chosen_tile)
            return chosen_tile
        except Exception as e:
            print(f"AIが牌を選択中にエラーが発生しました: {e}")
            return None

    def evaluate_tile(self, hand: List[Tile], tile: Tile) -> int:
        """
        各牌の不要度を評価するためのスコアを返します。スコアが高いほど不要とみなします。
        """
        # 簡易的なスコアリング: 字牌は高スコア、端牌も高スコア、順子に参加していない牌は高スコア
        if tile.is_honor() or tile.is_terminal():
            return 10
        else:
            # 順子に参加できるか評価
            previous_tile = Tile(name=f"{tile.number -1}{tile.suit}") if tile.number >1 else None
            next_tile = Tile(name=f"{tile.number +1}{tile.suit}") if tile.number <9 else None
            if previous_tile and previous_tile in hand:
                return 5
            if next_tile and next_tile in hand:
                return 5
            return 8  # どちらでもない場合

    def has_waited_tile_in_discards(self, waiting_tiles: List[Tile], discards: List[Tile]) -> bool:
        """
        捨て牌に待ち牌が含まれているか確認します。
        """
        for tile in discards:
            if tile.name in [wt.name for wt in waiting_tiles]:
                return True
        return False
