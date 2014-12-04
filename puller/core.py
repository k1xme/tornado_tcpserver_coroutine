from tornado import tcpserver, iostream, gen
from tornado.iostream import StreamClosedError
from tornado.concurrent import return_future, Future
from puller import logger, session
from puller.models import Device, DeviceData
from puller.hmframe import insert_crc, bytes_to_float, bytes_to_double, \
    unpack_frame, parse_data, compute_hisdata_addr, DATA_LENGTHS, gen_collect_cmd_frame
from bitstring import BitArray, Bits, pack
from socket import inet_ntoa
import struct, datetime


now = datetime.datetime.now


class Puller(tcpserver.TCPServer):
    device_dict = {}


    def handle_stream(self, stream, address):
        logger.info('New connection from %s' % str(address))
        self.handle_registration(stream, address)


    @gen.coroutine
    def handle_registration(self, stream, address):
        try:
            # receives the 21-byte registration info and proceeds.
            # Otherwise yield and keep waiting.
            message = yield stream.read_bytes(21)

            # unpacks the received bytes into phone number, IP addr.
            reg_data = struct.unpack('!I11scIc',message)
            phone = reg_data[1]

            logger.info('Registered device(%s)' % phone)

            # adds this new device into database.
            device = Device(18, phone, stream)
            session.add(device)
            session.commit()
            self.device_dict[device.portid] = device

        except Exception as e:
            logger.exception('Register device(%s) failed' % phone)
            logger.exception('In handle_registration %s' % e)
        else:
            logger.info('[Device list] %s' % self.device_dict.keys())
            device.colltype = 'R'
            self.handle_device(device)


    @gen.coroutine
    def collect_data(self, device, data_type, interval=1, chktime=None):
        try:
            timestamp = now() if data_type==4 and not chktime else chktime
            recv_frame = BitArray()
            request_frame = gen_collect_cmd_frame(device.devaddr, data_type, interval,
                    timestamp)

            # sends out the inqury command frame.
            device.stream.write(request_frame.bytes)

            # receives the first 4 leading bytes
            recv_bytes = yield device.stream.read_bytes(4)

            leading, head, remain_length = struct.unpack('!HBB', recv_bytes)
            recv_frame += hex(leading)
            recv_frame += hex(head)
            recv_frame += hex(remain_length)

            # receives the remaining bytes from device.
            remain_bytes = yield device.stream.read_bytes(remain_length)

            for byte in remain_bytes:
                recv_frame += BitArray(uint=ord(byte), length=8)

            # unpacks the binary data into a Python dict object
            frame_dict = unpack_frame(remain_bytes, DATA_LENGTHS[data_type])

            # parses those data bytes into JSON.
            data_json = parse_data(frame_dict['data'])

            logger.info('Received: %s' % recv_frame)
            
        except StreamClosedError:
            logger.exception('Device(%s) lost connection' % device.portid)
            self.device_dict.pop(device.portid)
        except Exception as e:
            logger.error('In collect_data %s' % str(e))
            self.device_dict.pop(device.portid)
            device.stream.close()
            device.online = False
        else:
            raise gen.Return(data_json)


    @gen.coroutine
    def send_cmd(self, device, message):
        device = self.device_dict.get(device.portid, None)
        if not device:
            raise Exception('No such device')

        try:
            yield device.write(message)
        except StreamClosedError:
            logger.exception('Device(%s) lost connections' % device.portid)
            self.device_dict.pop(device.portid)
            device.online = False


    @gen.coroutine 
    def handle_device(self, device, chktime=None):
        action = device.colltype or 'R'
        cmd = None
        try:
            # get msg from rabbitmq.
            # process the msg.

            if action == 'R':
                timestamp = now()

                data = yield self.collect_data(device, 4)
                # Ensures we only store data in a interval of 1 minute.

                if not device.chktime or (timestamp.minute != device.chktime.minute):
                    device.chktime = timestamp
                    logger.info("storing data")
                    #devdata = DeviceData(data)
                    #device.devdata.append(devdata)
                    #session.add(device)
                    #session.commit()

                logger.info('[Parsed data] %s' % data)
                delay = 60 - timestamp.second
                if delay > 55:
                    # This is only for keeping the connection alive.
                    # The data returned is not meant to be stored in database.
                    self.io_loop.call_later(55, self.handle_device, device)
                else:
                    self.io_loop.call_later(delay, self.handle_device, device)

            elif action == 'C':
                yield self.send_cmd(device, cmd)
                self.io_loop.add_callback(self.handle_device, device)

            elif action == 'H':
                chktime = chktime
                yield self.collect_data(device, 4, chktime=chktime)
                device.chktime = chktime
                # request history data from device right in the next iteration.
                #devdata = DeviceData(data)
                #device.devdata.append(devdata)
                #session.add(device)
                #session.commit()
                chktime += datetime.timedelta(0,60,0)
                self.io_loop.add_callback(self.handle_device, device, chktime)

        except Exception as e:
            logger.exception(str(e))
            raise e

        