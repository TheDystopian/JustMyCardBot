from typing import Iterable
from functions.card_utils import botUtils
from json import dumps
from time import time


class dialog:
    def __init__(self, conf):
        self.conf = conf

    def __composePayload(self, keyboard: dict):
        if (
            not keyboard
            or not keyboard.get("buttons")
            and not isinstance(keyboard["buttons"], Iterable)
        ):
            return
        for y in keyboard["buttons"]:
            for x in y:
                x["action"]["payload"] = (
                    dumps(x["action"]["payload"]).replace("\\", "").strip('"')
                )

        return keyboard

    def getDialogPlain(
        self,
        userid: int | str,
        *,
        preset: list | str = ["error"],
        text: str = None,
        script: str = None,
    ):
        if not isinstance(preset, (list, tuple)):
            preset = [preset]
        keyboard = (
            self.__composePayload(
                self.conf["dialogs"].get(preset[-1], {}).get("keyboard")
            )
            if not script
            else script
        )

        return {
            "id": userid,
            "message": [text]
            if text is not None
            else [self.conf["dialogs"].get(p, {}).get("message", p) for p in preset],
            "keyboard": dumps(keyboard) if keyboard else None,
        }

    def getDialogParsed(
        self,
        receiverID: int | str,
        preset: str | list = ["error"],
        *,
        userdata: dict = None,
        selectCard: int | list = None,
        **kwargs,
    ):
        if userdata is None:
            userdata = dict()
        if not isinstance(preset, list):
            preset = [preset]
        keyboard = self.__composePayload(
            self.conf["dialogs"][preset[-1]].get("keyboard")
        )

        return {
            "id": receiverID,
            "message": [
                self.conf["dialogs"]
                .get(msg, "error")
                .get("message", "DIALOG_PLACEHOLDER")
                .format(
                    card="\n".join(
                        [
                            botUtils.formatCards(card)
                            for card in self.conf.cards.getOwnedCards(
                                userdata.get("cards", []), select=selectCard
                            )
                        ]
                    ),
                    status=self.conf["status"]["status"][userdata.get("status", 0)][
                        "name"
                    ],
                    statusDays=generateStatusDays(userdata),
                    balance=userdata.get("balance", 0),
                    scraps=userdata.get("scraps", 0),
                    battles=userdata.get("battles", 0),
                    packs=userdata.get("packs", [0, 0, 0, 0]),
                    rank=f'{self.conf.rank.getStatus(userdata)} ({userdata.get("experience", 0)})',
                    key=kwargs,
                )
                for msg in preset
            ],
            "keyboard": dumps(keyboard) if keyboard else None,
        }


def generateStatusDays(data):
    if data is None or not data.get("status"):
        return ""

    statusDays = data["day"] - int(time() // 86400)

    return "({})".format(
        f'{statusDays} {"день" if statusDays % 10 == 1 else "дня" if statusDays % 10 < 5 and statusDays % 10 >= 2 else "дней"}'
    )
