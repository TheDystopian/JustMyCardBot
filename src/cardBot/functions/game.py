from threading import Timer
from backend.db import DB
from functions.card_utils import botUtils

from functions.functions import generalFunctions
from dataclasses import dataclass, field
from enum import Enum
from random import choice, randrange

import components.config as config

class role(Enum):
    """Player roles"""
    judge = ('Судья', 'judge')
    player = ("Игрок", 'player')
    
    def __init__(self, title, id):
        self.title = title
        self.id = id  

class lobby_status(Enum):
    """Lobby statuses"""
    active = ("Идет игра")
    full = ("Полное. Ожидание готовности")
    free = ("Есть места")

    def __init__(self, title):
        self.title = title

@dataclass
class player:
    id: int
    role: role 
    ready: bool = False 
      
@dataclass
class lobby:
    timeoutTask: Timer = None
    players: list[player] = field(default_factory=lambda:[])
    lobbyStatus: lobby_status = lobby_status.free
    
    def getPlayersByRole(self, role: role) -> player:
        return [player for player in self.players if player.role is role]
    
    def getPlayerIDs(self, *, exclude: int = None): 
        return [player.id for player in self.players if player.id != exclude]
    
    def getPlayerByID(self, id: int) -> player:
        return next((
            player
            for player in self.players
            if player.id == id
        ), None)
    
    def timeout(self, config: config, lobbyStorage: list):
        db = config.DBConn()
    
        for player in self.players:
            playerData = db.get(player.id)
            
            if player.ready:
               config.vk.send(config.dialogs.getDialogPlain(userid=player.id, preset = 'AFKcomp'))
               playerData['balance'] += config['lobby']['AFK']['compensation']
               if player.role == role.player:
                   playerData['battles'] += 1
            else:
                config.vk.send(config.dialogs.getDialogPlain(userid=player.id, preset = 'AFKpun'))
                playerData['balance'] -= config['lobby']['AFK']['punish']
                
            db.edit(playerData)
                
        lobbyStorage.remove(self) 
     
class game:
    def __init__(self, conf: config, db: DB):
        self.conf = conf
        self.db = db
        self.lobbies: list[lobby] = []
    
    def addToLobby(self, id: int, role: role):
        freeLobby = next(
            (lobby for lobby in self.lobbies 
            if lobby.lobbyStatus is lobby_status.free
            and len([
                player for player in lobby.players
                if player.role is role
                ]) 
            < self.conf['lobby']['maxPlayers'][role.id]), 
            None)
        
        self.conf.vk.send(self.conf.dialogs.getDialogPlain(userid=id, preset = 'lobbySearch'))
        
        if freeLobby is None:
            self.lobbies.append(
                lobby(
                    players = [player(id = id, role = role)], 
                ))
            return
        
        freeLobby.players.append(player(id = id, role = role))
        if len(freeLobby.players) == sum(self.conf['lobby']['maxPlayers'].values()):
            self.readyLobby(freeLobby)
            
    def readyLobby(self, lobby: lobby):
        self.conf.vk.send(
        self.conf.dialogs.getDialogPlain(userid=','.join(map(str, lobby.getPlayerIDs())), preset = 'lobbyReady')
        ) 

        lobby.status = lobby_status.full
        for player in [player for player in lobby.players if player.role is not role.judge]:
            plr = self.db.get(player.id)
            plr['battles'] -= 1
            self.db.edit(plr)
        
        lobby.timeoutTask = Timer(
            self.conf['lobby'].get('timeout',60), 
            lobby.timeout,
            args = (
                self.conf,
                self.lobbies
            )
        )
        lobby.timeoutTask.start()

    def setReadiness(self, id, *, lobby: lobby = None):
        if lobby is None:
            lobby = self.findLobby(id)
            if lobby is None: return
        
        player = next((player for player in lobby.players if id == player.id), None)
        if player is None: return
        
        player.ready = True
        if all(player.ready for player in lobby.players):
            self.allReady(lobby)
        
    def allReady(self, lobby: lobby):
        lobby.timeoutTask.cancel()
        
        self.conf.vk.send(
        self.conf.dialogs.getDialogPlain(userid=','.join(map(str, lobby.getPlayerIDs())), preset = 'lobbyActive')
        )

        lobby.lobbyStatus = lobby_status.active
    
    def deletePlayer(self, id: int, *, lobby: lobby = None):
        if lobby is None:
            lobby = self.findLobby(id)
            if lobby is None: return
        try: 
            lobby.players.remove(
                next(
                    (player for player in lobby.players
                     if player.id == id)
                    )
                )
        finally:
            pass
        
    def findLobby(self, id: int):
        return next((
            lobby for lobby in self.lobbies 
            if id in lobby.getPlayerIDs()
        ), None)

