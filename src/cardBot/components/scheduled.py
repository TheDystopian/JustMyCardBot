from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from time import time
import components.config as config


sched = BlockingScheduler()

class scheduled:
    def event1(self):
        self.conf.log.info("Event 1 triggered") 
        
        
        for user in self.DB.get():
            user['battles'] = self.conf['status']['status'][user['status']]['battles']['count']
            user["loses"] = user["wins"] = user["judge"] = 0
            
            if user["status"] and user["day"] - time() // 86400 <= 0:
                self.conf.vk.send(
                    self.conf.dialogs.getDialogParsed(
                        user["id"],
                        'statusExpire',
                        userdata = user
                    )
                )
                user["status"] = 0
                
            self.DB.edit(user)

    def event2(self):
        self.conf.log.info("Event 2 triggered")
        
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

    def __init__(self, conf: config = None):
        self.conf = conf
        
        self.DB = conf.DBConn()

        sched.add_job(self.event1, 'cron', hour = 12, minute = 0)
        sched.add_job(self.event2, CronTrigger.from_crontab('0 12 1,18 * *'))
        
        sched.start()