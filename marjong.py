import random
from collections import Counter
import itertools
import sys
import socket
import threading
import unittest
import h5py
import numpy as np
import math
import optuna
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from typing import List, Dict, Tuple, Any, Optional
from optuna.trial import Trial
from enum import Enum
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize
from torch.nn import TransformerEncoder, TransformerEncoderLayer
from torch.nn.utils.rnn import pad_sequence

# 定数の定義
SUITS = ['萬', '索', '筒']
NUMBERS = list(range(1, 10))
HONORS = ['東', '南', '西', '北', '白', '發', '中']

class Tile:
    def __init__(self, suit: Optional[str], value: str):
        self.suit = suit  # '萬', '索', '筒', None for honors
        self.value = value  # 数字1-9または文字
    
    def __repr__(self) -> str:
        return f"{self.value}{self.suit}" if self.suit in SUITS else f"{self.value}"
    
    def __str__(self):
        return self.__repr__()
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tile):
            return NotImplemented
        return self.suit == other.suit and self.value == other.value
    
    def __hash__(self) -> int:
        return hash((self.suit, self.value))

class Yaku:
    def __init__(self, name: str, han: int, description: str, is_yakuman: bool = False):
        self.name = name
        self.han = han  # 翻数
        self.description = description
        self.is_yakuman = is_yakuman

    def __repr__(self) -> str:
        return f"{self.name} ({self.han}翻): {self.description}"

# 補助関数
def extract_melds(hand: List[Tile]) -> List[List[Tile]]:
    """手牌から面子を抽出する"""
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

def is_sequence(meld: List[Tile]) -> bool:
    """面子が順子かどうかを判定する"""
    if len(meld) != 3:
        return False
    suits = [tile.suit for tile in meld]
    values = [tile.value for tile in meld]
    return len(set(suits)) == 1 and values == list(range(min(values), min(values) + 3))

def is_triplet(meld: List[Tile]) -> bool:
    """面子が刻子かどうかを判定する"""
    return len(meld) == 3 and all(tile.value == meld[0].value and tile.suit == meld[0].suit for tile in meld)

# 各種役判定関数
def is_riichi(player):
    return player.reached

def is_dora(hand, dora_tiles):
    return sum(tile in dora_tiles for tile in hand)

def is_chitoitsu(hand):
    counts = Counter(str(tile) for tile in hand)
    return len(counts) == 7 and all(count == 2 for count in counts.values())

def is_sanankou(hand):
    counts = Counter(str(tile) for tile in hand)
    return sum(count >= 3 for count in counts.values()) == 3

def is_toitoi(hand):
    counts = Counter(str(tile) for tile in hand)
    return all(count >= 2 for count in counts.values())

def is_ryanpeikou(hand):
    if is_chitoitsu(hand):
        return False
    melds = extract_melds(hand)
    sequences = [tuple(sorted([tile.value for tile in meld])) for meld in melds if is_sequence(meld)]
    counts = Counter(sequences)
    return sum(count == 2 for count in counts.values()) == 2

def is_kokushi_musou(hand):
    kokushi_tiles = {"1m", "9m", "1p", "9p", "1s", "9s", "東", "南", "西", "北", "白", "發", "中"}
    unique_tiles = set(str(tile) for tile in hand)
    return unique_tiles.issuperset(kokushi_tiles) and len(unique_tiles) == 13

def is_pinfu(hand, winning_tile):
    melds = extract_melds(hand)
    if len(melds) * 3 != 14:
        return False
    if not all(is_sequence(m) for m in melds[:-1]):
        return False
    pair = melds[-1]
    return pair[0].suit in SUITS and pair[0].value not in [1, 9]

def is_yakuhai(hand, player_wind, round_wind):
    counts = Counter(str(tile) for tile in hand)
    return any(counts[tile] >= 3 for tile in ['白', '發', '中', player_wind, round_wind])

def is_tanyao(hand):
    return all(2 <= tile.value <= 8 and tile.suit in SUITS for tile in hand)

def is_iipeikou(hand):
    melds = extract_melds(hand)
    shuntsu = [m for m in melds if is_sequence(m)]
    duplicates = len(shuntsu) - len(set(tuple(s) for s in shuntsu))
    return duplicates == 1

