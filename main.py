from src.packet_sniff import sniffing_thread
from time import sleep

thread = sniffing_thread()
thread.start()

sleep(10)

thread.stop()