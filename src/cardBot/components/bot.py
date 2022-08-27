from traceback import format_exc

import components.config as config

class Bot:
    def __init__(self, conf: config.config):
        self.conf = conf

        self.db = conf.DBConn()
        conf.log.info("Loaded backend")

        from functions.game import game
        self.game = game(conf, self.db)

        from functions.core import core
        self._coreCtl = core(self)

        conf.log.info("Core loaded")

        while True:
            data = dict()

            try:
                for data in conf.vk.wait():
                    conf.log.debug(f"[GET] {data}")
                    self._coreCtl.core(data)

            except Exception:
                conf.log.error(f"{format_exc()}\n\nDATA:{data}")
                conf.vk.sendTo(
                    f"[ERROR] {format_exc()}\n\nDATA:{data}",
                    "devs",
                )
