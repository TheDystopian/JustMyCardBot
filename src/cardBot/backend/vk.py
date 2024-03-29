import vk_api
from json import loads
from time import sleep
from vk_api import bot_longpoll
from vk_api.utils import get_random_id
from requests.exceptions import ReadTimeout


class VK:
    def __init__(self, config):
        self.__cfg = config
        self.__vk_session = vk_api.VkApi(token=self.__cfg["key"], api_version="5.144")
        self.__LP = bot_longpoll.VkBotLongPoll(
            self.__vk_session,
            self.__vk_session.method("groups.getById")["groups"][0]["id"],
        )

    def send(self, sendable=None, attachments=None, sendSeparately=True):
        if attachments is not None:
            if not sendSeparately:
                attachments = [",".join(attachments)]

            [
                self.__vk_session.method(
                    "messages.send",
                    {
                        "attachment": atch,
                        "random_id": get_random_id(),
                        "peer_ids": sendable.get("id", ""),
                        "message": sendable.get("message"),
                        "disable_mentions": True,
                    },
                )
                for atch in attachments
            ]

        else:
            if not isinstance(sendable["message"], list):
                sendable["message"] = [sendable["message"]]

            for msg in sendable["message"]:
                self.__vk_session.method(
                    "messages.send",
                    {
                        "message": msg,
                        "random_id": get_random_id(),
                        "keyboard": sendable.get("keyboard"),
                        "peer_ids": sendable.get("id"),
                        "disable_mentions": True,
                    },
                )

    def wait(self):
        while True:
            try:
                for event in self.__LP.check():
                    # Events needed to be handled differently
                    # There is need to handle only MESSAGE_NEW and MESSAGE_EVENT as of now

                    if event.type == bot_longpoll.VkBotEventType.MESSAGE_NEW:
                        yield {
                            "user": event.message.from_id,
                            "payload": loads(event.message.payload)
                            if event.message.payload
                            else None,
                            "text": event.message.get("text"),
                            "peer_id": event.message.peer_id,
                            "reply_id": event.message.fwd_messages[0]["from_id"]
                            if event.message.fwd_messages
                            else event.message.get("reply_message", {}).get("from_id"),
                            "attachments": self.generateAttachments(
                                getattr(event.message, "attachments")
                            ),
                        }

                    if event.type == bot_longpoll.VkBotEventType.MESSAGE_EVENT:
                        self.__vk.messages.sendMessageEventAnswer(
                            event_id=event.obj.event_id,
                            user_id=event.obj.user_id,
                            peer_id=event.obj.peer_id,
                        )
                        yield {
                            "user": event.obj.user_id,
                            "payload": event.obj.payload,
                            "peer_id": event.obj.peer_id,
                        }
            except (ReadTimeout, ConnectionError):
                sleep(10)

    def sendTo(self, msg, category):
        for admin in self.__cfg["groups"][category]:
            self.send(sendable={"id": admin, "message": msg})

    def isAdmin(self, peer, user):
        return user in {
            *self.__cfg["groups"].get("admins", []),
            *self.__cfg["groups"].get("devs", []),
        } or next(
            (
                i.get("is_admin")
                for i in self.__vk_session.method(
                    "messages.getConversationMembers", {"peer_id": peer}
                )["items"]
                if i["member_id"] == user
            ),
            False,
        )

    def generateAttachments(self, attachments: list[dict]):
        return [
            atch["type"]
            + "_".join(
                map(
                    str,
                    filter(
                        None,
                        [
                            atch[atch["type"]].get("owner_id"),
                            atch[atch["type"]].get("id"),
                            atch[atch["type"]].get("access_key"),
                        ],
                    ),
                )
            )
            for atch in attachments
            if atch["type"] not in {"sticker"}
        ]

    def getUsernames(self, usernames: int | str):
        return [
            "[{}|{}]".format(
                name["screen_name"],
                " ".join([name.get("first_name", ""), name.get("last_name", "")]),
            )
            for name in self.__vk_session.method(
                "users.get", {"user_ids": usernames, "fields": "screen_name"}
            )
        ]
