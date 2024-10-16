# test_yaku_evaluator.py

import pytest
from tiles import Tile
from yaku_evaluator import YakuEvaluator

@pytest.fixture
def evaluator():
    return YakuEvaluator(is_dealer=True)

def test_tanyao(evaluator):
    hand = [Tile(name=f"2m"), Tile(name=f"3m"), Tile(name=f"4m"),
            Tile(name=f"5p"), Tile(name=f"6p"), Tile(name=f"7p"),
            Tile(name=f"2s"), Tile(name=f"3s"), Tile(name=f"4s"),
            Tile(name=f"5m"), Tile(name=f"6m"), Tile(name=f"7m"), Tile(name=f"8m"), Tile(name="5m")]
    yaku, han, fu = evaluator.evaluate_hand(hand, is_closed=True, is_tsumo=True)
    assert "断么九" in yaku, "タンヤオの判定が誤っています"

def test_pinfu(evaluator):
    hand = [
        Tile(name="2m"), Tile(name="3m"), Tile(name="4m"),
        Tile(name="5p"), Tile(name="6p"), Tile(name="7p"),
        Tile(name="2s"), Tile(name="3s"), Tile(name="4s"),
        Tile(name="6m"), Tile(name="7m"), Tile(name="8m"),
        Tile(name="5m"),
        Tile(name="5m")  # 対子
    ]
    yaku, han, fu = evaluator.evaluate_hand(hand, is_closed=True, is_tsumo=True)
    assert "平和" in yaku, "ピンフの判定が誤っています"
