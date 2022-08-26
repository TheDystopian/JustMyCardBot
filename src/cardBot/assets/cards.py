from collections import defaultdict
from itertools import chain
from random import choice, randint
from operator import itemgetter

from types import NoneType
from typing import Iterable


class cards:
    def __init__(self, conf):
        self.conf = conf

        self.__cardsByRarity = defaultdict(list)
        self.__pooledCards = defaultdict(list)

        for cardID, card in enumerate(conf["game"]["cards"]["cards"]):
            self.__cardsByRarity[str(card.get("rarity"))].append(cardID)
            self.__pooledCards[card.get("pool")].append(cardID)

    def getCardByRarity(
        self, cards: list[int] = None, chances: dict | int = None, level: int = 1
    ):
        if chances is None:
            chances = self.conf["game"]["cards"]["defaultChance"]

        if not isinstance(chances, dict):
            return {
                "id": choice(
                    self.__cardsByRarity[chances]
                    if chances != 0
                    else list(
                        chain.from_iterable(
                            [
                                cards
                                for rarity, cards in self.__cardsByRarity.items()
                                if rarity[0]
                                != self.conf["game"]["cards"]["noRandomIndicator"]
                            ]
                        )
                    )
                ),
                "level": level,
            }

        if cards is None:
            cards = self.__cardsByRarity
        else:
            cds = defaultdict(list)
            for cardID in cards:
                cds[str(self.conf["game"]["cards"]["cards"][cardID]["rarity"])].append(
                    cardID
                )
            cards = cds

        chances = {
            k: chances[k] for k in sorted(chances, reverse=True) if k in cards.keys()
        }

        chances = {
            rarity: sum(list(chances.values())[: i + 1])
            for i, rarity in enumerate(chances)
        }

        if "1" in cards.keys() and not "1" in chances:
            chances["1"] = 100 - sum(chances.values())

        random = randint(1, sum(chances.values()))

        return {
            "id": choice(
                cards[next((k for k, v in chances.items() if random <= v), "1")]
            ),
            "level": level,
        }

    def getCardByPool(self, pool):
        if not isinstance(pool, list):
            pool = [pool]

        return [self.getCardByRarity(self.__pooledCards[a]) for a in pool]

    def getOwnedCards(
        self, carddata: list, *, select: int | list = None, sort: str = None
    ):
        if not carddata:
            return []
        if not isinstance(select, (list, tuple)) and select is not None:
            select = [select]
        carddata = carddata if not select else [carddata[i] for i in select]

        returnable = [
            {
                "name": self.conf["game"]["cards"]["cards"][i["id"]]["name"],
                "rarity": self.conf["game"]["cards"]["cards"][i["id"]]["rarity"],
                "attachment": self.conf["game"]["cards"]["cards"][i["id"]]["photo"][
                    f'lvl{i["level"]}'
                ],
                "level": i["level"],
                "maxlevel": len(self.conf["game"]["cards"]["cards"][i["id"]]["photo"]),
                "raritySymbol": self.conf["game"]["cards"]["indicators"].get(
                    str(self.conf["game"]["cards"]["cards"][i["id"]]["rarity"]), ""
                ),
            }
            for i in carddata
        ]
        return returnable if not sort else sorted(returnable, key=itemgetter(sort))
