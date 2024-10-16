# yaku_evaluator.py

from typing import List, Tuple, TYPE_CHECKING
from tiles import Tile
from collections import Counter
import itertools

if TYPE_CHECKING:
    from tiles import Tile

class YakuEvaluator:
    def __init__(self, is_dealer: bool = False):
        self.is_dealer = is_dealer

    def evaluate_hand(self, hand: List[Tile], is_closed: bool = True, is_tsumo: bool = True) -> Tuple[List[str], int, int]:
        try:
            yaku_list = self.check_general_yaku(hand, is_closed, is_tsumo)
            total_han = self.calculate_han(yaku_list)
            fu = self.calculate_fu(hand, yaku_list, is_tsumo, is_closed)
            return yaku_list, total_han, fu
        except Exception as e:
            print(f"Yaku評価中にエラーが発生しました: {e}")
            return [], 0, 0

    def check_general_yaku(self, hand: List[Tile], is_closed: bool, is_tsumo: bool) -> List[str]:
        yaku_list = []

        # 各役のチェック
        yaku_checks = {
            "断么九": self.is_tanyao(hand),
            "平和": self.is_pinfu(hand, is_closed, is_tsumo),
            "一盃口": self.is_ipeikou(hand),
            "両立直": self.is_ryanpeikou(hand),
            "三色同順": self.is_sanshokudoujun(hand),
            "三色同刻": self.is_sanshokudouko(hand),
            "一気通貫": self.is_ikkitsukan(hand),
            "対々和": self.is_toitoi(hand),
            "混全帯么九": self.is_honchantou(hand),
            "清一色": self.is_chinitsu(hand),
            "混一色": self.is_honitsu(hand),
            "小三元": self.is_shousangen(hand),
            "大三元": self.is_daisangen(hand),
            "小四喜": self.is_shousushi(hand),
            "大四喜": self.is_daisuushi(hand),
            "字一色": self.is_tsuimuso(hand),
            "七対子": self.is_chitoitsu(hand),
            "国士無双": self.is_kokushi_muushou(hand),
            "四暗刻": self.is_suanko(hand),
            "四暗刻単騎": self.is_suankotanki(hand),
            # 追加の役は必要に応じてここに追加
        }

        for yaku, has_yaku in yaku_checks.items():
            if has_yaku:
                yaku_list.append(yaku)

        return yaku_list

    def is_tanyao(self, hand: List[Tile]) -> bool:
        for tile in hand:
            if not tile.is_simple():
                return False
        return True

    def is_pinfu(self, hand: List[Tile], is_closed: bool, is_tsumo: bool) -> bool:
        # 平和の判定ロジックを実装
        # ここでは簡略化のため、仮実装
        if not is_closed or not is_tsumo:
            return False
        # 対子が役牌でないことを確認
        pair = self.get_pair(hand)
        if pair and not pair.is_honor() and not pair.is_dragons():
            # 全ての面子が順子であることを確認
            if self.all_melds_are_sequences(hand, pair):
                return True
        return False

    def is_ipeikou(self, hand: List[Tile]) -> bool:
        # 一盃口の判定ロジックを実装
        counts = Counter(tile.name for tile in hand)
        return any(count >= 2 for count in counts.values())

    def is_ryanpeikou(self, hand: List[Tile]) -> bool:
        # 両立直の判定ロジックを実装
        # 仮実装
        return False  # 実装が必要

    def is_sanshokudoujun(self, hand: List[Tile]) -> bool:
        # 三色同順の判定ロジックを実装
        return False  # 実装が必要

    def is_sanshokudouko(self, hand: List[Tile]) -> bool:
        # 三色同刻の判定ロジックを実装
        return False  # 実装が必要

    def is_ikkitsukan(self, hand: List[Tile]) -> bool:
        # 一気通貫の判定ロジックを実装
        return False  # 実装が必要

    def is_toitoi(self, hand: List[Tile]) -> bool:
        # 対々和の判定ロジックを実装
        return False  # 実装が必要

    def is_honchantou(self, hand: List[Tile]) -> bool:
        # 混全帯么九の判定ロジックを実装
        return False  # 実装が必要

    def is_chinitsu(self, hand: List[Tile]) -> bool:
        # 清一色の判定ロジックを実装
        suits = set(tile.suit for tile in hand if tile.suit)
        return len(suits) == 1

    def is_honitsu(self, hand: List[Tile]) -> bool:
        # 混一色の判定ロジックを実装
        suits = set(tile.suit for tile in hand if tile.suit)
        has_honor = any(tile.is_honor() for tile in hand)
        return len(suits) == 1 and has_honor

    def is_shousangen(self, hand: List[Tile]) -> bool:
        # 小三元の判定ロジックを実装
        dragons = ['P', 'F', 'C']
        count = 0
        for dragon in dragons:
            if sum(1 for tile in hand if tile.name == dragon) >= 3:
                count += 1
        return count >= 2

    def is_daisangen(self, hand: List[Tile]) -> bool:
        # 大三元の判定ロジックを実装
        dragons = ['P', 'F', 'C']
        return all(sum(1 for tile in hand if tile.name == dragon) >= 3 for dragon in dragons)

    def is_shousushi(self, hand: List[Tile]) -> bool:
        # 小四喜の判定ロジックを実装
        winds = ['E', 'S', 'W', 'N']
        count = 0
        for wind in winds:
            if sum(1 for tile in hand if tile.name == wind) >= 3:
                count += 1
        return count >= 3

    def is_daisuushi(self, hand: List[Tile]) -> bool:
        # 大四喜の判定ロジックを実装
        winds = ['E', 'S', 'W', 'N']
        return all(sum(1 for tile in hand if tile.name == wind) >= 3 for wind in winds)

    def is_tsuimuso(self, hand: List[Tile]) -> bool:
        # 字一色の判定ロジックを実装
        return all(tile.is_honor() for tile in hand)

    def is_chitoitsu(self, hand: List[Tile]) -> bool:
        # 七対子の判定ロジックを実装
        counts = Counter(tile.name for tile in hand)
        return len(counts) == 7 and all(count == 2 for count in counts.values())

    def is_kokushi_muushou(self, hand: List[Tile]) -> bool:
        # 国士無双の判定ロジックを実装
        required_tiles = [
            '1m', '9m', '1p', '9p', '1s', '9s',
            'E', 'S', 'W', 'N', 'P', 'F', 'C'
        ]
        unique_tiles = set(tile.name for tile in hand)
        if len(unique_tiles) != 13:
            return False
        # 任意の1牌が重複
        duplicates = [tile for tile in required_tiles if hand.count(tile) >= 2]
        return len(duplicates) == 1

    def is_suanko(self, hand: List[Tile]) -> bool:
        # 四暗刻の判定ロジックを実装
        triplet_counts = Counter(tile.name for tile in hand if hand.count(tile.name) >= 3)
        return len(triplet_counts) == 4 and all(hand.count(tile) >= 3 for tile in triplet_counts)

    def is_suankotanki(self, hand: List[Tile]) -> bool:
        # 四暗刻単騎の判定ロジックを実装
        triplet_counts = [tile for tile in set(hand) if hand.count(tile) == 3]
        pair_counts = [tile for tile in set(hand) if hand.count(tile) == 2]
        return len(triplet_counts) == 4 and len(pair_counts) == 1

    def calculate_han(self, yaku_list: List[str]) -> int:
        han = 0
        yaku_han = {
            "断么九": 1,
            "平和": 1,
            "一盃口": 1,
            "両立直": 3,
            "三色同順": 2,
            "三色同刻": 2,
            "一気通貫": 2,
            "対々和": 2,
            "混全帯么九": 2,
            "清一色": 6,
            "混一色": 3,
            "小三元": 2,
            "大三元": 13,
            "小四喜": 2,
            "大四喜": 13,
            "字一色": 13,
            "七対子": 2,
            "国士無双": 13,
            "四暗刻": 13,
            "四暗刻単騎": 13,
            # 追加の役は必要に応じてここに追加
        }
        for yaku in yaku_list:
            han += yaku_han.get(yaku, 0)
        return han

    def calculate_fu(self, hand: List[Tile], yaku_list: List[str], is_tsumo: bool, is_closed: bool) -> int:
        fu = 20  # 基本符

        # 面子から符を計算
        melds = self.get_all_melds(hand)
        for meld in melds:
            if len(meld) == 3:
                if meld[0].is_honor() or meld[0].is_dragons() or meld[0].is_terminal():
                    fu += 4  # 字牌、三元牌、端牌の刻子
                else:
                    fu += 2  # 順子の刻子
            elif len(meld) == 4:
                if meld[0].is_honor() or meld[0].is_dragons() or meld[0].is_terminal():
                    fu += 8  # 字牌、三元牌、端牌の槓子
                else:
                    fu += 4  # 順子の槓子

        # 対子から符を計算
        pair = self.get_pair(hand)
        if pair:
            if pair.is_honor():
                fu += 2
            elif pair.is_dragons():
                fu += 2
            elif pair.is_wind(self.is_dealer):
                fu += 2

        # 門前清自摸和の場合、ツモによる符数加算
        if is_tsumo and is_closed:
            fu += 2

        # 平和の場合、符は20符固定
        if "平和" in yaku_list:
            fu = 20
        else:
            # 点数を10未満は切り上げ
            fu = (fu + 9) // 10 * 10

        return fu

    def get_pair(self, hand: List[Tile]) -> Tile:
        counts = Counter(tile.name for tile in hand)
        for name, count in counts.items():
            if count >= 2:
                return Tile(name=name)
        return None

    def get_all_melds(self, hand: List[Tile]) -> List[List[Tile]]:
        # 仮実装: 面子をリストとして返す
        # 実際には順子や刻子を正しく検出する必要があります
        return [hand[i:i+3] for i in range(0, len(hand)-2, 3)]

    def all_melds_are_sequences(self, hand: List[Tile], pair: Tile) -> bool:
        # 仮実装: 全ての面子が順子であるかを確認
        # 実際には面子の解析が必要
        return True  # 実装が必要
