import logging

from os.path import dirname, join
from yaml import safe_load
from os import getenv

import backend

class config:
    def __init__(self, conf = '../config.yaml', creds = '../creds.yaml'):
        logging.basicConfig(format="[%(levelname)s] %(message)s")
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.INFO)
        
        self.log.info('Loading config...')
        
        conf = join(dirname(__file__), conf)
        creds = join(dirname(__file__), creds)
        
        with open(conf, 'r', encoding= 'utf-8') as f:
            self.log.info(f'Found config at {conf}')
            self.conf = safe_load(f)
            
            
        if getenv('BOT_CRED'):
            self.__creds = safe_load(getenv('BOT_CRED'))
        
        else:
            with open(creds,'r',encoding= 'utf-8') as f:
                self.log.info(f'Found login data at {creds}')
                self.__creds = safe_load(f)   
            
            
            
            
        import assets
        self.cards = assets.cards(self)
        self.rank = assets.rank(self)
        self.dialogs = assets.dialog(self)
        self.vk = backend.VK(self.__creds['VK'])
        
        self.log.info('Config Loaded')
        
    def DBConn(self) -> backend.DB:
        self.log.info('New DB Connection')
        return backend.DB(self.__creds['DB'])
    
    def __getitem__(self, item):
        return self.conf.get(item)
