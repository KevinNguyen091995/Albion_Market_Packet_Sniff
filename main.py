from src.packet_sniff import *


if __name__ == '__main__':
    multiprocessing.freeze_support()
    data_queue = multiprocessing.Queue()
    albion_sniff_instance = albion_sniff(data_queue=data_queue)
    albion_sniff_instance.start_processes()