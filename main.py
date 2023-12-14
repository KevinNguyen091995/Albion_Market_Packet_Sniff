from src.packet_sniff import albion_sniff

thread = albion_sniff()
thread.start_threads()