def is_sanshoku_doujun(hand):
    melds = extract_melds(hand)
    sequences = [tuple(tile.value for tile in meld) for meld in melds if is_sequence(meld)]
    return any(all((v, 'm') in sequences and (v, 'p') in sequences and (v, 's') in sequences for v in range(1, 8)))

def is_ittsu(hand):
    melds = extract_melds(hand)
    sequences = [tuple(tile.value for tile in meld) for meld in melds if is_sequence(meld)]
    return any(all((1, 2, 3) in sequences and (4, 5, 6) in sequences and (7, 8, 9) in sequences for suit in SUITS))

def is_chanta(hand):
    melds = extract_melds(hand)
    return all(any(tile.value in [1, 9] or tile.suit is None for tile in meld) for meld in melds)

def is_honroutou(hand):
    return all(tile.value in [1, 9] or tile.suit is None for tile in hand)

def is_shousangen(hand):
    counts = Counter(str(tile) for tile in hand)
    return sum(counts[tile] >= 3 for tile in ['白', '發', '中']) == 2 and any(counts[tile] == 2 for tile in ['白', '發', '中'])

def is_honitsu(hand):
    suits = set(tile.suit for tile in hand if tile.suit in SUITS)
    return len(suits) == 1 and any(tile.suit is None for tile in hand)

def is_junchan(hand):
    melds = extract_melds(hand)
    return all(any(tile.value in [1, 9] for tile in meld) for meld in melds) and all(tile.suit in SUITS for tile in hand)

def is_chinitsu(hand):
    return len(set(tile.suit for tile in hand)) == 1 and all(tile.suit in SUITS for tile in hand)

def is_suuankou(hand, winning_tile):
    counts = Counter(str(tile) for tile in hand)
    triplets = [tile for tile, count in counts.items() if count >= 3]
    pairs = [tile for tile, count in counts.items() if count == 2]
    return len(triplets) == 4 and len(pairs) == 1 and str(winning_tile) in triplets

def is_daisangen(hand):
    counts = Counter(str(tile) for tile in hand)
    return all(counts[tile] >= 3 for tile in ['白', '發', '中'])

def is_shousuushii(hand):
    counts = Counter(str(tile) for tile in hand)
    return sum(counts[tile] >= 3 for tile in ['東', '南', '西', '北']) == 3 and any(counts[tile] >= 2 for tile in ['東', '南', '西', '北'])

def is_daisuushii(hand):
    counts = Counter(str(tile) for tile in hand)
    return all(counts[tile] >= 3 for tile in ['東', '南', '西', '北'])

def is_tsuuiisou(hand):
    return all(tile.suit is None for tile in hand)

def is_chinroutou(hand):
    return all(tile.value in [1, 9] and tile.suit in SUITS for tile in hand)

def is_ryuuiisou(hand):
    green_tiles = ['2s', '3s', '4s', '6s', '8s', '發']
    return all(str(tile) in green_tiles for tile in hand)

def is_chuuren_poutou(hand):
    if not is_chinitsu(hand):
        return False
    counts = Counter(tile.value for tile in hand)
    return counts[1] >= 3 and counts[9] >= 3 and all(counts[i] >= 1 for i in range(2, 9))

def is_suukantsu(hand):
    return sum(1 for meld in hand if len(meld) == 4) == 4

def is_tenhou(player):
    return player.is_dealer and player.turn_count == 1

def is_chiihou(player):
    return not player.is_dealer and player.turn_count == 1

def is_renhou(player):
    return not player.is_dealer and player.turn_count == 1 and player.won_on_discard

def is_double_riichi(player):
    return player.is_riichi and player.turn_count == 1

def is_menzen_tsumo(player):
    return player.is_tsumo and player.is_menzen

def is_haitei(player, wall):
    return player.is_tsumo and wall.is_empty()

def is_houtei(player, wall):
    return player.won_on_discard and wall.is_empty()

def is_rinshan_kaihou(player):
    return player.is_tsumo and player.drew_from_dead_wall

def is_chankan(player):
    return player.won_on_kan

def is_sanshoku_doukou(hand):
    melds = extract_melds(hand)
    triplets = [tuple(tile.value for tile in meld) for meld in melds if is_triplet(meld)]
    return any(all((v, 'm') in triplets and (v, 'p') in triplets and (v, 's') in triplets for v in range(1, 10)))

