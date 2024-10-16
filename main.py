# main.py

import pygame
from game import MahjongGame
import logging

# ログの設定
logging.basicConfig(filename='game_error.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

def main():
    # Pygameの初期化
    pygame.init()

    # ウィンドウの設定
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("日本麻雀ゲーム")

    # フォントの設定
    FONT = pygame.font.SysFont(None, 24)

    # ゲームの初期化
    game = MahjongGame()

    try:
        # ゲームをPygameでプレイ
        game.play_game_pygame(window, FONT)
    except Exception as e:
        logging.error("An error occurred", exc_info=True)
        pygame.quit()

if __name__ == "__main__":
    main()
