from gevent import monkey
monkey.patch_all()

from config import Config
from app import app

if __name__ == "__main__":
    app.run()