class gameFunctions(generalFunctions):
    def game(self, role, data):
        if (
            self.lobby.lobbyStatus is not lobby_status.free
        ): return
        
        if "ready" in role:
            self._game.setReadiness(
                data['db']['id'],
                lobby = self.lobby
            )
        
        elif "stop" in role:
            self._game.deletePlayer(data['db']['id'], lobby = self.lobby)
            
            self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    data['vk']['user'],
                    preset = 'stopLobbySearch'

                )
            )

    def flip(self, *_):
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                ','.join(map(str, self.lobby.getPlayerIDs())),
                preset = choice(["firstPlayer", "secondPlayer"])
            )
        )
    
    def chance(self, chance, _):
        if not chance: 
            raise NotImplementedError('cantError')
        
        if chance[-1] not in map(str, range(0, 101)):
            raise IndexError('wrongNumber')
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                ','.join(map(str, lobby.getPlayerIDs())),
                text = 'Успешно' 
                    if randrange(1, 101) <= int(chance[0])
                    else 'Не успешно'
            )
        )
        
    def win(self, playerIDx, data):        
        if (
            self.lobby.lobbyStatus is not lobby_status.active 
            or self.lobby.getPlayerByID(data['db']['id']).role is not role.judge
            or not playerIDx
            or not playerIDx[-1].isdecimal()  
        ): return
        
        playerWinner = int(playerIDx[-1])-1
        players = [self.db.get(i.id) for i in self.lobby.getPlayersByRole(role.player)]

        for playeridx, player in enumerate(players):            
            if playeridx == playerWinner:
                self.conf.rank.win(player)
                
                botUtils.changeStats(
                    player,
                    self.conf['status']['battles']['win'][player['status']] | {'wins': 1}
                )
                
                formatted = botUtils.formatStats(self.conf['status']['battles']['win'][player['status']])
                
                self.conf.vk.send(
                    self.conf.dialogs.getDialogPlain(
                        player['id'],
                        text = f'Вы выиграли. Вы получаете {formatted[0]} и {formatted[1]}'
                    )  
                )
                
                
                if not player['wins'] % self.conf['status']['streak']['count']['win'][player['status']]:
                    formatted = botUtils.formatStats(
                        self.conf['status']['streak']['reward']['win'][player['status']]
                    )
                    botUtils.changeStats(
                        player,
                        self.conf['status']['streak']['reward']['win'][player['status']] 
                    )
                    
                    self.conf.vk.send(
                        self.conf.dialogs.getDialogPlain(
                            player['id'],
                            text = f'Вы получаете {formatted[0]} за ваш винстрик'
                            
                        )  
                    )
                
                
                self.db.edit(player)
                continue
        
            self.conf.rank.lose(player)
            
            botUtils.changeStats(
                player,
                self.conf['status']['battles']['lose'][player['status']] | {'loses': 1}
            )
            
            formatted = botUtils.formatStats(self.conf['status']['battles']['lose'][player['status']])
            
            self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    player['id'],
                    text = f'Вы проиграли. Вы получаете {formatted[0]}'
                )
            )
            
            if not player['loses'] % self.conf['status']['streak']['count']['lose'][player['status']]:
                formatted = botUtils.formatStats(
                    self.conf['status']['streak']['reward']['lose'][player['status']]
                )
                botUtils.changeStats(
                    player,
                    self.conf['status']['streak']['reward']['lose'][player['status']] 
                )
                
                self.conf.vk.send(
                    self.conf.dialogs.getDialogPlain(
                        player['id'],
                        text = f'Вы получаете {formatted[0]} за ваш лузстрик'
                        
                    )  
                )
            
            
            self.db.edit(player)
        
        self.editDB = True
        botUtils.changeStats(
            data['db'],
            self.conf['status']['battles']['judge'][data['db']['status']] | {'judge': 1}
        )
        
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                data['vk']['user'],
                text = f"Вы получаете {botUtils.formatStats(self.conf['status']['battles']['judge'][data['db']['status']])[0]} за судейство"
            )
        )
        
        if not data['db']['judge'] % self.conf['status']['streak']['count']['judge'][data['db']['status']]:
            formatted = botUtils.formatStats(
                self.conf['status']['streak']['reward']['judge'][data['db']['status']]
            )
            
            botUtils.changeStats(
                data['db'],
                self.conf['status']['streak']['reward']['judge'][data['db']['status']] 
            )
            
            self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    data['db']['id'],
                    text = f'Вы получаете {formatted[0]} за активное судейство'
                    
                )  
            )
        
        
        self._game.lobbies.remove(self.lobby)
        
    def __init__(self,conf: config, lobby:lobby = None, data = None, payload = None, db = None, game: game = None):
        super().__init__(conf, db = db)
        
        self.lobby = lobby
        self._game = game
        
        if None in payload:
            playerID = data["db"]["id"]
            if playerID != data['vk']['peer_id']: return
            playerList = [player.id for player in lobby.getPlayersByRole(role.player)]
            
            try:
                playerType = f'Игрок {playerList.index(data["db"]["id"]) + 1}'
            except ValueError:
                playerType = 'Судья'
            
            recepients = ','.join(map(str, lobby.getPlayerIDs(exclude = playerID)))
            if not recepients: return
            
            
            self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    recepients,
                    text = f'''
                    {playerType}:\n{data['vk']['text']}
                    '''
                ),
                attachments=data['vk']['attachments'],
                sendSeparately=False
            )
            return
        if not isinstance(payload, list): return 
        
        for func in payload:
            for key, val in func.items():
                method = getattr(self, key, None)
                if method is None: continue
                
                
                try:
                    method(val, data)
                except Exception as e:
                    self.conf.vk.send(
                        self.conf.dialogs.getDialogPlain(
                            data['vk']['peer_id'],
                            preset=e.args
                        )
                    )