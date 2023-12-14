import logging

class Logger():
    def __init__(self):
        logging.basicConfig(filename='sniff.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger()

    def log_message(self, message):
        self.logger.error(message)