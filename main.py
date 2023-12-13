from src.packet_sniff import sniffing_thread
import json

thread = sniffing_thread()
thread.start()

