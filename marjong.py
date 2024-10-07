import random
from collections import Counter
import itertools
import tkinter as tk
from tkinter import messagebox
import socket
import threading
import unittest
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize

# 牌の種類を定義
SUITS = ['萬', '索', '筒']
NUMBERS = list(range(1, 10))
HONORS = ['東', '南', '西', '北', '白', '發', '中']

class Tile:
    def __init__(self, suit, value):
        self.suit = suit  # '萬', '索', '筒', None for honors
        self.value = value  # 数字1-9または文字
    
    def __repr__(self):
        return f"{self.value}{self.suit}" if self.suit in SUITS else f"{self.value}"
    
    def __str__(self):
        return self.__repr__()
    
    def __eq__(self, other):
        return self.suit == other.suit and self.value == other.value
    
    def __hash__(self):
        return hash((self.suit, self.value))

class Yaku:
    def __init__(self, name, han, description):
        self.name = name
        self.han = han  # 翻数
        self.description = description

    def __repr__(self):
        return f"{self.name} ({self.han}翻): {self.description}"

# 補助関数
def extract_melds(hand):
    # メルド抽出ロジックの実装（簡略化）
    melds = []
    sorted_hand = sorted(hand, key=lambda x: (x.suit if x.suit else '', x.value))
    temp = []
    for tile in sorted_hand:
        if not temp:
            temp.append(tile)
        elif tile.suit == temp[-1].suit and tile.value == temp[-1].value + 1:
            temp.append(tile)
        else:
            if len(temp) >= 3:
                melds.append(temp.copy())
            temp = [tile]
    if len(temp) >= 3:
        melds.append(temp.copy())
    return melds
def is_sequence(meld):
    if len(meld) != 3:
        return False
    suits = [tile.suit for tile in meld]
    values = [tile.value for tile in meld]
    return len(set(suits)) == 1 and values == list(range(values[0], values[0] + 3))

def is_triplet(meld):
    return len(meld) == 3 and all(tile.value == meld[0].value and tile.suit == meld[0].suit for tile in meld)

# 各種役判定関数
def is_riichi(player):
    return player.reached

def is_dora(hand, dora_tiles):
    count = 0
    for tile in hand:
        if tile in dora_tiles:
            count += 1
    return count

def is_chitoitsu(hand):
    counts = Counter(str(tile) for tile in hand)
    return len(counts) == 7 and all(count == 2 for count in counts.values())

def is_sanankou(hand):
    counts = Counter(str(tile) for tile in hand)
    triplets = [tile for tile, count in counts.items() if count >= 3]
    return len(triplets) >= 3

def is_toitoi(hand):
    counts = Counter(str(tile) for tile in hand)
    return all(count >= 2 for count in counts.values())

def is_ryanpeikou(hand):
    # 二盃口の判定（同じ順子が2組ある）
    if is_chitoitsu(hand):  # 七対子と両立しないため
        return False
    melds = extract_melds(hand)
    sequences = [tuple(sorted([tile.value for tile in meld])) for meld in melds if is_sequence(meld)]
    counts = Counter(sequences)
    return any(count >= 2 for count in counts.values())

def is_kokushi_musou(hand):
    kokushi_tiles = {"1m", "9m", "1p", "9p", "1s", "9s", "東", "南", "西", "北", "白", "發", "中"}
    unique_tiles = set(str(tile) for tile in hand)
    return unique_tiles.issuperset(kokushi_tiles) and len(unique_tiles) == 13

def is_pinfu(hand, winning_tile):
    # ピンフの判定（簡略化）
    melds = extract_melds(hand)
    if len(melds) * 3 != 14:
        return False
    if not all(is_sequence(m) for m in melds[:-1]):
        return False
    pair = melds[-1]
    if not (pair[0].suit and pair[0].suit in SUITS and pair[0].value not in [1,9]):
        return False
    # 待ちが両面待ちかどうかを判定するロジックを実装
    if len(melds) < 1:
        return False
    last_meld = melds[-1]
    if len(last_meld) != 2:
        return False
    if (last_meld[0].value + 1 == last_meld[1].value) or (last_meld[0].value - 1 == last_meld[1].value):
        return True
    return False
    return True

