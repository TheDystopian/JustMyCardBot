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

    def checkPermissions(self, permissions: list, state: dict):
        return not (
            not state["isAdmin"]
            and "admins" in permissions
            or not state["isChat"]
            and not "bot" in permissions
            or state["isChat"]
            and not "chat" in permissions
        )

    def textRecognition(self, data: dict, state: dict):
        if (
            len(data["text"]) < 2
            or not data["text"][0] in self.config["commands"]["call"]
        ):
            return
        payload = []

        for command in data["text"].lower().split():
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
                        command["permissions"], state
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
                        data["peer_id"], preset=preset.args
                    )
                )
                continue

        return payload

    def core(self, data):
        payload = data["payload"]
        state = self.messageState(data)

        if isinstance(payload, str):
            payload = loads(payload.replace("\\", "").strip('"'))

        if payload is None:
            payload = self.textRecognition(data, state)
            if not payload and not state["lobby"]:
                return

        if not isinstance(payload, (list, tuple)):
            payload = [payload]

        data = {"vk": data, "db": self.db.get(user=data["user"])}

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
                generalFunctions(self.config, data, payload, self.db, self.game)
                if not state["lobby"] or state["isChat"]
                else gameFunctions(
                    self.config, state["lobby"], data, payload, self.db, self.game
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
