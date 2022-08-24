from operator import itemgetter
from time import time
from random import choice, randrange
from backend.db import DB
from functions.card_utils import botUtils
import functions.game as funcgame
import components.config as config


class UserError(Exception):
    """
    Raised when player does not comply with requirements to execute function
    """
    pass


class generalFunctions:
    def dialog(self, dialog):
        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data['vk']['peer_id'], 
                dialog, 
                userdata = self.data['db'],
                packs = [i.get("price") for i in self.conf['game']["packs"]]
            )
        )
    
    def flip(self, _):
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                self.data['vk']['peer_id'], 
                preset = choice(["firstPlayer", "secondPlayer"])
            )
        )
    
    def openPack(self, pack):
        if not self.data["db"]["packs"][pack]:
            raise UserError('noPack')

        self.editDB = True
        self.data["db"]["packs"][pack] -= 1
        self.data["db"]["cards"].append(
            self.conf.cards.getCardByRarity(
                chances=self.conf['game']["packs"][pack]["rarities"]
            )
        )

        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data['vk']['peer_id'],
                'purchase',
                userdata = self.data['db'],
                selectCard= -1
            )
        )
    
    def getPack(self, pack):    
        if self.conf['game']["packs"][pack]["price"] > self.data["db"]["balance"]:
            raise UserError('notEnoughMoney')

        self.editDB = True
        self.data["db"]["balance"] -= self.conf['game']["packs"][pack]["price"]
        self.data["db"]["packs"][pack] += 1

        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                self.data['vk']['user'],
                preset = "gotPack"
            )    
        )    
    
    def addCardsPool(self, pool):
        self.editDB = True
        self.data["db"]["cards"].extend(self.conf.cards.getCardByPool(pool))
        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data['vk']['peer_id'],
                preset = 'poolcards',
                userdata = self.data['db'],
                selectCard = list(range(-len(pool),0))
            )
        )
    
    def showCards(self, cards):
        if not self.data["db"]["cards"]:
            raise UserError('noCards')
        
        isChat = self.data['vk']['user'] != self.data['vk']['peer_id']
        showPict = False
        
        cardData = self.conf.cards.getOwnedCards(self.data['db']['cards'])
        
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
                    self.data['vk']['peer_id'],
                    text = f'x{cardCount}' if cardCount > 1 else '' 
                ),
                attachments= cardData['attachment']
            )
             for cardData, cardCount in cardData
            ]
            
        else:
            self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    self.data['vk']['peer_id'],
                    text = f'''Ваши карты:\n\n{
                        chr(10).join([
                        botUtils.formatCards(cdt, ccnt)
                        for cdt, ccnt in cardData   
                    ])}''' 
                ),    
            )
            
    def give(self, thing):
        if not thing:
            raise UserError('cantError')
        
        if (
            self.data['vk']['reply_id'] is None 
            or self.data['vk']['reply_id'] == self.data['vk']['user']
        ):
            user = self.data['db']
            if self.editDB:
                self.db.edit(user)
            
            self.editDB = False
        else:
            user = self.db.get(user = self.data["vk"]["reply_id"])

        if (
            isinstance(thing, list)
            and thing[0].lower() in {i['name'].lower() for i in self.conf['status']['status']}   
        ):
            status = next(
                num
                for num, status in enumerate(self.conf['status']['status'])
                if thing[0].lower() == status['name'].lower()
            )
        
            statusDays = (
                int(thing[-1])
                if len(thing) > 1 and thing[-1].isdecimal()
                else self.conf['status']["defaultDuration"]
            )
            
            user['day'] = int(time() // 86400 + statusDays)
            user['battles'] += self.conf['status']['status'][status]['battles']['count'] - self.conf['status']['status'][user['status']]['battles']['count']
            user['status'] = status
            
            self.conf.vk.send(
                self.conf.dialogs.getDialogParsed(
                    user['id'],
                    'statusUpgrade',
                    userdata = user,
                    statusDays = f'{statusDays} {"день" if statusDays % 10 == 1 else "дня" if statusDays % 10 < 5 and statusDays % 10 >= 2 else "дней"}'
                )
            )
            
            
            self.db.edit(user)
            return

        if not isinstance(thing,dict):
            raise UserError('cantError')

        elif thing.get('win', False) != False:
            self.conf.rank.win(user)
            
            botUtils.changeStats(
                user, 
                stats = {'win': 1} | self.conf['status']['status'][user['status']]['battles']['win']
            )
            
            if not user['battles'] % self.conf['status']['status'][user["status"]]["streak"]['win']['count']:
                botUtils.changeStats(
                    user, 
                    stats = self.conf['status']['status'][user["status"]]["streak"]['win']['reward']
                )
            
        elif thing.get('lose', False) != False:
            self.conf.rank.lose(user)
            
            botUtils.changeStats(
                user, 
                stats = {'lose': 1} | self.conf['status']['status'][user['status']]['battles']['lose']
            )
            
            if not user['battles'] % self.conf['status']['status'][user["status"]]["streak"]['lose']['count']:
                botUtils.changeStats(
                    user, 
                    stats =  self.conf['status']['status'][user["status"]]["streak"]['lose']['reward']
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
                for cid, cdt in enumerate(self.conf['game']['cards']['cards'])
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
        
        elif (
            thing.get("rank")
            and thing['rank'][-1].lstrip('-').isdecimal()   
        ):
            user['experience'] += int(thing['rank'][-1])
           
        else: return
        
        self.db.edit(user)
    
    def remove(self, thing):
        if not thing:
            raise UserError('cantError')
        
        if (
            self.data['vk']['reply_id'] is not None 
            and self.data['vk']['reply_id'] != self.data['vk']['user']
        ):
            user = self.db.get(self.data['vk']['reply_id'])
        
        else:
            user = self.data['db']
            if self.editDB:
                self.db.edit(user)
                
            self.editDB = False
        
        if not isinstance(thing,dict):
            raise UserError('cantError')
         
        if thing.get('win', False) != False:
            self.conf.rank.rwin(user)
            
            if not user['battles'] % self.conf['status']['status'][user["status"]]["streak"]['win']['count']:
                botUtils.changeStats(
                    user,
                    {key: -val
                    for key, val in self.conf['status']['status'][user["status"]]["streak"]['win']['count']
                    }
                )
            
            botUtils.changeStats(
                user,
                {'win': -1} | {
                    key: -val
                    for key, val in self.conf['status']['status'][user["status"]]["streak"]['win']['reward']
                }
            )
            

        elif thing.get('lose', False) != False:
            self.conf.rank.rlose(user)
            
            if not user['battles'] % self.conf['status']['status'][user["status"]]["streak"]['lose']['count']:
                botUtils.changeStats(
                    user,
                    {key: -val
                    for key, val in self.conf['status']['status'][user["status"]]["streak"]['lose']['count']
                    }
                )
            
            botUtils.changeStats(
                user,
                {'lose': -1} | {
                    key: -val
                    for key, val in self.conf['status']['status'][user["status"]]["streak"]['lose']['reward']
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
                raise UserError('noCardsPlr')
            
            user['cards'].pop(foundCardID)
    
        else: return
        
        self.db.edit(user)
        
    def profile(self, _):
        isAdmin = self.conf.vk.isAdmin(self.data["vk"]["peer_id"], self.data["vk"]["user"])
        isChat = self.data['vk']['peer_id'] != self.data['vk']['user']
        
        if self.data['vk']['reply_id']:
            userData = self.db.get(user = self.data['vk']['reply_id'])
        else:
            userData = self.data['db']
        
        if isAdmin:
            self.conf.vk.send(
                self.conf.dialogs.getDialogParsed(
                    self.data['vk']['user'] if self.data['vk']['reply_id'] != self.data['vk']['user'] and self.data['vk']['reply_id'] is not None else self.data['vk']['peer_id'],
                    'profile',
                    userdata = userData 
                ) | ({'keyboard': None} if isChat else {}) 
            )
            return
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data['vk']['peer_id'],
                'profile_inline_otheruser' if self.data['vk']['reply_id'] != self.data['vk']['user'] and self.data['vk']['reply_id'] is not None else 'profile',
                userdata = userData 
            ) | ({'keyboard': None} if isChat else {}) 
        )
                
    def chance(self, chance):
        if not chance: 
            raise UserError('cantError')
        
        if chance[-1] not in map(str, range(0, 101)):
            raise UserError('wrongNumber')
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                self.data['vk']['peer_id'],
                text = 'Успешно' 
                    if randrange(1, 101) <= int(chance[0])
                    else 'Не успешно'
            )
        )
        
    def destroy(self, card):
        if len(self.data['db']['cards']) <= self.conf['game']['cards']['break'].get("minimumCards", 0):
            raise UserError('minimumCards')
        
        if (
            not isinstance(card, list)
            or not card  
        ):
            raise UserError('cantError')
        
        cardDataAll = self.conf.cards.getOwnedCards(self.data['db']['cards'])
        
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
            self.conf['game']['cards']['break'].get('multiplier', 0.7)
        )
        if not cardPrice:
            raise UserError('noDestoyableCards')
        
        
        self.editDB = True
        self.data['db']['cards'].pop(cardIndex)
        self.data['db']['scraps'] += cardPrice
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                self.data['vk']['peer_id'],
                text = f'Разорвана карта\n{botUtils.formatCards(cardData)}\nВы получаете {cardPrice} обрывков',
            )
        )    
    
    def upgrade(self, card):
        if len(self.data['db']['cards']) <= self.conf['game']['cards']['break'].get("minimumCards", 0):
            raise UserError('minimumCards')
        
        cardData = self.conf.cards.getOwnedCards(self.data['db']['cards'])
        
        upgradeableCards = [
            cardData[cd['index']] | cd
            for cd in botUtils.findUpgradeableCards(
            cardData,
            self.conf['game']['cards']['upgrade'],
            self.data['db']['scraps']        
        )]
        
        if not card:
            if not upgradeableCards:
                raise UserError('upgradeFail')

            return self.conf.vk.send(
                self.conf.dialogs.getDialogParsed(
                    self.data['vk']['peer_id'],
                    preset = 'upgradeCards',
                    upgradeCardsList = '\n'.join([
                        botUtils.formatCards(cd)
                        for cd in upgradeableCards
                    ])
                )
            )

        if not isinstance(card, list): return
        
        
        card = sorted([
                cardd
                for cardd in upgradeableCards
                if cardd['name'].lower().find(' '.join(card)) != -1  
                ],
                reverse = True,
                key = itemgetter('level')
            )

        if card is None:
            raise UserError('upgradeFail')
        
        card = card[0]
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data['vk']['peer_id'],
                "upgraded",
                userdata = self.data['db'],
                selectCard = card['index']
            )
        )
        
        self.editDB = True
        if card.get('repeat'):
            cardIndex = card['index']
                
            for _ in range(card.get('repeat') - 1):
                self.data['db']['cards'].pop(
                    self.data['db']['cards'].index(
                        self.data['db']['cards'][cardIndex]
                    )
                )
                cardIndex -= 1
                
            self.data['db']['cards'][cardIndex]['level'] += 1  
            
        elif card.get('scrapCost'):
            self.data['db']['cards'][card['index']]['level'] += 1
            self.data['db']['scraps'] -= card['scrapCost'] 

    def game(self, _role):
        if 'stop' in _role:
            self.payload.append({'dialog': 'profile'})
            return
        
        if "random" in _role:
            _role = choice(('player', 'judge'))

            
        if self.data['db']['battles'] <= 0 and _role == 'player': 
            raise UserError('nobattles')
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data['vk']['user'],
                "randomRole",
                role = getattr(funcgame.role, _role).title
            )
        )
        
        self._game.addToLobby(self.data['db']['id'], getattr(funcgame.role, _role))

    def trade(self, tradeData):
        if (
            not tradeData
        ):
            raise UserError('cantTrade')
        
        if 'balance' in tradeData:
            try:
                amount = int(tradeData['balance'][-1])
                if (
                    amount < 0
                    or self.data['db']['balance'] < amount
                ):
                    raise ValueError 
            except ValueError:
                raise UserError('cantTrade')
            
            roundBal = amount - (amount % self.conf['game']['trade']['toScraps'])
            addScraps = roundBal // self.conf['game']['trade']['toScraps']
            
            self.editDB = True
            self.data['db']['balance'] -= roundBal
            self.data['db']['scraps'] += addScraps
            
            convertFrom, convertTo = botUtils.formatStats({'balance': roundBal, 'scraps': addScraps})

        elif 'scraps' in tradeData:
            try:
                amount = int(tradeData['scraps'][-1])
                if (
                    amount < 0
                    or self.data['db']['scraps'] < amount
                ):
                    raise ValueError 
            except ValueError:
                raise UserError('cantTrade')

            self.editDB = True
            addBalance = amount * self.conf['game']['trade']['toBalance']
            self.data['db']['balance'] += addBalance
            self.data['db']['scraps'] -= amount
            
            convertFrom, convertTo = botUtils.formatStats({'scraps': amount, 'balance': addBalance})
            
            
        else:
            raise UserError('cantTrade')
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data['vk']['peer_id'],
                'trade',
                convertFrom = convertFrom,
                convertTo = convertTo
            )
        )
        
    def updateConf(self, _):
        self.conf.updateConf()
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data['vk']['peer_id'],
                'updateConf'
            )
        )
    
    def topExp(self, count):
        if (
            not count
            or not count[-1].isdecimal()
        ):
            count = None
 
        users = sorted(
            [
                user
                for user in self.db.get(columns = ['id', 'experience'])
                if user['experience'] > 0
            ],
            key = itemgetter('experience'),
            reverse=True
        )
        
        if count:
            users = users[:int(count[-1])]


        users = [
            (place + 1, user, exp)
            
            for place, (user, exp) in enumerate(
                zip(
                    self.conf.vk.getUsernames(
                        ','.join(map(str, [users['id'] for users in users])),
                    ),
                    ['{} ({})'.format(
                        users['experience'],
                        self.conf.rank.getStatus(users)
                    ) for users in users] 
                ) 
            ) 
        ]
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data['vk']['peer_id'],
                'topExp',
                topExp = '\n'.join([
                    '{}. {} - {}'.format(*user)
                    for user in users
                ])
            )
        )
        
    def __init__(self, conf: config, data: dict = None, payload: list[dict] = None, db: DB = None, _game = None):
        self.conf = conf
        self.db = db
        self._game = _game
        self.editDB = False

        self.data = data
        self.payload = payload
        
        
        if not isinstance(self.payload, list): return 
        
        for func in self.payload:
            if not func: continue
            
            for key, val in func.items():
                method = getattr(self, key, None)
                if method is None: continue

                method(val)