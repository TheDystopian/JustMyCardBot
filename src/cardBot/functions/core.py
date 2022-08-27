from json import loads
from functions.game import gameFunctions
from functions.functions import generalFunctions


class dictRecursive:
    def get(_dict):
        if not isinstance(_dict, dict):
            return _dict
        return dictRecursive.get(next(iter(_dict.values())))

    def set(_dict, val):
        if not isinstance(_dict, dict):
            _dict.append(val)
            return _dict
        return {
            next(iter(_dict.keys())): dictRecursive.set(next(iter(_dict.values())), val)
        }


class core:
    def __init__(self, parent):
        self.config = parent.conf
        self.db = parent.db
        self.game = parent.game

        self.__commands = []
        for key, val in self.config["commands"]["commands"].items():
            self.__commands.append([key] + [kw.lower() for kw in val["keywords"]])

        self.__args = []
        for key, val in self.config["commands"]["args"].items():
            self.__args.append([key] + [kw.lower() for kw in val["keywords"]])

    def messageState(self, data: dict):
        return {
            "isChat": data["user"] != data["peer_id"],
            "isAdmin": self.config.vk.isAdmin(data["peer_id"], data["user"]),
            "lobby": self.game.findLobby(data["user"]),
        }

    def checkPermissions(self, permissions: list, data: dict) -> bool:
        return not (
            not data["isAdmin"]
            and "admins" in permissions
            or not data["isChat"]
            and not "bot" in permissions
            or data["isChat"]
            and not "chat" in permissions
        )

    def textRecognition(self, data: dict):
        if (
            len(data['vk']["text"]) < 2
            or not data['vk']["text"][0] in self.config["commands"]["call"]
        ):
            return
        payload = []

        for command in data['vk']["text"].lower().split():
            try:
                isCommand = command[0] in self.config["commands"]["call"]

                if isCommand:
                    key = next(
                        (kw[0] for kw in self.__commands if command[1:] in kw), None
                    )
                    if not key:
                        continue

                    command = self.config["commands"]["commands"][key]

                    assert self.checkPermissions(
                        command["permissions"], data
                    ), "cantError"

                    payload.append(command.get("payload", {key: []}))
                    continue

                if not payload:
                    continue
                
                arg = next((arg[0] for arg in self.__args if command in arg), None)

                if arg:
                    payload[-1][list(payload[-1].keys())[-1]] = {arg: []}
                    continue

                dictRecursive.set(payload[-1], command)

            except AssertionError as preset:
                self.config.vk.send(
                    self.config.dialogs.getDialogPlain(
                        data['vk']["peer_id"], preset=preset.args
                    )
                )
                continue

        return payload

    def core(self, data):
        payload = data["payload"]
        if isinstance(payload, str):
            payload = loads(payload.replace("\\", "").strip('"'))
        
        data = {'vk': data} | self.messageState(data)

        if payload is None:
            payload = self.textRecognition(data)
            if not payload and not data["lobby"]:
                return

        if not isinstance(payload, (list, tuple)):
            payload = [payload]

        data['vk'].pop('payload')
        data = data | {'db': self.db.get(user=data['vk']["user"]), 'payload': payload}

        if not data["db"]:
            if data["vk"]["peer_id"] != data["vk"]["user"]:
                return

            self.db.add(data["vk"]["user"])
            self.config.vk.send(
                self.config.dialogs.getDialogPlain(
                    data["vk"]["user"], preset=["greeting"]
                )
            )
            return

        try:
            func = (
                generalFunctions(self.config, data, self.db, self.game)
                if data['isChat'] or not data['lobby']                
                else gameFunctions(
                    self.config, data, self.db, self.game
                )
            )

            if func.editDB:
                self.db.edit(data["db"])

        except AssertionError as preset:
            self.config.vk.send(
                self.config.dialogs.getDialogPlain(
                    data["vk"]["peer_id"], preset=preset.args
                )
            )
