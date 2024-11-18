# /usr/bin/env python

from pylsl import StreamInlet, resolve_byprop, resolve_stream
from pythonosc import udp_client
from threading import Thread
from time import sleep

from muse_osc.buffers import BandCalculator, ELEMENTS, BANDS
oscclient = udp_client.SimpleUDPClient("127.0.0.1", 4545)

muse_names = [
    'Muse-0530',
    'Muse-00AC',
    'Muse-EB8D',
    'Muse-EFCD',
    'Muse-00AD',
    'Muse-079C'
]

SOURCE_IDs = {
'Muse00:55:DA:B8:05:30': 'Muse-0530', # BGAPI Source ID
'Muse00:55:DA:B6:00:AC': 'Muse-00AC',# BGAPI Source ID
'Muse00:55:DA:B7:EB:8D': 'Muse-EB8D',
'Muse00:55:DA:B5:EF:CD': 'Muse-EFCD',
'Muse00:55:DA:B6:00:AD': 'Muse-00AD',
'Muse00:55:DA:B6:07:9C': 'Muse-079C',
'Muse143648F2-D9AD-77CC-5E6D-4C6185E433A9': 'Muse-00AC', # BLEAK source id
'Muse6CAEA77C-CFB5-8297-B709-419565E920D1': 'Muse-0530', # BLEAK source id
'MuseFCC7CA7F-9A94-727A-621C-09620A24A809': 'Muse-EFCD',
'MuseA6F24BE5-6134-D1E5-2A8D-96F242EC5448': 'Muse-EB8D',
'MuseAAAD869F-7E03-A2DA-5BC5-05D1CFAB4373': 'Muse-00AD',
'Muse68F92D62-07FF-DC68-09E6-ED2A18DD5EAB': 'Muse-079C',
}

class LslToOscStreamer:

    def __init__(self, device_name, compute_bands = False):
        # oscclient = udp_client.SimpleUDPClient(host, port)
        self.is_streaming = False

        self.device_name = device_name

        self.inlets = {
            # As defined in muselsl stream
            'EEG': None,
            'accelerometer': None,
            'PPG': None,
            'gyroscope': None,
        }
        self.band_calculator = None        
        self.shift_length = 0.2
        self.sample_rate = 256

        if compute_bands:
            print("Initializing Band Calculator")
            self.band_calculator = BandCalculator()
            # for key in self.streams.keys():
            #     self.band_calculators[key] = BandCalculator()
            tmp = BandCalculator()
            self.shift_length = tmp.shift_length
            self.sample_rate = tmp.sample_rate
    
    def connect(self, streams):
        for stream in streams:
            if stream.source_id() is not None:
                muse_name = SOURCE_IDs[stream.source_id()]
                if muse_name == self.device_name:
                    stream_type = stream.type()
                    print(f"{muse_name} {stream_type} captured")                    
                    # print(stream.source_id() , stream_type)
                    if stream_type == 'ACC': stream_type = 'accelerometer'
                    if stream_type == 'GYRO': stream_type = 'gyroscope'
                    if stream_type in ['EEG', 'PPG', 'accelerometer', 'gyroscope'] and self.inlets[stream_type] == None:
                        self.inlets[stream_type] = StreamInlet(stream, max_chunklen=12)
                # else:
                    # print(muse_name + "not equals " +self.device_name)
        # if list(set(self.inlets.values())) == [None]:
        #     raise RuntimeError(f"No Stream available.")
        print(f"Streams available: {self.inlets}")
        return True


    def stream_data(self):
        self.is_streaming = True
        

    def close_stream(self):
        self.is_streaming = False
        for inlet in self.inlets.values():
            inlet.close_stream()

