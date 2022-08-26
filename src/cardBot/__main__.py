from multiprocessing import Process
import components.bot as bot
import components.scheduled as scheduled
import components.config as config

conf = config()

processes = [
    Process(target=bot.Bot, args=(conf,), name="Main bot"),
    Process(target=scheduled, args=(conf,), name="Schedule process"),
]

[p.start() for p in processes]
[p.join() for p in processes]
