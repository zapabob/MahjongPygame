# tiles.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
import pygame
import os

@dataclass
class Tile:
    name: str
    image: Optional[pygame.Surface] = field(default=None, repr=False)

    def load_image(self, image_size=(50, 70)) -> None:
        """
        タイルの画像をロードし、リサイズします。画像がない場合はNoneのまま。
        """
        image_path = os.path.join('images', 'tiles', f"{self.name}.png")
        if os.path.exists(image_path):
            image = pygame.image.load(image_path).convert_alpha()
            self.image = pygame.transform.scale(image, image_size)
        else:
            self.image = None  # 画像がない場合

    @property
    def suit(self) -> Optional[str]:
        """
        スート（m, p, s）を返す。字牌の場合はNoneを返す。
        """
        if self.name[-1] in ['m', 'p', 's']:
            return self.name[-1]
        return None

    @property
    def number(self) -> Optional[int]:
        """
        数字牌の場合は番号を返す。字牌の場合はNoneを返す。
        """
        if self.suit:
            try:
                return int(self.name[:-1])
            except ValueError:
                return None
        return None

    def is_simple(self) -> bool:
        """
        2から8の数牌かどうかを判定します。
        """
        return self.number is not None and 2 <= self.number <= 8

    def is_terminal(self) -> bool:
        """
        1または9の数牌かどうか、または字牌かどうかを判定します。
        """
        return (self.number == 1 or self.number == 9) or self.is_honor()

    def is_dragons(self) -> bool:
        """
        三元牌かどうかを判定します。
        """
        return self.name in ['P', 'F', 'C']  # 白、發、中

    def is_honor(self) -> bool:
        """
        字牌かどうかを判定します。
        """
        return self.name in ['E', 'S', 'W', 'N', 'P', 'F', 'C']

    def is_wind(self, is_dealer: bool = False) -> bool:
        """
        風牌かどうかを判定します。
        """
        return self.name in ['E', 'S', 'W', 'N']

def create_tiles() -> List[Tile]:
    """
    すべての牌を生成します。
    """
    suits = ['m', 'p', 's']
    numbers = list(range(1, 10))
    honor_tiles = ['E', 'S', 'W', 'N', 'P', 'F', 'C']  # 東、南、西、北、白、發、中
    tiles = []
    
    for suit in suits:
        for number in numbers:
            for _ in range(4):  # 各牌は4枚存在
                tiles.append(Tile(name=f"{number}{suit}"))

    for honor in honor_tiles:
        for _ in range(4):
            tiles.append(Tile(name=honor))
    
    return tiles