def is_sankantsu(hand):
    return sum(1 for meld in hand if len(meld) == 4) == 3

def is_sanankou(hand):
    return sum(1 for meld in hand if is_triplet(meld) and meld[0].is_closed) == 3

def is_honroutou(hand):
    return all(tile.value in [1, 9] or tile.suit is None for tile in hand)

def is_isshoku_sanjun(hand):
    melds = extract_melds(hand)
    sequences = [tuple(tile.value for tile in meld) for meld in melds if is_sequence(meld)]
    return any(all((v, v+1, v+2) in sequences and (v+3, v+4, v+5) in sequences and (v+6, v+7, v+8) in sequences for v in range(1, 4)))

def is_chiitoitsu(hand):
    counts = Counter(str(tile) for tile in hand)
    return len(counts) == 7 and all(count == 2 for count in counts.values())

def is_nagashi_mangan(player, discards):
    return all(tile.value in [1, 9] or tile.suit is None for tile in discards) and not player.has_called


def get_next_dora(indicator):
    if indicator is None:
        return None
    
    if indicator.suit in ['m', 'p', 's']:  # 数牌の場合
        next_value = indicator.value % 9 + 1
        return Tile(indicator.suit, next_value)
    elif indicator.suit is None:  # 字牌の場合
        honor_order = ['東', '南', '西', '北', '白', '發', '中']
        current_index = honor_order.index(indicator.value)
        next_index = (current_index + 1) % len(honor_order)
        return Tile(None, honor_order[next_index])
    else:
        return None  # 不正な牌の場合

class Wall:
    def __init__(self):
        self.tiles = []
        self.dora_indicators = []  # ドラ表示牌を初期化
        self.open_dora_indicators = []
        self.tiles = self.initialize_wall()
        self.dora_indicators = self.get_dora()
        self.open_dora_indicators = self.dora_indicators.copy()

    def initialize_wall(self):
        tiles = []
        # 数牌を生成
        for suit in SUITS:
            for num in NUMBERS:
                tiles.extend([Tile(suit, num) for _ in range(4)])  # 数牌を一度に追加
        # 字牌を生成
        tiles.extend([Tile(None, honor) for honor in HONORS for _ in range(4)])  # 字牌を一度に追加
        random.shuffle(tiles)  # シャッフル
        # ドラ表示牌を1枚引く
        self.dora_indicators.append(self.draw())
        self.open_dora_indicators.append(self.draw())  # ドラ表示牌を公開
        return tiles

    def draw(self) -> Tile:
        """山から牌を引くメソッド。

        Returns:
            Tile: 引いた牌。山が空の場合はNoneを返す。
        """
        return self.tiles.pop() if self.tiles else None

    def get_dora(self) -> List[Tile]:
        """ドラ牌を取得するメソッド。

        Returns:
            List[Tile]: ドラ牌のリスト。
        """
        return [get_next_dora(indicator) for indicator in self.open_dora_indicators]

