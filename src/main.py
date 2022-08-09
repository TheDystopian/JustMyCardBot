import logging
from multiprocessing import Process
from os.path import dirname, join
from yaml import safe_load

from assets.dialog import dialog
from assets.rank import rank
from assets.cards import cards

from backend.db import DB
from backend.vk import VK
import bot
from scheduled import scheduled

class config:
    def __init__(self, file = 'config.yaml'):
        logging.basicConfig(format="[CONFIG:%(levelname)s] %(message)s")
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.INFO)
        
        self.log.info('Loading config...')
        
        file = join(dirname(__file__), file)
        
        with open(
            file,
            'r',
            encoding= 'utf-8'
        ) as f:
            self.log.info(f'Found config at {file}')
            self.__conf = safe_load(f)
        
        self.conf = {k: v for k, v in  self.__conf.items() if k not in {'DB', 'VK'}}
        
        self.cards = cards(self)
        self.rank = rank(self)
        self.dialogs = dialog(self)
        self.vk = VK(self.__conf['VK'])
        
        self.log.info('Config Loaded')
        
    def DBConn(self) -> DB:
        self.log.info('New DB Connection')
        return DB(self.__conf['DB'])
    
    def __getitem__(self, item):
        return self.conf.get(item)
    
if __name__ == '__main__':
    conf = config()
    
    processes = [
        Process(target = bot.Bot, args = (conf,), name = 'Main bot'),
        Process(target = scheduled, args = (conf,), name = 'Schedule process')
    ]
    
    [p.start() for p in processes]
    [p.join() for p in processes]