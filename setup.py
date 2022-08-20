#  _____ ____  ____  
# |_   _| __ )|  _ \ 
#   | | |  _ \| | | |
#   | | | |_) | |_| |
#   |_| |____/|____/ 

from importlib.metadata import entry_points
from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    readme = f.read()

with open('requirements.txt', 'r') as f:
    reqs = f.read().split() 
   
setup(
    name = 'Card Bot',
    version = '0.0.0',
    description = 'Might add later',
    long_description=readme,
    url = 'https://github.com/TheDystopian/NarutoCardBot',
    packages = find_packages('src'),
    install_requires = reqs,
    package_dir={'':'src'},
)


