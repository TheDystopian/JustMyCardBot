import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from time import time


sched = BlockingScheduler()

class scheduled:
    def event1(self):
        self.log.info("Event 1 triggered") 
        
        
        for user in self.DB.get():
            user['battles'] = self.conf['status']['battles']['count'][user['status']]
            user["loses"] = user["wins"] = user["judge"] = 0
            
            if user["status"] and user["day"] - time() // 86400 == 1:
                self.conf.vk.send(
                    {
                        "message": f'Ваш статус {self.conf["status"]["names"][user["status"]]} заканчивается. Для пополнения напишите в администрацию',
                        "id": user["id"],
                    }
                )
            
            
            if user["status"] and user["day"] - time() // 86400 <= 0:
                self.conf.vk.send(
                    {
                        "message": f'Ваш статус {self.conf["status"]["names"][user["status"]]} истек. Для пополнения напишите в администрацию',
                        "id": user["id"],
                    }
                )
                user["status"] = 0
                
            self.DB.edit(user)

    def event2(self):
        self.log.info("Event 2 triggered")
        
        def giveRewards(user, whatToGive):
            def balance(amount):
                user["balance"] += amount

            def scraps(amount):
                user["scraps"] += amount

            def cardPack(packs):
                for pack in packs:
                    user["packs"][pack] += 1

            def card(cardData):
                user["cards"].append(
                    self.conf.cards.getCardByRarity(
                        chances={str(cardData.get("rarity", 1)): 100},
                        level=cardData.get("level", 1),
                    )
                )
                
            for i in whatToGive:
                for j, k in i.items():
                    locals()[j](k)
            return user

        for user in self.DB.get():
            levels ={
                int(level): levelInfo
                for level, levelInfo in self.conf['ranks']['levels'].items()
                if int(level) <= user["experience"]
            }
            
            user = giveRewards(user, [i["reward"] for i in levels.values()])
            
            user["experience"] = (
                list(levels.keys())[-2] if len(levels.keys()) >= 2 else 0
            )

            self.DB.edit(user)

    def __init__(self, conf):
        self.conf = conf
        logging.basicConfig(format="[SCHED:%(levelname)s] %(message)s")
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        
        self.DB = conf.DBConn()

        sched.add_job(self.event1, CronTrigger.from_crontab('0 12 * * *'))
        sched.add_job(self.event2, CronTrigger.from_crontab('0 0 */14 * *'))