def calculate_fu(hand, winning_tile, yaku_list, tsumo=False):
    # 簡略化された符計算
    fu = 20  # 基本符を20に変更（日本麻雀のルールに基づく）

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
    fu += 4 if is_special_wait(hand, winning_tile) else 2  # 特定の待ちの場合は4符加算、その他の場合は2符加算

    # 切り上げ
    fu = ((fu + 9) // 10) * 10
    return fu

def is_open(meld, hand):
    # メルドが開かれているか（他家からの切り牌で完成しているか）を判定
    return len(meld) == 3 and any(tile in hand for tile in meld) and meld[0] != meld[1] and meld[1] != meld[2]

def calculate_score(yaku_list, fu, dealer=False, tsumo=False):
    total_han = sum(yaku.han for yaku in yaku_list)

    # 日本麻雀の点数計算に基づく
    if total_han >= 13:
        return "役満"
    elif total_han >= 11:
        return "三倍満"
    elif total_han >= 8:
        return "倍満"
    elif total_han >= 6:
        return "跳満"
    elif total_han >= 5:
        base = fu * (2 ** (total_han + 2))
    else:
        base = fu * (2 ** (total_han + 2))  # total_hanが4未満の場合も同じ計算を行う

    score = base
    if dealer:
        score = int(score * 1.5)  # ディーラーの場合は1.5倍
    return int(score)  # 整数に変換して返す

def evaluate_yakus(hand, winning_tile, dora_tiles, player, wall):
    yaku_list = []
    total_fu = 0  # 符の合計を初期化

    if is_tanyao(hand):
        yaku_list.append(Yaku("タンヤオ", 1, "数牌の2から8のみで構成"))
        total_fu += 20  # タンヤオの符を追加
    if is_pinfu(hand, winning_tile):
        yaku_list.append(Yaku("平和", 1, "門前で役牌の対子を持たない"))
        total_fu += 30  # 平和の符を追加
    if is_chitoitsu(hand):
        yaku_list.append(Yaku("七対子", 2, "7つの対子で構成"))
        total_fu += 25  # 七対子の符を追加
    if is_sanankou(hand):
        yaku_list.append(Yaku("三暗刻", 2, "3つの暗刻を持つ"))
        total_fu += 30  # 三暗刻の符を追加
    if is_kokushi_musou(hand):
        yaku_list.append(Yaku("国士無双", 13, "13種類の国士牌とそのいずれかをもう1枚"))
        total_fu += 40  # 国士無双の符を追加
    if is_riichi(player):
        yaku_list.append(Yaku("立直", 1, "テンパイ状態で宣言"))
        total_fu += 20  # 立直の符を追加
    dora_count = is_dora(hand, dora_tiles)
    if dora_count > 0:
        yaku_list.append(Yaku(f"ドラ", dora_count, "ドラ表示牌に対応する牌"))
        total_fu += dora_count * 10  # ドラの符を追加
    if is_yakuhai(hand, player.wind, player.round_wind):
        yaku_list.append(Yaku("役牌", 1, "役牌を持つ"))
        total_fu += 10  # 役牌の符を追加
    if is_honroutou(hand):
        yaku_list.append(Yaku("混老頭", 2, "1と9のみで構成"))
        total_fu += 20  # 混老頭の符を追加
    if is_shousangen(hand):
        yaku_list.append(Yaku("小三元", 2, "白發中のうち2つ"))
        total_fu += 20  # 小三元の符を追加
    if is_honitsu(hand):
        yaku_list.append(Yaku("混一色", 2, "数牌のみで構成"))
        total_fu += 20  # 混一色の符を追加
    if is_junchan(hand):
        yaku_list.append(Yaku("純全帯", 2, "数牌のみで構成"))
        total_fu += 20  # 純全帯の符を追加
    if is_chinitsu(hand):
        yaku_list.append(Yaku("清一色", 6, "同じ牌のみで構成"))
        total_fu += 30  # 清一色の符を追加
    if is_suuankou(hand, winning_tile):
        yaku_list.append(Yaku("四暗刻", 8, "4つの暗刻を持つ"))
        total_fu += 20  # 四暗刻の符を追加
    if is_daisangen(hand):
        yaku_list.append(Yaku("大三元", 8, "白發中の3つ"))
        total_fu += 20  # 大三元の符を追加
    if is_shousuushii(hand):
        yaku_list.append(Yaku("小四喜", 11, "東南西北の4つ"))
        total_fu += 20  # 小四喜の符を追加
    if is_daisuushii(hand):
        yaku_list.append(Yaku("大四喜", 13, "東南西北の4つ"))
        total_fu += 20  # 大四喜の符を追加 
    if is_tsuuiisou(hand):
        yaku_list.append(Yaku("対々和", 2, "同じ牌の対子を2つ"))
        total_fu += 20  # 対々和の符を追加
    if is_chinroutou(hand):
        yaku_list.append(Yaku("清老頭", 2, "1と9のみで構成"))
        total_fu += 20  # 清老頭の符を追加
    if is_ryuuiisou(hand):
        yaku_list.append(Yaku("緑一色", 2, "緑牌のみで構成"))
        total_fu += 20  # 緑一色の符を追加
    if is_chuuren_poutou(hand):
        yaku_list.append(Yaku("九蓮宝燈", 13, "1から9の順子を持つ"))
        total_fu += 20  # 九蓮宝燈の符を追加
    if is_suukantsu(hand):
        yaku_list.append(Yaku("四暗刻", 13, "4つの暗刻を持つ"))
        total_fu += 20  # 四暗刻の符を追加
    if is_tenhou(player):
        yaku_list.append(Yaku("天和", 13, "テンパイ状態で宣言"))        
    if is_chiihou(player):
        yaku_list.append(Yaku("地和", 13, "テンパイ状態で宣言"))
    if is_renhou(player):
        yaku_list.append(Yaku("人和", 13, "テンパイ状態で宣言"))
    if is_double_riichi(player):
        yaku_list.append(Yaku("ダブル立直", 1, "テンパイ状態で宣言"))
    if is_menzen_tsumo(player):
        yaku_list.append(Yaku("門前ツモ", 1, "門前でツモ上がり"))
    if is_haitei(player, wall):
        yaku_list.append(Yaku("海底撈月", 1, "海底で上がり"))
    if is_houtei(player, wall):
        yaku_list.append(Yaku("河底撈魚", 1, "河底で上がり"))
    if is_rinshan_kaihou(player):
        yaku_list.append(Yaku("嶺上開花", 1, "嶺上で上がり"))
    if is_chankan(player):
        yaku_list.append(Yaku("槍槓", 1, "槍槓で上がり"))
    if is_sanshoku_doukou(hand):
        yaku_list.append(Yaku("三色同刻", 1, "三色同じ牌の暗刻を持つ"))
        

    # 上がり条件のチェック
    if player.is_tsumo:
        total_fu += 2  # ツモ上がりの場合の符を追加
    elif player.is_ron:
        total_fu += 10  # ロン上がりの場合の符を追加

    return yaku_list, total_fu  # 役のリストと符の合計を返す

class MahjongGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("麻雀ゲーム")
        self.setGeometry(100, 100, 1200, 800)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)
        players = [Player(f"プレイヤー{i+1}") for i in range(4)]
        self.game = Game(players)
        self.initUI()

        # 背景を緑色に設定
        self.setStyleSheet("background-color: green;")

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

        # 河、山、ドラ表示
        self.river_label = QLabel("河: []")
        self.layout.addWidget(self.river_label)
        self.dora_label = QLabel("ドラ: []")
        self.layout.addWidget(self.dora_label)

        self.update_display()

    def update_display(self):
        """UIを更新するメソッド"""
        # 山札の更新
        self.wall_label.setText(f"残り牌: {len(self.game.wall.tiles)}")

        # 河の更新
        self.river_label.setText(f"河: {self.game.discard_pile}")

        # ドラの更新（仮の実装）
        self.dora_label.setText(f"ドラ: {self.game.dora_indicators}")

        # プレイヤーの手牌更新
        for i, player in enumerate(self.game.players):
            self.update_player_hand(i, player.hand)

        # 捨て牌の更新
        discard_layout = self.layout.itemAt(3).layout()  # 捨て牌のレイアウトを取得
        self.clear_layout(discard_layout)  # 既存の捨て牌をクリア
        for tile in self.game.discard_pile:  # 捨て牌のリストを取得
            self.add_tile_button(discard_layout, tile)  # 新しい捨て牌を追加

    def update_player_hand(self, player_index, hand):
        """プレイヤーの手牌を更新するメソッド"""
        layout = self.player_hands[player_index]
        self.clear_layout(layout)  # 既存の手牌をクリア
        for tile in hand:
            self.add_tile_button(layout, tile)  # 新しい手牌を追加

    def clear_layout(self, layout):
        """レイアウト内の全ウィジェットをクリアするヘルパーメソッド"""
        for i in reversed(range(layout.count())): 
            layout.itemAt(i).widget().setParent(None)

    def add_tile_button(self, layout, tile):
        """タイルボタンを追加するヘルパーメソッド"""
        tile_button = QPushButton(str(tile))
        tile_button.setFixedSize(40, 60)
        layout.addWidget(tile_button)

    def tile_clicked(self, tile):
        """タイルがクリックされたときの処理"""
        print(f"{tile} がクリックされました")
        self.game.discard_pile.append(tile)  # タイルを捨て牌に追加
        self.update_display()  # 表示を更新

    def update_dora(self):
        # ドラの更新
        self.dora_label.setText(f"ドラ: {', '.join(map(str, self.game.dora_indicators))}")