def is_sangenpai_triplet(hand):
    counts = Counter(str(tile) for tile in hand)
    return any(tile in ['白', '發', '中'] and count >= 3 for tile, count in counts.items())

def is_tanyao(hand):
    # タンヤオの条件をチェックするロジックを実装
    # すべての牌が2-8の数牌であるかをチェック
    return all(2 <= tile.number <= 8 and tile.suit in ['man', 'sou', 'pin'] for tile in hand)

def is_iipeekou(hand):
    # 面子のリストを取得
    melds = extract_melds(hand)
    # 順子のみを抽出
    shuntsu = [m for m in melds if is_sequence(m)]
    # 重複する順子をカウント
    duplicates = len(shuntsu) - len(set(tuple(s) for s in shuntsu))
    return duplicates >= 1

def is_sunankou(hand, winning_tile):
    # 四暗刻の判定ロジックを実装
    counts = Counter(str(tile) for tile in hand)
    return all(tile in ['白', '發', '中'] and count == 3 for tile, count in counts.items())

def evaluate_yakus(hand, winning_tile, dora_tiles, player):
    yaku_list = []

    # タンヤオ
    if is_tanyao(hand, winning_tile):
        yaku_list.append(Yaku("タンヤオ", 2, "数牌の2から8のみで構成"))  # 符を修正

    # ピンフ
    if is_pinfu(hand, winning_tile):
        yaku_list.append(Yaku("ピンフ", 1, "門前で役牌の対子を持たない"))

    # 七対子
    if is_chitoitsu(hand, winning_tile):
        yaku_list.append(Yaku("七対子", 2, "7つの対子で構成"))

    # サンアンコウ
    if is_sanankou(hand, winning_tile):
        yaku_list.append(Yaku("サンアンコウ", 2, "3つの暗刻を持つ"))

    # 国士無双
    if is_kokushi_musou(hand, winning_tile):
        yaku_list.append(Yaku("国士無双", 13, "13種類の国士牌とそのいずれかをもう1枚"))

    # リーチ
    if is_riichi(player, winning_tile):
        yaku_list.append(Yaku("リーチ", 1, "テンパイ状態で宣言"))

    # ドラ
    dora_count = is_dora(hand, dora_tiles)
    if dora_count > 0:
        yaku_list.append(Yaku(f"ドラ x{dora_count}", dora_count, "ドラ表示牌に対応する牌"))

    # 対々和
    if is_toitoi(hand, winning_tile):
        yaku_list.append(Yaku("対々和", 2, "全ての面子が刻子"))
    
    # 一盃口
    if is_iipeekou(hand, winning_tile):
        yaku_list.append(Yaku("一盃口", 2, "同じ順子が2組ある"))
    
    # 二盃口（包括）
    if is_ryanpeikou(hand, winning_tile):
        yaku_list.append(Yaku("二盃口", 3, "同じ順子が3組ある"))

    # 三元牌刻子
    if is_sangenpai_triplet(hand, winning_tile):
        yaku_list.append(Yaku("三元牌刻子", 2, "三元牌の刻子を持つ"))  # 符を修正
    
    # 三暗刻
    if is_sanankou(hand, winning_tile):
        yaku_list.append(Yaku("三暗刻", 2, "3つの暗刻を持つ"))
    
    # 四暗刻
    if is_sunankou(hand, winning_tile):
        yaku_list.append(Yaku("四暗刻", 13, "4つの暗刻を持つ"))
    
    # 緑一色
    if is_ryuiisou(hand, winning_tile):
        yaku_list.append(Yaku("緑一色", 6, "全ての牌が緑一色"))  # 符を修正
    
    # 清一色
    if is_tinriisou(hand, winning_tile):
        yaku_list.append(Yaku("清一色", 6, "全ての牌が清一色"))  # 符を修正
    
    # 混一色
    if is_konisou(hand, winning_tile):
        yaku_list.append(Yaku("混一色", 5, "全ての牌が混一色"))  # 符を修正
    
    # 小三元
    if is_shosangen(hand, winning_tile):
        yaku_list.append(Yaku("小三元", 2, "全ての牌が小三元"))
    
    # 小四喜
    if is_sunankou(hand, winning_tile):
        yaku_list.append(Yaku("四暗刻", 13, "全ての牌が四暗刻"))
    
    # 大三元
    if is_daisangen(hand, winning_tile):
        yaku_list.append(Yaku("大三元", 13, "全ての牌が大三元"))
    
    # 大四喜
    if is_daisushii(hand, winning_tile):
        yaku_list.append(Yaku("大四喜", 13, "全ての牌が大四喜"))
    
    # 字一色
    if is_jihaiisou(hand, winning_tile):
        yaku_list.append(Yaku("字一色", 6, "全ての牌が字一色"))  # 符を修正
    
    # 清老頭
    if is_tinroutou(hand, winning_tile):
        yaku_list.append(Yaku("清老頭", 2, "全ての牌が清老頭"))
    
    # 小四喜
    if is_shousushi(hand, winning_tile):
        yaku_list.append(Yaku("小四喜", 13, "三種の風牌が刻子で、残りの一種が雀頭"))
    
    # 大四喜
    if is_daisuishii(hand, winning_tile):
        yaku_list.append(Yaku("大四喜", 13, "全ての牌が大四喜"))

    return yaku_list

