"""logging"""

import logging
import sys

from src.gname import PYTASKMGR

__all__ = ["logger"]

def setup():
    logger = logging.getLogger(PYTASKMGR)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(
        logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(sh)
    logger.setLevel(logging.DEBUG)
    return logger
setup()

logger = logging.getLogger(PYTASKMGR)