def is_special_wait(hand, winning_tile):
    """特定の待ちの判定ロジックを実装"""
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
        self.hand = []  # ここでhand属性を初期化

# Gameクラスを定義
class Game:
    def __init__(self, players):
        """ゲームの初期化を行います。"""
        self.round_wind = '東'  # 場風
        self.bonus_points = 0  # 本場点数
        self.players = players
        self.player = players[0]  # 人間プレイヤー
        self.ai_players = players[1:]  # AIプレイヤー
        self.all_players = players
        self.wall = Wall()
        self.current_player_index = 0
        self.discard_pile = []
        self.dora_indicators = []
        self.first_round = True
        self.first_turn = True
        self.initUI()

    def initUI(self):
        """UIの初期化処理を行います。"""
        self.window = QMainWindow()
        self.window.setWindowTitle("麻雀ゲーム")
        self.window.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # プレイヤーの手牌表示エリア
        player_hand_layout = QHBoxLayout()
        self.player_hand_widget = QWidget()
        self.player_hand_widget.setLayout(player_hand_layout)
        main_layout.addWidget(self.player_hand_widget)

        # 捨て牌表示エリア
        discard_layout = QGridLayout()
        self.discard_widget = QWidget()
        self.discard_widget.setLayout(discard_layout)
        main_layout.addWidget(self.discard_widget)

        # AIプレイヤーの手牌表示エリア（簡略化）
        for _ in range(3):
            ai_hand_layout = QHBoxLayout()
            ai_hand_widget = QWidget()
            ai_hand_widget.setLayout(ai_hand_layout)
            main_layout.addWidget(ai_hand_widget)

        self.window.show()

    def start_game(self):
        """ゲームを開始します。"""
        self.deal_initial_hands()
        self.play_game()

    def deal_initial_hands(self):
        """初期手牌を配ります。"""
        for player in self.all_players:
            player.hand = [self.wall.draw() for _ in range(13)]

    def deal_initial_hands(self):
        """初期手牌を配ります。"""
        for player in self.all_players:
            player.hand = [self.wall.draw() for _ in range(13)]
        print("初期手牌が配られました。")  # デバッグ用

    def start_game(self):
        """ゲームを開始します。"""
        self.deal_initial_hands()
        self.play_game()  # play_game()が呼ばれることを確認

    def play_game(self):
        """ゲームの進行を管理します。"""
        self.first_round = True
        self.first_turn = True
        
        while not self.is_game_over():
            current_player = self.players[self.current_player_index]
            print(f"現在のプレイヤー: {current_player.name}")  # デバッグ用
            
            if self.first_turn and self.is_tenhou(current_player):
                self.handle_win(current_player, "天和")
                return
            
            if self.first_round and not self.first_turn and self.current_player_index != 0 and self.is_chiihou(current_player):
                self.handle_win(current_player, "地和")
                return
            
            state = self.get_state()
            action = self.get_action(current_player, state)
            self.perform_action(current_player, action)
            
            if self.first_round and not self.first_turn:
                for player in self.players:
                    if player != current_player and self.can_win_on_discard(player, action) and self.is_renhou(player):
                        self.handle_win(player, "人和")
                        return
            
            self.first_turn = False
            if self.current_player_index == 3:
                self.first_round = False
            
            self.current_player_index = (self.current_player_index + 1) % 4

    def is_tenhou(self, player):
        """天和の判定を行います。"""
        return self.first_turn and player == self.players[0] and self.is_winning_hand(player.hand)

    def is_chiihou(self, player):
        """地和の判定を行います。"""
        return self.first_round and player != self.players[0] and self.is_winning_hand(player.hand)

    def is_renhou(self, player):
        """人和の判定を行います。"""
        return self.first_round and not self.first_turn and player != self.players[0]

    def can_win_on_discard(self, player, discarded_tile):
        """捨て牌で和了できるか判定します。"""
        return self.is_winning_hand(player.hand + [discarded_tile])

    def handle_win(self, player, yaku_name):
        """和了処理を行います。"""
        print(f"{player.name}の{yaku_name}!")
        # 点数計算と精算処理

    def get_yaku(self, hand, winning_tile, is_tsumo):
        """役を取得します。"""
        yaku_list = []
        if self.is_tenhou(self.players[self.current_player_index]):
            yaku_list.append(Yaku("天和", 13, is_yakuman=True))
        elif self.is_chiihou(self.players[self.current_player_index]):
            yaku_list.append(Yaku("地和", 13, is_yakuman=True))
        elif self.is_renhou(self.players[self.current_player_index]):
            yaku_list.append(Yaku("人和", 5))  # 人和は役満ではなく5翻
        
        if self.players[self.current_player_index].in_double_riichi:
            yaku_list.append(Yaku("ダブル立直", 2))
        elif self.players[self.current_player_index].in_riichi:
            yaku_list.append(Yaku("立直", 1))
        
        return yaku_list

    def handle_player_turn(self):
        """プレイヤーの行動を処理します。"""
        player = self.all_players[self.current_player_index]
        drawn_tile = self.wall.draw()
        player.hand.append(drawn_tile)
        
        self.update_player_hand_display()
        
        discarded_tile = self.get_player_discard()
        player.hand.remove(discarded_tile)
        
        self.update_discard_display(discarded_tile)
        
        self.handle_calls(discarded_tile)

    def handle_ai_turn(self, ai_player):
        """AIプレイヤーの行動を処理します。"""
        drawn_tile = self.wall.draw()
        ai_player.hand.append(drawn_tile)
        
        game_state = self.get_game_state()
        discarded_tile = ai_player.ai.choose_discard_tile(ai_player.hand, game_state)
        ai_player.hand.remove(discarded_tile)
        
        self.update_discard_display(discarded_tile)
        ai_player.ai.handle_calls(discarded_tile)

    def is_game_over(self):
        """ゲーム終了条件をチェックします。"""
        return len(self.wall.tiles) == 0 or any(player.has_won() for player in self.all_players)

    def calculate_reward(self, player, winning_tile=None, is_tsumo=False):
        """報酬を計算します。"""
        if self.is_game_over():
            return self.calculate_final_reward(player)
        
        if winning_tile:
            score = self.calculate_score(player, winning_tile, is_tsumo)
            return score / 1000  # スコアを1000で割って正規化
        
        if self.is_tenpai(player.hand):
            return 0.1  # テンパイ状態にある場合、小さな正の報酬
        return 0  # それ以外の場合は報酬なし

    def calculate_final_reward(self, player):
        """ゲーム終了時の最終的な報酬を計算します。"""
        player_rank = self.get_player_rank(player)
        if player_rank == 1:
            return 1.0  # 1位の場合、最大の報酬
        elif player_rank == 2:
            return 0.5  # 2位の場合、中程度の報酬
        elif player_rank == 3:
            return 0.0  # 3位の場合、報酬なし
        else:
            return -0.5  # 4位の場合、負の報酬

    def get_player_rank(self, player):
        """プレイヤーの順位を計算します。"""
        sorted_players = sorted(self.players, key=lambda p: p.score, reverse=True)
        return sorted_players.index(player) + 1

    def calculate_score(self, player, winning_tile, is_tsumo):
        """スコアを計算します。"""
        yaku_list = self.get_yaku(player.hand, winning_tile, is_tsumo)
        han = sum(yaku.han for yaku in yaku_list)
        fu = self.calculate_fu(player.hand, winning_tile, is_tsumo)
        
        if any(yaku.is_yakuman for yaku in yaku_list):
            base_score = 8000
        elif han >= 13:
            base_score = 8000
        elif han >= 11:
            base_score = 6000
        elif han >= 8:
            base_score = 4000
        elif han >= 6:
            base_score = 3000
        else:
            base_score = min(fu * 2**(han + 2), 2000)
        
        additional_score = 300 if player == self.players[0] else 200  # 親は300点、子は200点
        additional_score *= self.bonus_points
        
        return base_score + additional_score
