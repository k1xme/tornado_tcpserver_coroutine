# -*- encoding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, Float, Integer, String, DATETIME, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from puller import Base


now = datetime.now


class Device(Base):
    """docstring for Terminal"""
    __tablename__ = 'fthfldev'
    id = Column(Integer, primary_key=True)
    devname = Column(String(60), nullable=False)
    portid = Column(String(30), nullable=False)
    baudrate = Column(String(5))
    devaddr = Column(Integer, nullable=False)
    fcollect = Column(String(1), nullable=False) # H for history data, R for realtime, C for command
    status = Column(String(1))
    chktime = Column(DATETIME)
    collstat = Column(DATETIME)
    insttime = Column(DATETIME)
    collhint = Column(Integer)
    collrint = Column(Integer)

    flowunit = Column(String(20))
    sumunit = Column(String(20))
    diffunit = Column(String(20))
    presunit = Column(String(20))
    tempunit = Column(String(20))
    densunit = Column(String(20))

    owner = Column(String(20))
    userid = Column(String(10))
    dpzero = Column(Float)
    pzero = Column(Float)
    dpcut = Column(Float)
    flowmax = Column(Float)
    flowmin = Column(Float)
    online = Column(Boolean)
    compname = Column(String(50))
    charge_day = Column(Integer)
    stream = None

    devdata = relationship('DeviceData', backref='device')


    def __init__(self, devaddr, phone_num, stream, **kwargs):
        self.devaddr = devaddr
        self.portid = 'GPRS' + phone_num
        self.stream = stream
        self.online = True
        self.colltype = 'R'


class DeviceData(Base):
    """docstring for SensorInfo"""
    __tablename__ = 'fthfldtl'


    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey(Device.id))
    sumflow = Column(Float) #累计流量
    temperatu = Column(Float) #温度
    pressure = Column(Float) #压力
    diffpt = Column(Float) #差压传感器温度
    prest = Column(Float) #压力传感器温度
    diffpres = Column(Float) #差压
    retrycnt = Column(Integer) #重试次数
    density = Column(Float) #温度
    flow = Column(Float) #瞬时流量
    resetinfo = Column(String(30)) #重置信息
    warninfo = Column(String(30)) #告警信息
    status = Column(String(30)) #数据状态
    colltime = Column(DATETIME, nullable=False) #采集时间


    def __init__(self, sumflow, flow, temperatu,
        pressure, density, prest, diffpt, diffpres, resetinfo=None, warninfo=None, colltime=None):
        self.colltime = now() if not colltime else colltime
        self.sumflow = sumflow
        self.flow = flow
        self.density = density
        self.prest = prest
        self.temperatu = temperatu
        self.pressure = pressure
        self.diffpt = diffpt
        self.diffpres = diffpres
        self.resetinfo = resetinfo
        self.warninfo = warninfo