def is_jihaiisou(hand, winning_tile):
    # 字一色の判定ロジックを実装
    return all(tile.suit is None for tile in hand)  # すべての牌が字牌であるかをチェック

def is_tanyao(hand, winning_tile):
    # タンヤオの判定ロジックを実装
    return all(2 <= tile.number <= 8 and tile.suit in ['man', 'sou', 'pin'] for tile in hand)

def is_pinfu(hand, winning_tile):
    # ピンフの判定ロジックを実装
    melds = extract_melds(hand)
    if len(melds) * 3 != 14:
        return False
    if not all(is_sequence(m) for m in melds[:-1]):
        return False
    pair = melds[-1]
    return pair[0].suit in SUITS and pair[0].value not in [1, 9]

def is_chitoitsu(hand, winning_tile):
    # 七対子の判定ロジックを実装
    counts = Counter(str(tile) for tile in hand)
    return len(counts) == 7 and all(count == 2 for count in counts.values())

def is_sanankou(hand, winning_tile):
    # 三暗刻の判定ロジックを実装
    counts = Counter(str(tile) for tile in hand)
    return sum(count >= 3 for count in counts.values()) == 3

def is_kokushi_musou(hand, winning_tile):
    # 国士無双の判定ロジックを実装
    kokushi_tiles = ['1萬', '9萬', '1索', '9索', '1筒', '9筒', '東', '南', '西', '北', '白', '發', '中']
    unique_tiles = set(str(tile) for tile in hand)
    return unique_tiles.issuperset(kokushi_tiles) and len(unique_tiles) == 13

def is_riichi(player, winning_tile):
    # リーチの判定ロジックを実装
    return player.ready and winning_tile in player.hand

def is_dora(hand, dora_tiles):
    # ドラの判定ロジックを実装
    return sum(1 for tile in hand if tile in dora_tiles)

def is_toitoi(hand, winning_tile):
    # 対々和の判定ロジックを実装
    counts = Counter(str(tile) for tile in hand)
    return all(count == 3 or count == 2 for count in counts.values())

def is_iipeekou(hand, winning_tile):
    # 一盃口の判定ロジックを実装
    melds = extract_melds(hand)
    shuntsu = [m for m in melds if is_sequence(m)]
    duplicates = len(shuntsu) - len(set(tuple(s) for s in shuntsu))
    return duplicates >= 1

