from threading import Thread
from backend.db import DB
from functions.card_utils import botUtils

from functions.functions import generalFunctions
from dataclasses import dataclass, field
from enum import Enum
from random import choice, random, randrange

import components.config as config
from time import time


class role(Enum):
    """Player roles"""

    judge = ("Судья", "judge")
    player = ("Игрок", "player")

    def __init__(self, title, id):
        self.title = title
        self.id = id


class lobby_status(Enum):
    """Lobby statuses"""

    active = "Идет игра"
    free = "Ожидание"

    def __init__(self, title):
        self.title = title


@dataclass
class player:
    id: int
    role: role
    reward: bool = True
    lastActivity: int = None
    


@dataclass
class lobby:
    timeoutTask: Thread = None
    players: list[player] = field(default_factory=lambda: [])
    lobbyStatus: lobby_status = lobby_status.free
    lobbyStorage: list = None

    def getPlayersByRole(self, role: role) -> list[player]:
        return [player for player in self.players if player.role is role]

    def getPlayerIDs(self, *, exclude: int = None):
        return [player.id for player in self.players if player.id != exclude]

    def getPlayerByID(self, id: int) -> player:
        return next((player for player in self.players if player.id == id), None)

    def timeout(self, conf: config):
        # Operate

        while True:
            if getattr(self, "kill", False):
                return

            if any(
                time() - player.lastActivity > conf["lobby"].get("timeout", 60)
                for player in self.players
            ):
                break

        db = conf.DBConn()

        for player in self.players:
            playerData = db.get(player.id)

            if time() - player.lastActivity > conf["lobby"].get("timeout", 60):
                conf.vk.send(
                    conf.dialogs.getDialogPlain(userid=player.id, preset="AFKpun")
                )
                playerData["balance"] -= conf["lobby"]["AFK"]["punish"]
                if player.role is role.player and player.reward:
                    playerData["battles"] -= 1
            else:
                conf.vk.send(
                    conf.dialogs.getDialogPlain(userid=player.id, preset="AFKcomp")
                )
                playerData["balance"] += conf["lobby"]["AFK"]["compensation"]

            db.edit(playerData)

        self.killLobby()

    def killLobby(self):
        self.kill = True
        self.lobbyStorage.remove(self)


class game:
    lobbies: list[lobby] = []

    def __init__(self, conf: config, db: DB):
        self.conf = conf
        self.db = db

    def addToLobby(self, id: int, role: role, reward: bool = True):
        freeLobby = next(
            (
                lobby
                for lobby in self.lobbies
                if lobby.lobbyStatus is lobby_status.free
                and len([player for player in lobby.players if player.role is role])
                < self.conf["lobby"]["maxPlayers"][role.id]
            ),
            None,
        )

        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(userid=id, preset="lobbySearch")
        )

        if freeLobby is None:
            self.lobbies.append(
                lobby(
                    players=[
                        player(id=id, role=role, reward = reward)
                    ], 
                    lobbyStorage=self.lobbies)
            )
            return

        freeLobby.players.append(player(id=id, role=role, reward = reward))
        if len(freeLobby.players) == sum(self.conf["lobby"]["maxPlayers"].values()):
            self.readyLobby(freeLobby)

    def readyLobby(self, lobby: lobby):
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                userid=",".join(map(str, lobby.getPlayerIDs())), preset="lobbyReady"
            )
        )

        lobby.lobbyStatus = lobby_status.active
        for player in lobby.players:
            player.lastActivity = time()

        lobby.timeoutTask = Thread(target=lobby.timeout, args=(self.conf,), daemon=True)
        lobby.timeoutTask.start()

    def deletePlayer(self, id: int, *, lobby: lobby = None):
        if lobby is None:
            lobby = self.findLobby(id)
            if lobby is None:
                return
        try:
            lobby.players.remove(
                next((player for player in lobby.players if player.id == id))
            )
        finally:
            pass

    def findLobby(self, id: int):
        return next(
            (lobby for lobby in self.lobbies if id in lobby.getPlayerIDs()), None
        )


