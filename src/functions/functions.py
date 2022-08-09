from time import time
from random import choice, randrange
from typing import Iterable
from backend.db import DB
from functions.card_utils import botUtils
import functions.game
from main import config


class UserError(Exception):
    """
    Raised when player does comply with requirements to execute function
    """
    pass


class generalFunctions:
    def dialog(self, dialog, data):
        self.conf.vk.send(
                self.conf.dialogs.getDialogParsed(data['vk']['peer_id'], dialog, userdata = data['db'])
            )
    
    def flip(self, _, data):
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                data['vk']['peer_id'], 
                preset = choice(["firstPlayer", "secondPlayer"])
            )
        )
    
    def openPack(self, pack, data):
        if not data["db"]["packs"][pack]:
            raise UserError('noPack')

        self.editDB = True
        data["db"]["packs"][pack] -= 1
        data["db"]["cards"].append(
            self.conf.cards.getCardByRarity(
                chances=self.conf['game']["packs"][pack]["rarities"]
            )
        )

        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                data['vk']['peer_id'],
                'purchase',
                userdata = data['db'],
                selectCard= -1
            )
        )
    
    def getPack(self, pack, data):    
        if self.conf['game']["packs"][pack]["price"] > data["db"]["balance"]:
            raise UserError('notEnoughMoney')

        self.editDB = True
        data["db"]["balance"] -= self.conf['game']["packs"][pack]["price"]
        data["db"]["packs"][pack] += 1

        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                data['vk']['user'],
                preset = "gotPack"
            )    
        )    
    
    def addCardsPool(self, pool, data):
        self.editDB = True
        data["db"]["cards"].extend(self.conf.cards.getCardByPool(pool))
        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                data['vk']['peer_id'],
                preset = 'poolcards',
                userdata = data['db'],
                selectCard = list(range(-len(pool),0))
            )
        )
    
    def showCards(self, cards, data):
        if not data["db"]["cards"]:
            raise UserError('noCards')
        
        isChat = data['vk']['user'] != data['vk']['peer_id']
        showPict = False
        
        cardData = self.conf.cards.getOwnedCards(data['db']['cards'])
        
        cardData = [
            (cd, cardData.count(cd))
            for cidx, cd in enumerate(cardData)
            if cd not in cardData[cidx+1:]
        ]
        
        if not cards: 
            pass
        
        elif isinstance(cards, list):
            cardData = [
                card
                for card in cardData
                if card[0]['name'].lower().find(' '.join(cards)) != -1
            ]
            showPict = len(cardData) == 1
        
        elif cards.get("level"):
            cardData = [
                card 
                for card in cardData if
                str(card[0]['level']) == cards['level'][-1]
            ]
        
        elif cards.get("rarity"):
            cardData = [
                card 
                for card in cardData if
                str(card[0]['rarity']) == cards['rarity'][-1]
            ]

        if not cardData:
            raise UserError('noCards')
        
        if not isChat or showPict:
            [self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    data['vk']['peer_id'],
                    text = f'x{cardCount}' if cardCount > 1 else '' 
                ),
                attachments= cardData['attachment']
            )
             for cardData, cardCount in cardData
            ]
            
        else:
            self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    data['vk']['peer_id'],
                    text = f'''Ваши карты:\n\n{
                        chr(10).join([
                        botUtils.formatCards(cdt, ccnt)
                        for cdt, ccnt in cardData   
                    ])}''' 
                ),    
            )
            
    def give(self, thing, data):
        if not thing:
            raise UserError('cantError')
        
        if (
            data['vk']['reply_id'] is None 
            or data['vk']['reply_id'] == data['vk']['user']
        ):
            user = data['db']
            if self.editDB:
                self.db.edit(user)
            
            self.editDB = False
        else:
            user = self.db.get(user = data["vk"]["reply_id"])

        if (
            isinstance(thing, list)
            and thing[0].lower() in {i.lower() for i in self.conf['status']['names']}   
        ):
            user['status'] = next(
                num
                for num, status in enumerate(self.conf['status']['names'])
                if thing[0].lower() == status.lower()
            )
        
            statusDays = (
                int(thing[-1])
                if len(thing) > 1 and thing[-1].isdecimal()
                else self.conf['status']["defaultDays"]
            )
            
            user['premium'] = int(time() // 86400 + statusDays + 1)
            
            self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    user['id'],
                    text = f'''
Вам был выдан статус {self.conf['status']['names'][user['status']]}\n
Истекает через {statusDays} {"день" if statusDays % 10 == 1 else "дня" if statusDays % 10 < 5 and statusDays % 10 >= 2 else "дней"}
                    '''
                )
            )

        if not isinstance(thing,dict):
            raise UserError('cantError')

        elif thing.get('win', False) != False:
            self.conf.rank.win(user)
            
            botUtils.changeStats(
                user, 
                stats = {'wins': 1} | self.conf['status']["battles"]['win'][user["status"]]
            )
            
            if not user['battles'] % self.conf['status']["streak"]['count']['win'][user["status"]]:
                botUtils.changeStats(
                    user, 
                    stats = self.conf['status']["streak"]['reward']['win'][user["status"]]
                )
            
        elif thing.get('lose', False) != False:
            self.conf.rank.lose(user)
            
            botUtils.changeStats(
                user, 
                stats = {'loses': 1} | self.conf['status']["battles"]['lose'][user["status"]]
            )
            
            if not user['battles'] % self.conf['status']["streak"]['count']['lose'][user["status"]]:
                botUtils.changeStats(
                    user, 
                    stats = self.conf['status']["streak"]['reward']['lose'][user["status"]]
                )
    
        elif (
            thing.get("balance")
            and thing['balance'][-1].lstrip('-').isdecimal()  
        ):
            user['balance'] += int(thing['balance'][-1])
    
        elif (
            thing.get("scraps")
            and thing['scraps'][-1].lstrip('-').isdecimal()  
        ):
            user['scraps'] += int(thing['scraps'][-1])    

        elif (
            thing.get("pack")
            and thing['pack'][0] in map(str, range(len(self.conf['game']["packs"])))
        ):
            user['packs'][int(thing['pack'][0])] += (
                int(thing['pack'][1])
                if len(thing['pack']) > 1 and thing['pack'][-1].lstrip("-").isdecimal()
                else 1
            )

        elif thing.get("cards", False) != False:
            cardData = thing.get("cards")

            if cardData[-1].lstrip('-').isdecimal(): 
                foundCardLevel, thing['cards'] = (
                    int(cardData[-1]),
                    thing['cards'][:-1]
                ) 
            else:
                foundCardLevel = 1

            foundCardID = next((
                cid
                for cid, cdt in enumerate(self.conf.cards.allCards())
                if foundCardLevel in range(len('photo'))
                and cdt['name'].lower().find(" ".join(thing['cards'])) != -1
            ),
            None    
            )
            
            if foundCardID is None:
                raise UserError('cardDoesNotExist')
            
            user['cards'].append({
                "id": foundCardID,
                'level': foundCardLevel
            })    
                
        else: return
        
        self.db.edit(user)
    
    def remove(self, thing, data):
        if not thing:
            raise UserError('cantError')
        
        if (
            data['vk']['reply_id'] is not None 
            and data['vk']['reply_id'] != data['vk']['user']
        ):
            user = self.db.get(data['vk']['reply_id'])
        
        else:
            user = data['db']
            if self.editDB:
                self.db.edit(user)
                
            self.editDB = False
        
        if not isinstance(thing,dict):
            raise UserError('cantError')
         
        if thing.get('win', False) != False:
            self.conf.rank.rwin(user)
            
            if not user['battles'] % self.conf['status']["streak"]['count']['win'][user["status"]]:
                botUtils.changeStats(
                    user,
                    {key: -val
                    for key, val in self.conf['status']["streak"]['reward']['win'][user["status"]]
                    }
                )
            
            botUtils.changeStats(
                user,
                {'wins': -1} | {
                    key: -val
                    for key, val in self.conf['status']["battles"]['win'][user["status"]]
                }
            )
            

        elif thing.get('lose', False) != False:
            self.conf.rank.rlose(user)
            
            if not user['battles'] % self.conf['status']["streak"]['count']['win'][user["status"]]:
                botUtils.changeStats(
                    user,
                    {key: -val
                    for key, val in self.conf['status']["streak"]['reward']['win'][user["status"]]
                    }
                )
            
            botUtils.changeStats(
                user,
                {'loses': -1} | {
                    key: -val
                    for key, val in self.conf['status']["battles"]['lose'][user["status"]]
                }
            )
    
        elif (
            thing.get("pack")
            and thing['pack'][0] in map(str, range(len(self.conf['game']["packs"])))
        ):
            user['packs'][int(thing['pack'][0])] -= (
                int(thing['pack'][1])
                if len(thing['pack']) > 1 and thing['pack'].lstrip("-").isdecimal()
                else 1
            )
    
        elif thing.get("cards"):
            cardLevel = 1
            if thing['cards'][-1].lstrip('-').isdecimal():
                cardLevel, thing['cards'] = (
                    int(thing["cards"][-1]),
                    thing["cards"][:-1],
                )
                
            foundCardID = next((
                    cardID
                    for cardID, cdDT in enumerate(
                            self.conf.cards.getOwnedCards(user["cards"]),
                        )
                    if cdDT['level'] == cardLevel
                    and cdDT["name"].lower().find(" ".join(thing["cards"])) != -1
                
            ), None
            )
            
            if foundCardID is None:
                raise UserError('noСards')
            
            user['cards'].pop(foundCardID)
    
        else: return
        
        self.db.edit(user)
        
    def profile(self, _, data):
        isChat = data['vk']['peer_id'] != data['vk']['user']
        
        if (
            data['vk']['reply_id'] is None 
            or data['vk']['reply_id'] == data['vk']['user'] 
        ):
            self.conf.vk.send(
                self.conf.dialogs.getDialogParsed(data['vk']['peer_id'], 'profile', userdata = data['db']) 
                | ({'keyboard': None} if isChat else {}) 
            )
    
        else:
            isAdmin = self.conf.vk.isAdmin(data["vk"]["peer_id"], data["vk"]["user"])
            userData = self.db.get(user = data['vk']['reply_id'])
            
            self.conf.vk.send(
                self.conf.dialogs.getDialogParsed(
                    data['vk']['user'] if isAdmin 
                        else data['vk']['peer_id'], 
                        
                    'profile' if isAdmin
                        else "profile_inline_otheruser",
                         
                    userdata = userData
                    ) 
            | {'keyboard': None}
            ) 
                
    def chance(self, chance, data):
        if not chance: 
            raise UserError('cantError')
        
        if chance[-1] not in map(str, range(0, 101)):
            raise UserError('wrongNumber')
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                data['vk']['peer_id'],
                text = 'Успешно' 
                    if randrange(1, 101) <= int(chance[0])
                    else 'Не успешно'
            )
        )
        
    def destroy(self, card, data):
        if len(data['db']['cards']) <= self.conf['game']['cards']['break'].get("minimumCards", 0):
            raise UserError('noDestoyableCards')
        
        if (
            not isinstance(card, list)
            or not card  
        ):
            raise UserError('cantError')
        
        cardDataAll = self.conf.cards.getOwnedCards(data['db']['cards'])
        
        cardLevel = None
        if card[-1].lstrip().isdecimal():
            cardLevel = int(card[-1])
            card = card[:-1]
        
        destroyableCards = [
            (cidx, cdt)
            for cidx, cdt in enumerate(cardDataAll)
            if cdt['name'].lower().find(" ".join(card)) != -1
        ]
        
        if not destroyableCards:
            raise UserError('noDestoyableCards')
        
        if cardLevel is None:
            cardIndex, cardData = next(iter(sorted(
                destroyableCards,
                key = lambda x: x[1]['level']
            )))
        else:
            cardIndex, cardData = next((
                (cidx, cdt) 
                for cidx, cdt in destroyableCards
                if cdt['level'] == cardLevel),
                (None, None)
            )
            if cardIndex is None:
                raise UserError('noDestoyableCards')
                
        cardPrice = botUtils.calculateDestroyPrice(
            self.conf['game']['cards']['upgrade']['cost'],
            cardData,
            self.conf['game']['cards']['break'].get('destroyMultiplier', 0.7)
        )
        
        self.editDB = True
        data['db']['cards'].pop(cardIndex)
        data['db']['scraps'] += cardPrice
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                data['vk']['peer_id'],
                text = f'Разорвана карта\n{botUtils.formatCards(cardData)}\nВы получаете {cardPrice} обрывков',
            )
        )    
    
    def upgrade(self, card, data):
        cardData = self.conf.cards.getOwnedCards(data['db']['cards'])
        
        upgradeableCards = [
            cardData[cd['index']] | cd
            for cd in botUtils.findUpgradeableCards(
            cardData,
            self.conf['game']['cards']['upgrade'],
            data['db']['scraps']        
        )]
        
        if not card:
            if not upgradeableCards:
                raise UserError('upgradeFail')

            self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    data['vk']['peer_id'],
                    text = f"""
Список карт, доступных для улучшения:\n\n
{
    chr(10).join([
        botUtils.formatCards(cd)
        for cd in upgradeableCards
    ])
}

Стобы улучшить карту, напишите .ап <карта>
                    """
                )
            )
            
        else:
            if not isinstance(card, list): return
            
            card = next((
                cardd
                for cardd in upgradeableCards
                if cardd['name'].lower().find(' '.join(card)) != -1
            ), None)
            
            if card is None:
                raise UserError('upgradeFail')
            
            self.conf.vk.send(
                self.conf.dialogs.getDialogParsed(
                    data['vk']['peer_id'],
                    "upgraded",
                    userdata = data['db'],
                    selectCard = card['index']
                )
            )
            
            self.editDB = True
            if card.get('repeat'):
                cardIndex = card['index']
                  
                for _ in range(card.get('repeat') - 1):
                    data['db']['cards'].pop(
                        data['db']['cards'].index(
                            data['db']['cards'][cardIndex]
                        )
                    )
                    cardIndex -= 1
                    
                data['db']['cards'][cardIndex]['level'] += 1  
                
            elif card.get('scrapCost'):
                data['db']['cards'][card['index']]['level'] += 1
                data['db']['scraps'] -= card['scrapCost'] 

    def game(self, _role, data):
        if "random" in _role:
            _role = choice(('player', 'judge'))
        
        self._game.addToLobby(data['db']['id'],functions.game.role[_role])

    def __init__(self,conf: config, data: dict = None, payload: list[dict] = None, db: DB = None, _game = None):
        self.conf = conf
        self.db = db
        self._game = _game
        self.editDB = False
        
        if not isinstance(payload, Iterable): return 
        
        for func in payload:
            for key, val in func.items():
                method = getattr(self, key, None)
                if method is None: continue
                
                
                try:
                    method(val, data)
                except UserError as preset:
                    self.conf.vk.send(
                        self.conf.dialogs.getDialogPlain(
                            data['vk']['peer_id'],
                            preset=preset.args
                        )
                    )