def is_sangenpai_triplet(hand, winning_tile):
    # 三元牌刻子の判定ロジックを実装
    counts = Counter(str(tile) for tile in hand)
    return any(tile in ['白', '發', '中'] and count >= 3 for tile, count in counts.items())

def is_sunankou(hand, winning_tile):
    # 四暗刻の判定ロジックを実装
    counts = Counter(str(tile) for tile in hand)
    return sum(count >= 4 for count in counts.values()) == 1

def is_ryuiisou(hand, winning_tile):
    # 緑一色の判定ロジックを実装
    return all(tile.suit == 'sou' and tile.value in [2, 3, 4, 6, 8] for tile in hand)

def is_tinriisou(hand, winning_tile):
    # 清一色の判定ロジックを実装
    return all(tile.suit == hand[0].suit for tile in hand)

def is_konisou(hand, winning_tile):
    # 混一色の判定ロジックを実装
    return all(tile.suit in ['man', 'sou', 'pin'] or tile.suit is None for tile in hand)

def is_shosangen(hand, winning_tile):
    # 小三元の判定ロジックを実装
    counts = Counter(str(tile) for tile in hand)
    return sum(counts.get(tile, 0) for tile in ['白', '發', '中']) == 2

def is_tinroutou(hand, winning_tile):
    # 清老頭の判定ロジックを実装
    return all(tile.value in [1, 9] for tile in hand + [winning_tile])

def is_shosuishii(hand, winning_tile):
    # 小四喜の判定ロジックを実装
    counts = Counter(str(tile) for tile in hand + [winning_tile])
    return sum(counts.get(tile, 0) >= 2 for tile in ['東', '南', '西', '北']) == 3

def is_daisuishii(hand, winning_tile):
    # 大四喜の判定ロジックを実装
    counts = Counter(str(tile) for tile in hand + [winning_tile])
    return all(counts.get(tile, 0) >= 3 for tile in ['東', '南', '西', '北'])

def is_daisushii(hand, winning_tile):
    winds = ['東', '南', '西', '北']
    return all(hand.count(wind) >= 3 for wind in winds)

def is_shousushi(hand, winning_tile):
    wind_tiles = ['東', '南', '西', '北']
    wind_counts = [hand.count(tile) for tile in wind_tiles]
    return sum(count >= 3 for count in wind_counts) == 3 and any(count >= 2 for count in wind_counts)
def is_daisangen(hand, winning_tile):
    return all(tile in ['白', '發', '中'] and count == 3 for tile, count in Counter(str(tile) for tile in hand).items())

def get_next_dora(tile):
    if tile.suit in SUITS:
        if tile.value < 9:
            return Tile(tile.suit, tile.value + 1)
        else:
            return Tile(tile.suit, 1)
    else:
        # 字牌のドラは順序が決まっている
        order = ['東', '南', '西', '北', '白', '發', '中']
        idx = order.index(tile.value)
        return Tile(None, order[(idx + 1) % len(order)])

class Wall:
    def __init__(self):
        self.tiles = self.initialize_wall()
        self.dora_indicators = []
        self.open_dora_indicators = []  # ドラ表示牌を公開

    def initialize_wall(self):
        tiles = []
        # 数牌
        for suit in SUITS:
            for num in NUMBERS:
                for _ in range(4):
                    tiles.append(Tile(suit, num))
        # 字牌
        for honor in HONORS:
            for _ in range(4):
                tiles.append(Tile(None, honor))
        random.shuffle(tiles)
        # ドラ表示牌を1枚引く
        self.dora_indicators.append(self.draw())
        self.open_dora_indicators.append(self.draw())  # ドラ表示牌を公開
        return tiles

    def draw(self):
        return self.tiles.pop() if self.tiles else None

    def get_dora(self):
        dora_tiles = []
        for indicator in self.open_dora_indicators:
            dora = get_next_dora(indicator)
            dora_tiles.append(dora)
        return dora_tiles

