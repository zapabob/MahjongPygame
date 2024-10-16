# player.py

from typing import List, Optional
from tiles import Tile
from ai_agent import AIAgent
from yaku_evaluator import YakuEvaluator
import pygame

class Player:
    def __init__(self, name: str, is_human: bool = True, ai_agent: Optional[AIAgent] = None, evaluator: Optional[YakuEvaluator] = None):
        self.name = name
        self.is_human = is_human
        self.evaluator = evaluator
        self.ai_agent = ai_agent if ai_agent else (AIAgent(self.evaluator) if self.evaluator else None)
        self.hand: List[Tile] = []
        self.discards: List[Tile] = []
        self.is_reach: bool = False
        self.has_won_previous_round: bool = False
        self.initial_hand: Optional[List[Tile]] = None
        self.initial_draw: bool = False
        self.is_closed: bool = True

        # タイル表示用の位置を管理
        self.tile_positions = []  # 各タイルの矩形領域を保持

    def choose_discard(self) -> Optional[Tile]:
        if self.is_human:
            # 人間プレイヤーはPygameのイベントで捨てる牌を選択
            # このメソッドはPygameイベントハンドリングで呼び出される
            return None
        else:
            # AIプレイヤーの場合の処理
            return self.ai_agent.choose_discard(self.hand, self.discards)

    def handle_mouse_click(self, mouse_pos) -> Optional[Tile]:
        """
        マウスクリックされた位置に対応する牌を捨てる
        """
        for idx, rect in enumerate(self.tile_positions):
            if rect.collidepoint(mouse_pos):
                chosen_tile = self.hand.pop(idx)
                self.discards.append(chosen_tile)
                return chosen_tile
        return None

    def draw_hand(self, window, font):
        """
        手牌を画面に描画し、クリック可能な矩形を設定
        """
        self.tile_positions = []
        x_start = 50
        y_start = 600  # 下部に手牌を表示
        tile_width = 50
        tile_height = 70
        spacing = 10

        for idx, tile in enumerate(self.hand):
            x = x_start + idx * (tile_width + spacing)
            y = y_start
            if tile.image:
                window.blit(tile.image, (x, y))
            else:
                # 画像がない場合は矩形とテキストで代用
                pygame.draw.rect(window, (255, 255, 255), (x, y, tile_width, tile_height))
                text_surface = font.render(tile.name, True, (0, 0, 0))
                window.blit(text_surface, (x + 5, y + 25))
            rect = pygame.Rect(x, y, tile_width, tile_height)
            self.tile_positions.append(rect)

    def draw_discards(self, window, font):
        """
        捨て牌を画面に描画
        """
        x_start = 700
        y_start = 50  # 上部に捨て牌を表示
        tile_width = 50
        tile_height = 70
        spacing = 10
        max_tiles_per_row = 10  # 1行あたりの最大捨て牌数

        discard_text = f"{self.name} の捨て牌: "
        text_surface = font.render(discard_text, True, (255, 255, 255))
        window.blit(text_surface, (x_start, y_start - 30))

        for idx, tile in enumerate(self.discards):
            row = idx // max_tiles_per_row
            col = idx % max_tiles_per_row
            x = x_start + col * (tile_width + spacing)
            y = y_start + row * (tile_height + spacing)

            if tile.image:
                window.blit(tile.image, (x, y))
            else:
                pygame.draw.rect(window, (255, 255, 255), (x, y, tile_width, tile_height))
                text_surface = font.render(tile.name, True, (0, 0, 0))
                window.blit(text_surface, (x + 5, y + 25))
