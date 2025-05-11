# Import Packages
import logging
import sys


class Logger:
    """
    A class that is called at time of maintaining the logs
    """

    def __init__(self):
        """
        Initialize the logger
        """
        self.APP_LOGGER_NAME = "Intel AI Hackathon 2025"

    def get_logger(self, module_name, file_name="app.log"):
        """
        Creates a log file in defined format and returns the logger variable
        """

        # formating the logger
        logger = logging.getLogger(self.APP_LOGGER_NAME).getChild(module_name)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %Z",
        )
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(sh)
        if file_name:
            fh = logging.FileHandler(file_name, encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)

        return logger