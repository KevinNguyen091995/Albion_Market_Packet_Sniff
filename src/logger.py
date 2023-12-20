import logging

class Logger:
    def __init__(self):
        logging.basicConfig(filename='sniff.log', filemode='a', format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        self.logger = logging.getLogger()

    def log_message(self, message):
        self.logger.info(message)