class QNetwork(nn.Module):
    def __init__(self, input_size: int, output_size: int):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

# Ensure 'device' is defined before using it
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # Add this line

class AIPlayer:
    def __init__(self, name: str, model_params: Dict[str, Any]):
        """
        AIプレイヤーを初期化します。

        Args:
            name (str): プレイヤーの名前
            model_params (Dict[str, Any]): モデルのパラメータ
        """
        self.name = name
        self.model = TransformerEncoder(**model_params).to(device)
        self.monte_carlo_tree_search = Monte_Carlo_Tree_Search(self.model, num_simulations=model_params['num_simulations'])
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=model_params['learning_rate'],
            weight_decay=model_params['weight_decay']
        )

    def select_action(self, state: Any) -> int:
        """
        現在の状態に基づいて行動を選択します。

        Args:
            state (Any): 現在のゲーム状態

        Returns:
            int: 選択された行動
        """
        action_probs = self.monte_carlo_tree_search.search(state)
        actions = list(action_probs.keys())
        probs = list(action_probs.values())
        return np.random.choice(actions, p=probs / np.sum(probs))

    def train(self, examples: List[Tuple[Any, List[float], float]]):
        """
        与えられた例を使用してモデルを訓練します。

        Args:
            examples (List[Tuple[Any, List[float], float]]): 訓練データ
                各要素は (state, mcts_probs, winner) のタプル
        """
        self.model.train()
        for state, mcts_probs, winner in examples:
            state_input = self.monte_carlo_tree_search.prepare_input(state)
            mcts_probs = torch.FloatTensor(mcts_probs).to(device)
            winner = torch.FloatTensor([winner]).to(device)

            self.optimizer.zero_grad()
            policy, value = self.model(state_input)
            policy_loss = -torch.sum(mcts_probs * torch.log(policy + 1e-10))  # 数値安定性のために小さな値を追加
            value_loss = F.mse_loss(value.squeeze(-1), winner)
            loss = policy_loss + value_loss
            loss.backward()
            self.optimizer.step()

