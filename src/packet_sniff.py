from datetime import datetime
from src.logger import Logger
from datetime import datetime
from src.city_mapping import city_mapping

import multiprocessing
import socket
import platform
import json
import re
import time
import requests

PROBLEMS = ["'", "$", "QH", "?8", "H@", "ZP"]

def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

class albion_sniff(multiprocessing.Process):
    def __init__(self, data_queue=None):
        super(albion_sniff, self).__init__()

        # set problems list
        self.problems = PROBLEMS
        self.data_queue = data_queue
        self.logs = list()
        self.logger = Logger()  # You need to define Logger class
        self.lock = multiprocessing.Lock()

        # define process attributes
        self.market_location = None
        self.current_location = None
        self.previous_location = None
        self.recording = True
        self.visited = False
        self.found_data = False
        self.dupe_check = set()

        # initialize socket object
        if platform.system() != "Windows":
            self.sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)

        # socket setup for windows environment
        if platform.system() == "Windows":
            self.sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW)
            self.sniffer.bind((local_ip(), 0))
            self.sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

    def process_data(self):
        print("Starting Albion Packet Sniffer")
        # while the process is set to recording, sniff and record data
        while self.recording:
            # wait for market data
            try:
                self.data_queue.put(self.sniffer.recvfrom(1350)[0])
            except OSError:
                pass

    def run_market(self):
        while self.recording:
            if not self.data_queue.empty():
                self.data = str(self.data_queue.get())

                for p in self.problems:
                    self.data = self.data.replace(p, "")

                self.find_location()
                self.find_market_data()

    def find_location(self):
        try:
            for s in self.data.split("\\"):
                match = re.findall(r'^x04(\d{4})$', s)

                if len(s) > 6 and match and city_mapping.get(match[0]):
                    if self.current_location != city_mapping.get(match[0]) and not self.visited:
                        self.previous_location = self.current_location
                        self.current_location = city_mapping.get(match[0])
                        self.visited = True
                        print(f"Current Location : {self.current_location}")

                    if 'Market' in city_mapping.get(match[0]) and self.market_location != city_mapping.get(match[0]):
                        print(f"Successfully Grab Market Location : {city_mapping.get(match[0])}")
                        self.market_location = city_mapping.get(match[0])
                        time.sleep(5)

                    elif city_mapping.get(match[0]):
                        self.visited = False

        except Exception as e:
            self.logger.log_message(f"{datetime.now()} - Location Error : {e}")

    def find_market_data(self):
        # partition received cleaned data into chunks
        chunks = [s[3:] for s in self.data.split("\\") if len(s) > 5 and ("UnitPriceSilver" in s or "ReferenceId" in s)]

        # processed chunks
        for chunk in chunks:
            # if this chunk is the start of a new piece of market information, add a new entry to the log
            if "{" in chunk[:4]:
                self.found_data = True
                self.logs.append(chunk[chunk.find("{"):])

            # otherwise, this chunk is assumed to be a continuation of the last chunk and is simply concatenated to the end
            elif self.logs:
                self.logs[-1] += chunk

        if self.market_location and self.found_data:
            try:
                market_data = json.loads(self.logs[0])
                if '@' not in market_data['ItemTypeId']:
                    market_data['ItemTypeId'] = market_data['ItemTypeId'] + '@' + str(market_data['EnchantmentLevel'])

                if market_data['ItemTypeId'] + str(market_data['QualityLevel']) not in self.dupe_check:
                    market_data['UnitPriceSilver'] //= 10000
                    market_data['TotalPriceSilver'] //= 10000
                    market_data['Location'] = self.market_location
                    self.post_to_database(market_data)

                self.dupe_check.add(market_data['ItemTypeId'] + str(market_data['QualityLevel']))

            except json.decoder.JSONDecodeError:
                self.logger.log_message(f"{datetime.now()} - JSON Decode Error Ignoring")

        self.found_data = False
        self.logs = list()

    def start_processes(self):
        # Create processes for both run_location and run_market
        process_data = multiprocessing.Process(target=self.process_data)
        market_process = multiprocessing.Process(target=self.run_market)

        # Start processes
        process_data.start()
        market_process.start()

    def post_to_database(self, json_data):
        # Replace the following URL with the endpoint of your database API
        database_url = "http://159.89.34.98:8000/api/prices/"

        # Send a POST request with JSON data to the database
        response = requests.post(database_url, json=json_data)
 
        # Check if the request was successful (status code 200)
        if response.status_code == 200 or response.status_code == 201:
            pass
        else:
            self.logger.log_message(f"{datetime.now()} -  Failed to post data to the database. Status code: {response.status_code}")