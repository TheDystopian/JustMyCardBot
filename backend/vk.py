import vk_api, yaml
from json import loads
from time import sleep
from vk_api import bot_longpoll
from os.path import dirname, join
from vk_api.utils import get_random_id
from requests.exceptions import ReadTimeout


class VK:
    def __init__(self, file="vk.yaml"):

        with open(join(dirname(__file__), "..", "configs", file), "r") as cfg:
            self.__cfg = yaml.safe_load(cfg)

        self.start()

    def start(self):
        self.__vk_session = vk_api.VkApi(
            token=self.__cfg["APIKey"], api_version="5.144"
        )
        self.__LP = bot_longpoll.VkBotLongPoll(
            self.__vk_session,
            self.__vk_session.method("groups.getById")["groups"][0]["id"],
        )

    def send(self, sendable=None, attachments=None, sendSeparately=True):
        if attachments is not None:
            if sendSeparately:
                [
                    self.__vk_session.method(
                        "messages.send",
                        {
                            "attachment": atch,
                            "user_id": sendable.get("id"),
                            "random_id": get_random_id(),
                            "peer_ids": sendable.get("peer_id"),
                            "message": sendable.get("message"),
                        },
                    )
                    for atch in attachments
                ]
            else:
                self.__vk_session.method(
                    "messages.send",
                    {
                        "attachment": ",".join(attachments),
                        "user_id": sendable.get("id"),
                        "random_id": get_random_id(),
                        "peer_ids": sendable.get("peer_id"),
                        "message": sendable.get("message"),
                    },
                )

        else:
            if not isinstance(sendable["message"], list):
                sendable["message"] = [sendable["message"]]

            for msg in sendable["message"]:
                self.__vk_session.method(
                    "messages.send",
                    {
                        "message": msg,
                        "user_id": sendable.get("id"),
                        "random_id": get_random_id(),
                        "keyboard": sendable.get("keyboard"),
                        "peer_ids": sendable.get("peer_id"),
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
                            "attachments": [
                                f'{i["type"]}{i[i["type"]].get("owner_id")}_{i[i["type"]].get("id")}{ ("_" + i[i["type"]].get("access_key")) if i[i["type"]].get("access_key") is not None else ""  }'
                                for i in event.message.attachments
                            ],
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
            except ReadTimeout:
                sleep(10)

    def sendTo(self, msg, category):
        for admin in self.__cfg[category]:
            self.send(sendable={"id": admin, "message": msg})

    def isAdmin(self, peer, user):
        return user in {*self.__cfg["admins"], *self.__cfg["devs"]} or next(
            (
                i.get("is_admin")
                for i in self.__vk_session.method(
                    "messages.getConversationMembers", {"peer_id": peer}
                )["items"]
                if i["member_id"] == user
            ),
            False,
        )