class gameFunctions(generalFunctions):
    def game(self, role):
        if self.data['lobby'].lobbyStatus is not lobby_status.free:
            return

        elif "stop" in role:
            self._game.deletePlayer(self.data["db"]["id"], lobby=self.data['lobby'])

            self.conf.vk.send(
                self.conf.dialogs.getDialogPlain(
                    self.data["vk"]["user"], preset="stopLobbySearch"
                )
            )

    def ready(self, _):
        playerType = self.__getplayer(self.data['lobby'].getPlayersByRole(role.player))

        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                ",".join(
                    map(str, self.data['lobby'].getPlayerIDs(exclude=self.data["db"]["id"]))
                ),
                text="{} {}".format(playerType, "готов"),
            )
        )

    def actions(self, _):
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                self.data["vk"]["user"], preset=f"{self.player.role.id}Actions"
            )
        )

    def profile(self, _):
        if (
            self.data['isChat']
            or self.data["vk"]["reply_id"]
        ):
            return super().profile(None)

        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                self.data["vk"]["user"]
                if self.data["vk"]["reply_id"] != self.data["vk"]["user"]
                else self.data["vk"]["peer_id"],
                "profile_game",
                userdata=self.data["db"],
                role=self.player.role.title,
                lobbyStatus=self.data['lobby'].lobbyStatus.title,
            )
        )

    def flip(self, _):
        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                ",".join(map(str, self.data['lobby'].getPlayerIDs())),
                preset=choice(["firstPlayer", "secondPlayer"]),
            )
        )

    def chance(self, chance):
        assert chance, "cantError"

        assert chance[-1].replace(".", "", 1).isdecimal(), "wrongNumber"

        chance = float(chance[-1])

        assert chance > 0 and chance < 100, "wrongNumber"

        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                ",".join(map(str, self.data['lobby'].getPlayerIDs())),
                text=f'Шанс {chance}% - {"Успешно" if random() * 100 <= chance else "Не успешно"}',
            )
        )

    def showCards(self, cards):
        if (
            not cards
            or not isinstance(cards, list)
            or self.data['lobby'].lobbyStatus is not lobby_status.active
        ):
            return super().showCards(cards)

        recepients = ",".join(
            map(str, self.data['lobby'].getPlayerIDs(exclude=self.data["db"]["id"]))
        )
        if not recepients:
            return super().showCards(cards)

        try:
            cardLevel = int(cards[-1])
            cards = cards[:-1]
        except ValueError:
            cardLevel = 1

        cardData = self.conf.cards.getOwnedCards(self.data["db"]["cards"])

        cardData = [
            card
            for card in cardData
            if card["name"].lower().find(" ".join(cards)) != -1
            and card["level"] == cardLevel
        ]
        assert cardData, "noCards"

        cardData = [
            card for cID, card in enumerate(cardData, 1) if card not in cardData[cID:]
        ]

        assert len(cardData) == 1, "undefinedCard"

        cardData = cardData[-1]

        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                self.data["vk"]["peer_id"],
                text=f"Вы походили картой {botUtils.formatCards(cardData, raritySymbol= False)}",
            ),
            attachments=cardData["attachment"],
            sendSeparately=False,
        )

        playerType = self.__getplayer(self.data['lobby'].getPlayersByRole(role.player))

        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                recepients,
                text=f"{playerType} походил картой {botUtils.formatCards(cardData, raritySymbol= False)}",
            ),
            attachments=cardData["attachment"],
            sendSeparately=False,
        )

    def win(self, playerIDx):
        if (
            self.data['lobby'].lobbyStatus is not lobby_status.active
            or self.player.role is not role.judge
            or not playerIDx
            or not playerIDx[-1].isdecimal()
        ):
            return

        playerWinner = int(playerIDx[-1])
        assert playerWinner in range(1, self.conf["lobby"]["maxPlayers"][role.player.id] + 1), 'incorrectPlayer'
        
        players = self.data['lobby'].getPlayersByRole(role.player)

        self.data['lobby'].killLobby()

        for playeridx, (player, playerDB) in enumerate(zip(players, [self.db.get(i.id) for i in players]), 1):
            playerStatus = "win" if playeridx == playerWinner else "lose"
            
            if player.reward:
                playerDB["battles"] -= 1
                self.__giveStat(playerDB, playerStatus)
                self.db.edit(playerDB)

            else:
                self.conf.vk.send(
                    self.conf.dialogs.getDialogParsed(
                    player.id,
                    preset=f"{playerStatus}NoRewardTemplate",
            )
        )


        self.editDB = True
        self.__giveStat(self.data["db"], "judge")

    def __giveStat(self, player, status):
        rank = getattr(self.conf.rank, status, None)
        if rank:
            rank(player)

        botUtils.changeStats(
            player,
            self.conf["status"]["status"][player["status"]]["battles"][status]
            | {status: 1},
        )

        self.conf.vk.send(
            self.conf.dialogs.getDialogParsed(
                player["id"],
                preset=f"{status}Template",
                formatStats=botUtils.formatStats(
                    self.conf["status"]["status"][player["status"]]["battles"][status]
                ),
            )
        )

        if (
            not player[status]
            % self.conf["status"]["status"][player["status"]]["streak"][status]["count"]
        ):
            botUtils.changeStats(
                player,
                self.conf["status"]["status"][player["status"]]["streak"][status][
                    "reward"
                ],
            )

            self.conf.vk.send(
                self.conf.dialogs.getDialogParsed(
                    player["id"],
                    preset=f"{status}TemplateStreak",
                    formatStats=botUtils.formatStats(
                        self.conf["status"]["status"][player["status"]]["streak"][
                            status
                        ]["reward"]
                    ),
                )
            )

    def __chat(self, data):
        if not data["vk"]["text"] and not data["vk"]["attachments"]:
            return

        recepients = ",".join(
            map(str, data['lobby'].getPlayerIDs(exclude=data["db"]["id"]))
        )
        if not recepients:
            return

        playerType = self.__getplayer(data['lobby'].getPlayersByRole(role.player))

        self.conf.vk.send(
            self.conf.dialogs.getDialogPlain(
                recepients, text="{}:\n{}".format(playerType, data["vk"]["text"])
            ),
            attachments=data["vk"]["attachments"],
            sendSeparately=False,
        )

    def __init__(
        self,
        conf: config,
        data: dict=None,
        db=None,
        game: game = None,
    ):
        self.conf = conf
        self.editDB = False
        self.player = data['lobby'].getPlayerByID(data["db"]["id"])

        if data['lobby'].lobbyStatus is not lobby_status.free:
            self.player.lastActivity = time()

        if (
            None in data.get('payload') or 
            "ready" in data.get('payload')
            or not isinstance(data.get('payload'), list)
        ):
            return self.__chat(data)

        super().__init__(conf, data, db, game)

    def __getplayer(self, playerList):
        try:
            return f"{role.player.title} {playerList.index(self.player) + 1}"
        except ValueError:
            return role.judge.title
