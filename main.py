from src.packet_sniff import sniffing_thread
from time import sleep
import json

thread = sniffing_thread()
thread.start()

