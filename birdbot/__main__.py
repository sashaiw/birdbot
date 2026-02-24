import os
from birdbot.bot import BirdBot


# if os.name != "nt":
#     import uvloop
#     uvloop.install()

if __name__ == '__main__':
    BirdBot().run(os.environ.get('DISCORD_TOKEN'))
