# -*- encoding: utf-8 -*-
from bitstring import BitArray, Bits, pack
from json import dumps, loads
import math
import struct


DATA_ADDRS = [8,
              16646192,
              16711806,
              16711796]
# Lengths(Bytes) of different data type
DATA_LENGTHS = [20,
                8,
                28,
                32,
                32
            ]
# Data types
FLOAT_DATA = 0
TIME_DATA = 1
CONCISE_REALTIME_DATA = 2
SPECIFIC_REALTIME_DATA = 3
HISTORY_DATA = 4


def insert_crc(frame):
    '''
    Params    Type
    frame     BitArray

    Calculates and inserts check code into the given frame.
    '''
    crc = 0
    frame_bytes = frame.bytes
    for i in range(1, 8):
        crc = (crc + ord(frame_bytes[i+1])) % 256
    crc = 256 - crc
    crc = Bits(uint=crc, length=8)
    frame.append(crc)
    return True


def bytes_to_float(info_bytes):
    if len(info_bytes) != 4:
        raise Exception

    b1 = ord(info_bytes[0])
    b2 = ord(info_bytes[1])
    b3 = ord(info_bytes[2])
    b4 = ord(info_bytes[3])

    exp_sign = -1 if (b1 & 0x80 == 128) else 1
    exp = b1 & 0x7f if exp_sign >0 else ~(b1&0x7f)+1

    mantissa_sign = -1 if (b2 & 0x80 == 128) else 1

    if mantissa_sign > 0:
        tmp = Bits(uint=b2&0x7f, length=8) + Bits(uint=b3,length=8) + \
          Bits(uint=b4, length=8)
    else:
        tmp = BitArray()
        tmp += Bits(uint=b2&0x7f, length=7)
        tmp += Bits(uint=b3, length=8)
        tmp += Bits(uint=b4, length=8)
        tmp = Bits(int=~(tmp.int) + 1, length=24)

    mantissa_int = 0

    if exp_sign > 0:
        mantissa_int = tmp[:exp+1].int if mantissa_sign > 0 else -tmp[:exp+1].int

        tmp = tmp[exp+1:]
        mantissa = 0
        for i in range(0, len(tmp)):
            if tmp[i]:
                mantissa += math.pow(0.5, i+1)

    else:
        mantissa = 0
        for i in range(0, len(tmp)):
            if tmp[i]:
                mantissa += math.pow(0.5, i + (-exp))

    return mantissa_int + mantissa


def bytes_to_double(info_bytes):
    if len(info_bytes) != 8:
        raise Exception

    b1 = ord(info_bytes[0])
    b2 = ord(info_bytes[1])
    b3 = ord(info_bytes[2])
    b4 = ord(info_bytes[3])
    try:
        tmp = Bits(uint=b1, length=8) + Bits(uint=b2,length=8) + \
          Bits(uint=b3, length=8) + Bits(uint=b4, length=8)
    except Exception as e:
        raise e

    return tmp.int + bytes_to_float(info_bytes[4:])


def unpack_frame(bdata, info_len=32):
    info_len += 4
    frame_format = '<3B{info_len}sB'.format(info_len=info_len)
    dest_addr, org_addr, reply_code, data, crc = struct.unpack(frame_format,
        bdata)
    result = {'dest_addr': dest_addr, 'org_addr':org_addr,
              'reply_code': hex(reply_code),
              'data': data, 'crc': crc}
    
    return result


def parse_data(bdata, type=4, jsonify=True):
    try:
        if type == HISTORY_DATA:
            total_flow = bytes_to_double(bdata[4:12])
            flow = bytes_to_float(bdata[12:16])
            tempture = bytes_to_float(bdata[16:20])
            pressure = bytes_to_float(bdata[20:24])
            diff_pressure = bytes_to_float(bdata[24:28])
            density = bytes_to_float(bdata[28:32])
            result = {'total_flow': total_flow,
            'flow': flow, 'tempture': tempture, 
            'pressure': pressure, 'diff_pressure': diff_pressure,
            'density': density}
    except Exception as e:
        raise e
    else:
        return result if not jsonify else \
            dumps(result, indent=4, separators=(', ', ': '))


def compute_hisdata_addr(interval, year, month, day, hour, minute):
    '''
    Calculates the address of history data according to the given time params.

    interval can be set to [1, 10, 60], which stands for 1min, 10min, 60min interval
    respectively.

    '''
    data_addr = 0

    if interval == 1:
        if day <= 10:
            daytemp = day
        elif day <= 20:
            daytemp = day - 10
        else:
            daytemp = day - 20

        data_addr = ((daytemp - 1) * 1440 + hour * 60 + minute) * 32
    
    elif interval == 10:
        if month <= 3:
            monthtemp = month
        elif month <= 6:
            monthtemp = month - 3
        elif month <= 9:
            monthtemp = month - 6
        elif month <= 12:
            monthtemp = month - 9
        else:
            monthtemp = 1

        data_addr = ((monthtemp - 1) * 144 * 31 + (day - 1) * 144 \
                        + hour * 6 + (minute / 10)) * 32
    
    elif interval == 60:
        data_addr = ((month - 1) * 24 * 31 + (day - 1) * 24 + hour) * 32

    return data_addr


def gen_collect_cmd_frame(device_addr, data_type, interval=1, timestamp=None):
    '''
    device_addr -- the logic address of the device.      
    data_type -- the type of target data.
    data_addr  -- the beginning address of target data.
    interval -- the interval of historical data to be retrieved in minutes.
    timestamp -- the specific time of historical data to be retrieved. 

        value           comment
        8               use for accessing 5 float(e.g 瞬时流量，温度，压力，密度，差压).
        16646192        use for accessing device timestamp
        16711806        use for accessing realtime sensor data
        16711796        use for accessing more specific realtime sensor data
    '''
    try:
        # assemble request frame.
        data_addr = compute_hisdata_addr(interval, timestamp.year,
                                     timestamp.month, timestamp.day,
                                     timestamp.hour,
                                     timestamp.minute) \
                                    if data_type == 4 else DATA_ADDRS[data_type]

        frame_format = 'hex:8, hex:8, uint:8, uint:8, hex:8, uint:8, uint:8, uint:8, \
        uint:8'
        frame_header = '0x7e'
        frame_length = '0x08' 
        origin_addr = 0 # the logic address of the server, which ranges from 0 to 4.
        cmd = '0x46' # all the read request uses '0x46' command code.
        para_1 = ((data_addr >> 16) & 0xff) # don't know what it is used for.
        para_2 = ((data_addr >> 8) & 0xff)
        para_3 = (data_addr & 0xff)

        # specifies the data length in returning data. This may
        # varies with different data type. For now, we just go by 28,
        # which was the length of realtime data.
        data_length = DATA_LENGTHS[data_type]
    
        # pack all the fields into a frame.
        request_frame = pack(frame_format, frame_header,frame_length,
            device_addr, origin_addr, cmd, para_1, para_2, para_3, data_length)
        # generate CRC and insert it at the end of the frame.
        insert_crc(request_frame)
    except Exception as e:
        raise e

    return request_frame # BitArray