def objective(trial: Trial) -> float:
    """
    Optunaの目的関数。ハイパーパラメータを最適化します。

    Args:
        trial (Trial): Optunaのトライアルオブジェクト

    Returns:
        float: 評価スコア（勝率）
    """
    model_params = {
        'input_size': 4 * 4 * 9,  # 4 players, 4 suits, 9 tiles
        'output_size': 34,  # Number of possible actions
        'nhead': trial.suggest_int('nhead', 4, 8),
        'num_layers': trial.suggest_int('num_layers', 2, 6),
        'dim_feedforward': trial.suggest_int('dim_feedforward', 512, 2048, step=256),
        'num_simulations': trial.suggest_int('num_simulations', 100, 400, step=50),
        'learning_rate': trial.suggest_loguniform('learning_rate', 1e-5, 1e-3),
        'weight_decay': trial.suggest_loguniform('weight_decay', 1e-5, 1e-3),
    }

    ai_player = AIPlayer("AI", model_params)
    
    def evaluate(player: AIPlayer) -> float:
        """
        AIプレイヤーの評価を行います。

        Args:
            player (AIPlayer): 評価対象のAIプレイヤー

        Returns:
            float: 勝率
        """
        test_games = 10
        wins = 0
        for _ in range(test_games):
            game = Game([player] + [AIPlayer(f"Opponent{i+1}", model_params) for i in range(3)])
            winner = game.play()
            if winner == player:
                wins += 0.1
        return wins / test_games

    return evaluate(ai_player)

def train_ai_players(num_trials: int):
    """
    AIプレイヤーをトレーニングします。

    Args:
        num_trials (int): トライアルの数
    """
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=num_trials)
    print(f"Best trial: {study.best_trial.params}")

def load_game_data(filename='game_data.h5') -> Dict[str, Any]:
    """
    ゲームデータをロードします。

    Args:
        filename (str): データファイル名

    Returns:
        Dict[str, Any]: プレイヤーごとのデータ
    """
    data = {}
    with h5py.File(filename, 'r') as f:
        for player_name in f.keys():
            data[player_name] = {
                'discarded_tiles': f[player_name]['discarded_tiles'][:],
                'actions': f[player_name]['actions'][:]
            }
    return data

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # ゲーム開始時に選択肢を表示
    choice = input("AIとの対戦を選択するには '1' を、強化学習を選択するには '2' を入力してください: ")

    if choice == '1':
        window = MahjongGUI()
        window.show()
        sys.exit(app.exec_())
    elif choice == '2':
        # AIプレイヤーのトレーニング
        train_ai_players(100)  # AIをトレーニング
    else:
        print("無効な選択です。プログラムを終了します。")
        sys.exit(1)