def calculate_fu(hand, winning_tile, yaku_list, tsumo=False):
    # 簡略化された符計算
    fu = 30  # 基本符を30に変更

    melds = extract_melds(hand)
    counts = Counter(str(tile) for tile in hand)

    # 面子ごとの符計算
    for meld in melds:
        if len(meld) == 3:
            if is_sequence(meld):
                continue  # 順子は符加算なし
            elif is_triplet(meld):
                if is_open(meld, hand):
                    fu += 2  # 明刻
                else:
                    fu += 4  # 暗刻

    # 対子
    for tile, count in counts.items():
        if count == 2:
            if tile in ['東', '南', '西', '北', '白', '發', '中']:
                fu += 2  # 役牌の対子
            else:
                fu += 0  # 役牌以外の対子

    # リーチ
    if any(yaku.name == "リーチ" for yaku in yaku_list):
        fu += 10  # リーチ符

    # ツモ
    if tsumo:
        fu += 2  # ツモ符

    # 特定の待ちの場合
    # 待ちの種類によって符を加算する
    # ここでは簡略化して、待ちの種類に応じて符を加算する
    fu += 4 if is_special_wait(hand, winning_tile) else 2  # 特定の待ちの場合は4符加算、その他の場合は2符加算

    # 切り上げ
    fu = ((fu + 9) // 10) * 10
    return fu

def is_open(meld, hand):
    # メルドが開かれているか（他家からの切り牌で完成しているか）を判定
    # 他家からの切り牌が含まれている場合はTrueを返す
    return len(meld) == 3 and any(tile in hand for tile in meld) and meld[0] != meld[1] and meld[1] != meld[2]

def calculate_score(yaku_list, fu, dealer=False, tsumo=False):
    total_han = sum(yaku.han for yaku in yaku_list)

    # 簡略化のため、翻数と符に基づく基本的な点数計算
    # 実際の日本麻雀の点数計算を簡略化
    if total_han >= 13:
        return "役満"
    elif total_han >= 11:
        return "三倍満"
    elif total_han >= 8:
        return "倍満"
    elif total_han >= 6:
        return "跳満"
    elif total_han >= 5:
        return "満貫"
    elif total_han >= 4:
        base = fu * (2 ** (total_han + 2))
    else:
        base = fu * (2 ** (total_han + 2))  # ここでtotal_hanが4未満の場合も同じ計算を行う
    # 簡略化された計算
    score = base
    if dealer:
        score = int(score * 1.5)
    else:
        score = int(score)  # ディーラーでない場合は整数に変換
    return score

class MahjongGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("麻雀ゲーム")
        self.setGeometry(100, 100, 1200, 800)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)
        self.game = Game([Player(f"プレイヤー{i+1}") for i in range(4)])
        self.initUI()

    def initUI(self):
        # 山札表示
        self.wall_label = QLabel("残り牌: 136")
        self.layout.addWidget(self.wall_label)

        # プレイヤーの手牌表示
        self.player_hands = []
        for i in range(4):
            hand_layout = QHBoxLayout()
            self.player_hands.append(hand_layout)
            self.layout.addLayout(hand_layout)

        # 捨て牌表示
        discard_layout = QGridLayout()
        self.layout.addLayout(discard_layout)

        # 操作ボタン
        button_layout = QHBoxLayout()
        self.pon_button = QPushButton("ポン")
        self.chi_button = QPushButton("チー")
        self.kan_button = QPushButton("カン")
        self.riichi_button = QPushButton("リーチ")
        self.tsumo_button = QPushButton("ツモ")
        self.ron_button = QPushButton("ロン")
        button_layout.addWidget(self.pon_button)
        button_layout.addWidget(self.chi_button)
        button_layout.addWidget(self.kan_button)
        button_layout.addWidget(self.riichi_button)
        button_layout.addWidget(self.tsumo_button)
        button_layout.addWidget(self.ron_button)
        self.layout.addLayout(button_layout)

        self.update_display()

    def update_display(self):
        # 山札の更新
        self.wall_label.setText(f"残り牌: {len(self.game.wall.tiles)}")

        # プレイヤーの手牌更新
        for i, player in enumerate(self.game.players):
            self.update_player_hand(i, player.hand)

        # 捨て牌の更新
        discard_layout = self.layout.itemAt(3).layout()  # 捨て牌のレイアウトを取得
        for i in reversed(range(discard_layout.count())): 
            discard_layout.itemAt(i).widget().setParent(None)  # 既存の捨て牌をクリア
        for tile in self.game.discard_pile:  # 捨て牌のリストを取得
            tile_button = QPushButton(str(tile))
            tile_button.setFixedSize(40, 60)
            discard_layout.addWidget(tile_button)  # 新しい捨て牌を追加

    def update_player_hand(self, player_index, hand):
        layout = self.player_hands[player_index]
        for i in reversed(range(layout.count())): 
            layout.itemAt(i).widget().setParent(None)
        for tile in hand:
            tile_button = QPushButton(str(tile))
            tile_button.setFixedSize(40, 60)
            layout.addWidget(tile_button)

    def tile_clicked(self, tile):
        # タイルがクリックされたときの処理
        print(f"{tile} がクリックされました")
        # クリックされたタイルを捨て牌として選択する処理を追加
        self.game.discard_pile.append(tile)  # タイルを捨て牌に追加
        self.update_display()  # 表示を更新

