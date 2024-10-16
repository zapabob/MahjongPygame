from typing import List, Optional
from tiles import Tile, create_tiles
from yaku_evaluator import YakuEvaluator
from ai_agent import AIAgent
import random
from player import Player
import pygame
import logging

# ログの設定
logging.basicConfig(filename='game_error.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

class MahjongGame:
    def __init__(self, num_players: int = 4):
        if not (2 <= num_players <= 4):
            raise ValueError("プレイヤー数は2人から4人までです。")
        self.num_players = num_players
        self.players = [
            Player(
                f"Player {i+1}", 
                is_human=(i == 0), 
                evaluator=YakuEvaluator(is_dealer=(i == 0))
            ) for i in range(self.num_players)
        ]
        self.tiles = create_tiles()
        for tile in self.tiles:
            tile.load_image()  # タイル画像をロード
        self.deal_tiles()
        self.current_player_index = self.determine_first_player()
        self.game_over = False
        self.state = 'draw'  # 'draw', 'discard'

    def deal_tiles(self):
        """
        各プレイヤーに13枚ずつ牌を配ります（親には14枚）。
        """
        random.shuffle(self.tiles)
        for i, player in enumerate(self.players):
            start = i * 13
            end = start + 13
            player.hand = self.tiles[start:end]
        # 親（Player 1）に14枚目を配る
        self.players[0].hand.append(self.tiles[self.num_players * 13])

    def determine_first_player(self) -> int:
        """
        初めのプレイヤーを決定します。ここでは親を指定したプレイヤーに設定。
        """
        return 0  # 親は常にPlayer 1とする

    def draw_tile(self, player: Player):
        """
        山から一枚牌を引く
        """
        if not self.tiles:
            print("牌が尽きました。")
            self.game_over = True
            return
        drawn_tile = self.tiles.pop()
        player.hand.append(drawn_tile)
        print(f"{player.name} が引いた牌: {drawn_tile.name}")
        if len(player.hand) > 14:
            player.hand = player.hand[:14]  # 手牌が14枚を超えないように制限
    def play_game_pygame(self, window, font):
        clock = pygame.time.Clock()
        running = True

        while running and not self.game_over:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        print("MOUSEBUTTONDOWN event detected")
                        if self.state == 'discard':
                            current_player = self.players[self.current_player_index]
                            if current_player.is_human:
                                mouse_pos = pygame.mouse.get_pos()
                                print(f"{current_player.name} の捨て牌処理を開始します。クリック位置: {mouse_pos}")
                                discarded_tile = current_player.handle_mouse_click(mouse_pos)
                                if discarded_tile:
                                    print(f"{current_player.name} が捨てました: {discarded_tile.name}")
                                    yaku_list, han, fu = current_player.evaluator.evaluate_hand(
                                        current_player.hand, current_player.is_closed, True
                                    )
                                    print(f"{current_player.name} の役: {yaku_list}, 翻数: {han}, 符数: {fu}")
                                    if yaku_list:
                                        self.end_game(winner=current_player)
                                        continue
                                    self.current_player_index = (self.current_player_index + 1) % self.num_players
                                    self.state = 'draw'

                # AIのターンを処理
                if not self.game_over and self.state == 'draw':
                    current_player = self.players[self.current_player_index]
                    if not current_player.is_human:
                        print(f"{current_player.name} のAIターンを開始します。")
                        self.draw_tile(current_player)
                        discarded_tile = current_player.choose_discard()
                        if discarded_tile:
                            print(f"{current_player.name} が捨てました: {discarded_tile.name}")
                            yaku_list, han, fu = current_player.evaluator.evaluate_hand(
                                current_player.hand, current_player.is_closed, False
                            )
                            print(f"{current_player.name} の役: {yaku_list}, 翻数: {han}, 符数: {fu}")
                            if yaku_list:
                                self.end_game(winner=current_player)
                                continue
                            self.current_player_index = (self.current_player_index + 1) % self.num_players
                            self.state = 'draw'
                    else:
                        # 人間プレイヤーのターン
                        print(f"{current_player.name} の人間ターンを開始します。")
                        self.draw_tile(current_player)
                        self.state = 'discard'

                # 描画処理
                window.fill((0, 128, 0))  # 背景を緑色に設定

                self.draw_game_state(window, font)

                pygame.display.flip()
                clock.tick(30)

            except Exception as e:
                logging.error("An error occurred", exc_info=True)
                running = False

        # ゲーム終了時のメッセージ表示
        if self.game_over:
            self.display_end_message(window, font)

        pygame.quit()

    def draw_game_state(self, window, font):
        """
        ゲームの現在の状態を描画します。
        """
        # 各プレイヤーの捨て牌を描画
        for player in self.players:
            player.draw_discards(window, font)

        # 各プレイヤーの手牌を描画
        for player in self.players:
            player.draw_hand(window, font)

    def display_end_message(self, window, font):
        """
        ゲーム終了時のメッセージを描画します。
        """
        end_text = "ゲーム終了！"
        for player in self.players:
            yaku_list, han, fu = player.evaluator.evaluate_hand(player.hand, player.is_closed, True)
            if yaku_list:
                end_text += f" {player.name} が和了しました！"
                break
        else:
            end_text += " 流局となりました。"

        end_surface = font.render(end_text, True, (255, 215, 0))
        window.blit(end_surface, (50, 750))

    def end_game(self, winner: Player):
        """
        ゲームを終了し、勝者を設定します。
        """
        print(f"{winner.name} が和了しました！")
        self.game_over = True
