class rank:
    def __init__(self, conf):
        self.conf = conf
        
    def lose(self, user):
        user["experience"] -= self.conf['ranks']['expChange'][
            next(
                j["expGroup"]
                for i, j in reversed(self.conf['ranks']['levels'].items())
                if user["experience"] >= int(i)
            )
        ]["lose"]
        if user["experience"] < 0:
            user["experience"] = 0

    def win(self, user):
        user["experience"] += self.conf['ranks']['expChange'][
            next(
                j["expGroup"]
                for i, j in reversed(self.conf['ranks']['levels'].items())
                if user["experience"] >= int(i)
            )
        ]["win"]

    def getStatus(self, user):
        if "experience" not in user: return 'INVALID_USER'
        return next(
            j["name"]
            for i, j in reversed(self.conf['ranks']['levels'].items())
            if user["experience"] >= int(i)
        )

    def rwin(self, user):
        for rank, rankInfo in reversed(
            self.conf['ranks']['levels'].items()
        ):
            if (
                user["experience"]
                < int(rank)
                - self.conf['ranks']['expChange'][rankInfo["expGroup"]]["win"]
            ):
                continue
            user["experience"] -= self.conf['ranks']['expChange'][
                rankInfo["expGroup"]
            ]["win"]
            return

    def rlose(self, user):
        for rank, rankInfo in reversed(
            self.conf['ranks']['levels'].items()
        ):
            if (
                user["experience"]
                < int(rank)
                + self.conf['ranks']['expChange'][rankInfo["expGroup"]]["lose"]
            ):
                continue
            user["experience"] += self.conf['ranks']['expChange'][
                rankInfo["expGroup"]
            ]["lose"]
            return