def _stream_handler():
    hz_10_counter = 0
    # while self.is_streaming:
        # for muse_name, stream_inlets in self.streams.items():
    while True:
        for streamer in streamers:
            if streamer.is_streaming:
                muse_name = streamer.device_name                
                for stream_type, inlet in streamer.inlets.items():
                    if inlet == None: continue
                    # sample_chunk, ts = inlet.pull_sample(); sample_chunk = [sample_chunk]
                    sample_chunk, ts = inlet.pull_chunk(
                        timeout=0.0, max_samples=int(streamer.shift_length * streamer.sample_rate)
                        )
                    # print(len(sample_chunk))
                    for sample in sample_chunk:
                        # Taken by the spec of Mind-Monitor
                        # https://mind-monitor.com/FAQ.php#oscspec
                        if stream_type == "EEG":
                            assert len(sample) == 5 # TP9, AF7, AF8, TP10, AUX
                            # oscclient.send_message(f"/{muse_name}/eeg", sample)
                            # Broken out per EEG element
                            for channel_idx, channel in enumerate([
                                    f"/{muse_name}/eeg-tp9-le",
                                    f"/{muse_name}/eeg-af7-lf",
                                    f"/{muse_name}/eeg-af8-rf",
                                    f"/{muse_name}/eeg-tp10-re",
                                    f"/{muse_name}/eeg-aux",
                                ]):                                
                                oscclient.send_message(channel, sample[channel_idx])
                                # print(muse_name)

                        if stream_type == "gyroscope":
                            assert len(sample) == 3 # X, Y, Z                
                            oscclient.send_message(f"/{muse_name}/gyro", sample)

                        if stream_type == "accelerometer":
                            assert len(sample) == 3 # X, Y, Z
                            oscclient.send_message(f"/{muse_name}/acc", sample)

                        if stream_type == "PPG":
                            assert len(sample) == 3 # PPG1, PPG2, PPG3
                            oscclient.send_message(f"/{muse_name}/ppg", sample)

                    if streamer.band_calculator != None and stream_type == "EEG": # Compute bands
                        if (len(sample_chunk) > 0):
                            streamer.band_calculator.add_sample(sample_chunk, sample_type="EEG")

                            if round(ts[0],1) - int(ts[0]) != hz_10_counter:
                                streamer.band_calculator.compute_bands()
                                # print(self.band_calculator.get_protocol('alpha'))
                                hz_10_counter = round(ts[0],1) - int(ts[0])

                                for band in BANDS:
                                    channel = f"/{muse_name}/{band}_absolute"
                                    powers = []
                                    oscclient.send_message(channel,
                                            streamer.band_calculator.get_band_power(band, elements="ALL")
                                        )

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
                prog='muselsl2osc',
                description='Converts LSL input to OSC for use with tools like Neuromore',
            )
    parser.add_argument('--host', '-H', help="The HOST where OSC will be sent to", default='127.0.0.1')
    parser.add_argument('--port', '-p', help="The PORT where OSC will be sent to", default=4545)
    parser.add_argument('--timeout', help="Number of seconds until exit", default=3600)
    parser.add_argument('--lsl-streams', help='List of Muse LSL streams to be accepted', nargs='+',
        choices=['EEG','ACC','PPG','GYRO'], default=['EEG']
        )
    args = parser.parse_args()

    host = args.host
    port = args.port
    stream_time_sec = args.timeout

    print(f"Initializing connection to {args.host}:{args.port} - forwarding LSL streams: {args.lsl_streams}")
    streamers = []
    for idx, muse_name in enumerate(muse_names[0:6]):
        streamer = LslToOscStreamer(muse_name, compute_bands=True)
        # print(muse_name, port + idx)
        streamers.append(streamer)
    

    from threading import Timer

    def connect_all_streams():
        streams = resolve_stream()    
        for streamer in streamers:
            streamer.connect(streams)        
        Timer(5, connect_all_streams).start()  # 再次启动定时器

    connect_all_streams()  # 第一次调用    
    
    streaming_thread = Thread(target=_stream_handler)
    streaming_thread.daemon = True
    streaming_thread.start()    

    print(f"Start streaming data for {stream_time_sec} seconds")
    for streamer in streamers:
        streamer.stream_data()
    sleep(stream_time_sec)
    
    for streamer in streamers:
        streamer.close_stream()
    print("Stopped streaming. Exiting program...")
