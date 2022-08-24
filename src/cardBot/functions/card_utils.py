from math import ceil


FORMATSTATS = {
    'balance': ('монету', 'монеты', 'монет'),
    'scraps': ('обрывок', 'обрывка', 'обрывков'),
    'experience': ('опыт','опыта', 'опыта'),
} 
    
class botUtils:
    def formatStats(stats: dict):
        return [
            f'{val} {FORMATSTATS[key][0 if val % 10 == 1 else 1 if val % 10 <= 4 and val % 10 >= 2 and val not in range(10, 20) else 2]}'
            for key, val in stats.items()
        ]
    
    def formatCards(cardData: dict, cardCount: int = 1, *, raritySymbol: bool = True):
        
        """
        About repeat or scraps
        If bool and it's True, then repeat
        If int, than it's scraps
        """  
        return ' '.join(
            filter(
                None, [
                    cardData['raritySymbol'] if raritySymbol else '',
                    cardData['name'],
                    f'(Ур. {cardData["level"]})' if cardData["level"] > 1 else '',
                    f'(x{cardCount})' if cardCount > 1 else '',
                    '(За повторки)' if cardData.get('repeat') else f"({botUtils.formatStats({'scraps': cardData.get('scrapCost')})[0]})" if cardData.get("scrapCost") else ''                   
                ]
            )
        )  
        
    def changeStats(data:dict, stats:dict = None, removeStats: dict = None):
        if stats is None: stats = {}
        if removeStats is None: removeStats = {}
        
        for key, val in stats.items():
            data[key] += val 
            
        for key, val in removeStats.items():
            data[key].remove(val)
            
    def calculateDestroyPrice(params: dict, card: dict, multiplier: int = 0.7):
        upgradePrice = botUtils.calculateUpgradePrice(params, card)
        if not upgradePrice: return
        
        return ceil(upgradePrice * multiplier)     
               
    def calculateUpgradePrice(params: dict, card:dict):
        if not params['rarityRatios'].get(str(card['rarity'])): return None
        
        return \
            params['defaultPrice'] + \
            params['rarityRatios'][str(card['rarity'])] * \
            card['level'] ** params['defaultPower']
                
    def findUpgradeableCards(cards: list, params: dict, scrapCount:int = 0) -> list:
        cardData = [
            (card, cards.count(card), cidx)
            for cidx,card in enumerate(cards)
            if card not in cards[cidx + 1:]  
            and card['level'] < card['maxlevel'] 
        ]
        
        upgradeableCards = []
        
        for card, cardCount, cardn in cardData:
            if (
                cardCount >= params['repeats'][str(card['rarity'])][card['level']-1]
            ): 
                upgradeableCards.append({
                    "index": cardn,
                    "repeat": params['repeats'][str(card['rarity'])][card['level']-1]
                })
           
            else:
                cardCost = botUtils.calculateUpgradePrice(params['cost'], card)
                if (
                    cardCost is None
                    or cardCost > scrapCount
                ):
                    continue

                upgradeableCards.append({
                    "index": cardn,
                    "scrapCost": int(cardCost)
                })  
               
        return upgradeableCards