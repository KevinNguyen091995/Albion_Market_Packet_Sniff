import socket
import json
import threading
import platform
import keyboard
import requests
import time
from datetime import datetime

PROBLEMS = ["'", "$", "QH", "?8", "H@", "ZP"]
HEADERS = ["Id", "unitprice", "TotalPriceSilver", "Amount", "tier", "IsFinished",
           "AuctionType", "HasBuyerFetched", "HasSellerFetched", "SellerCharacterId",
           "SellerName", "BuyerCharacterId", "BuyerName", "unique_name", "itemgroup",
           "enchantment", "quality", "Expires", "ReferenceId"]


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


class datapoint:
    """ Single market datapoint including all available data from the game's api"""

    def __init__(self, data):
        # data attribute
        self.data = data[:]
        
        # correct silver prices
        data[1] //= 10000
        data[2] //= 10000
        # convert expire date to datetime object
        data[17] = datetime.strptime(data[17][0:16], "%Y-%m-%dT%H:%M")
        # set attributes to data indexes
        self.Id = data[0]
        self.UnitPriceSilver = data[1]
        self.TotalPriceSilver = data[2]
        self.Amount = data[3]
        self.Tier = data[4]
        self.IsFinished = data[5]
        self.AuctionType = data[6]
        self.HasBuyerFetched = data[7]
        self.HasSellerFetched = data[8]
        self.SellerCharacterId = data[9]
        self.SellerName = data[10]
        self.BuyerCharacterId = data[11]
        self.BuyerName = data[12]
        self.ItemTypeId = data[13]
        self.ItemGroupTypeId = data[14]
        self.EnchantmentLevel = data[15]
        self.QualityLevel = data[16]
        self.Expires = data[17]
        self.ReferenceId = data[18]

class sniffer_data:
    """ Organized sniffed market data"""

    def __init__(self, logs, parsed):
        self.logs = logs[:]

    def __getitem__(self, i):
        return self.parsed[i]

    def __len__(self):
        return len(self.parsed)

    def __str__(self):
        parsed = [{HEADERS[j]: attribute for j, attribute in enumerate(i.data)} for i in self.parsed]
        return json.dumps({"logs": self.logs})


class sniffing_thread(threading.Thread):
    """ Sniffing thread class"""

    def __init__(self, problems=PROBLEMS):

        threading.Thread.__init__(self)

        # set problems list
        self.problems = problems

        # define thread attributes
        self.n = 0
        self.e = 0
        self.order_data = ""
        self.recording = False
        # log list with placeholder entry
        self.logs = [""]

        # initialize socket object
        if platform.system() != "Windows":
            self.sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)

        # socket setup for windows environment
        if platform.system() == "Windows":
            self.sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW)
            self.sniffer.bind((local_ip(), 0))
            self.sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)


    def run(self):

        # set recording to True
        self.recording = True

        # Create a thread to listen for the tilde key press
        tilde_listener = threading.Thread(target=self.stop_on_tilde_key_press)
        tilde_listener.start()

        # while the thread is set to recording, sniff and record data
        while self.recording:

            # wait for market data
            try:
                data = self.sniffer.recvfrom(1350)[0]
            except OSError:
                pass

            # remove known problematic strings from data
            data = str(data)
            for p in self.problems:
                data = data.replace(p, "")

            # partition received cleaned data into chunks
            chunks = [s[3:] for s in data.split("\\") if len(s) > 5 and ("Silver" in s or "ReferenceId" in s)]

            # processed chunks
            for chunk in chunks:
                # if this chunk is the start of a new piece of market information, add a new entry to the log
                if "{" in chunk[:4]:
                    self.logs.append(chunk[chunk.find("{"):])
                    
                # otherwise, this chunk is assumed to be a continuation of the last chunk and is simply concatenated to the end
                elif self.logs:
                    self.logs[-1] += chunk

            if self.logs and self.logs[0] != "":
                market_data = json.loads(self.logs[0])
                market_data['UnitPriceSilver'] //= 10000
                market_data['TotalPriceSilver'] //= 10000
                self.post_to_database(market_data)

            self.logs = list()

    def stop_on_tilde_key_press(self):
        while True:
            # Check if the tilde key (~) is pressed
            if keyboard.is_pressed('~'):
                self.recording = False
                print("Tilde key pressed. Stopping recording.")
                break

    def post_to_database(self, json_data):
        # Replace the following URL with the endpoint of your database API
        database_url = "http://127.0.0.1:8000/api/prices/"
        
        # Send a POST request with JSON data to the database
        response = requests.post(database_url, json=json_data)

        # Check if the request was successful (status code 200)
        if response.status_code == 200 or response.status_code == 201:
            print("Data posted to the database successfully.")
        else:
            print(f"Failed to post data to the database. Status code: {response.status_code}")
            print("Response content:", response.text)