def is_special_wait(hand, winning_tile):
    # 特定の待ちの判定ロジックを実装
    # 例: 1枚の牌を待っている場合の判定
    counts = Counter(str(tile) for tile in hand)
    if len(counts) == 1:
        return True  # 同じ牌が揃っている場合は特定の待ち
    if len(counts) == 2 and any(count == 2 for count in counts.values()):
        return True  # 2種類の牌があり、1つが対子の場合
    if len(counts) == 2 and any(count == 1 for count in counts.values()):
        return True  # 2種類の牌があり、1つが単独の場合
    return False  # 特定の待ちではない

# Playerクラスを定義
class Player:
    def __init__(self, name):
        self.name = name

# Gameクラスを定義
class Game:
    def __init__(self, players):
        self.players = players
        self.central_widget.setLayout(self.layout)
        self.game = Game([Player(f"プレイヤー{i+1}") for i in range(4)])
        self.initUI()

class MahjongAI:
    def __init__(self):
        self.dangerous_tiles = set()
        self.safe_tiles = set()
        
    def update_dangerous_tiles(self, game_state):
        # ゲームの状態から危険な牌を更新
        self.dangerous_tiles.clear()  # 既存の危険な牌をクリア
        for player in game_state.players:
            if player.is_ready:  # リーチ宣言をしているプレイヤー
                self.dangerous_tiles.add(player.winning_tile)  # 勝ち牌を危険な牌として追加
            # 鳴きの情報を使用して危険な牌を追加
            for meld in player.melds:
                self.dangerous_tiles.update(meld.tiles)  # 鳴き牌を危険な牌として追加
    def is_safe_to_discard(self, tile):
        return tile not in self.dangerous_tiles  # 単純化された安全な牌の判定
        
    def should_play_defensive(self, game_state):
        # 場況に応じて守りに入るべきかを判断
        return any(player.is_ready for player in game_state.players)  # リーチしているプレイヤーがいる場合は守りに入る
    def choose_discard_tile(self, hand, game_state):
        if self.should_play_defensive(game_state):
            # 安全な牌を優先して切る
            for tile in hand:
                if self.is_safe_to_discard(tile):
                    return tile
        
        # 通常の切り牌選択ロジック
        return self.normal_discard_strategy(hand)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MahjongGUI()
    window.show()
    sys.exit(app.exec_())