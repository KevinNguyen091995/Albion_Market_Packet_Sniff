import socket
import json
import re
import threading
import platform
import keyboard
import requests

PROBLEMS = ["'", "$", "QH", "?8", "H@", "ZP"]

def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

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
        self.location = ""
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

            for s in data.split("\\"):
                match = re.findall(r'@([^@]+)@', s)
                
                if len(s) > 5 and match:
                    print(match)

            # processed chunks
            for chunk in chunks:
                # if this chunk is the start of a new piece of market information, add a new entry to the log
                if "{" in chunk[:4]:
                    self.logs.append(chunk[chunk.find("{"):])
                    
                # otherwise, this chunk is assumed to be a continuation of the last chunk and is simply concatenated to the end
                elif self.logs:
                    self.logs[-1] += chunk

            # if self.logs and self.logs[0] != "":
            #     market_data = json.loads(self.logs[0])
            #     market_data['UnitPriceSilver'] //= 10000
            #     market_data['TotalPriceSilver'] //= 10000
            #     self.post_to_database(market_data)

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