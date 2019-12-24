#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import faulthandler; faulthandler.enable()

import configparser as ConfigParser
import os
import re
import time
from typing import Union, Any

import paho.mqtt.client as mqtt

import cec

# Default configuration
config = {
    'mqtt': {
        'broker': 'localhost',
        'port': 1883,
        'prefix': 'media',
        'user': os.environ.get('MQTT_USER'),
        'password': os.environ.get('MQTT_PASSWORD'),
    },
    'cec': {
        'id': 1,
        'port': 'RPI',
        'devices': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15',
    }
}
cec_client: Union[cec.ICECAdapter, None] = {}
mqtt_client: Union[mqtt.Client, None] = None

device_type = cec.CEC_DEVICE_TYPE_RECORDING_DEVICE
# levelStrMap = {
#     [cec.CEC_LOG_ERROR]: "ERROR"
#     [cec.CEC_LOG_WARNING]: "WARNING"
#     [cec.CEC_LOG_NOTICE]: "NOTICE"
#     [cec.CEC_LOG_TRAFFIC]: "TRAFFIC"
#     [cec.CEC_LOG_DEBUG]: "DEBUG"
# }


def mqtt_on_connect(client: mqtt, userdata: Any, flags: dict, rc: int):
    print("Connection returned result: " + str(rc))

    # Subscribe to CEC commands
    prefix = config['mqtt']['prefix'] + '/cec'
    client.subscribe([
        (prefix + '/cmd', 0),
        (prefix + '/+/cmd', 0),
        (prefix + '/tx', 0)
    ])


def mqtt_on_message(client: mqtt, userdata: Any, message: mqtt.MQTTMessage):
    try:
        cmd = message.topic.replace(config['mqtt']['prefix'] + '/cec', '').strip('/')
        payload = message.payload.decode()
        receive_message(cmd, payload)
    except Exception as e:
        print("Error during processing of message: ", message.topic, message.payload, str(e))


def mqtt_on_log(client: mqtt, userdata: Any, level: Any, buf: Any):
    print(level, buf)


def receive_message(topic: str, payload: str):
    print(f'Command received: {topic} ({payload})')

    if topic == 'cmd':
        commands = {
            'mute': cec_client.AudioMute,
            'unmute': cec_client.AudioUnmute,
            'voldown': cec_client.VolumeDown,
            'volup': cec_client.VolumeUp,
        }
        if payload not in commands:
            raise Exception(f'Unknown command ({payload})')
        commands[payload]()
        return

    if topic == 'tx':
        for command in payload.split(','):
            print(f'Sending raw: {command}')
            cec_send(command)
        return

    split = topic.split('/')
    if split[1] == 'cmd':
        addr = int(split[0])

        if payload == 'on':
            cec_send('44:6D', addr)
            mqtt_send(addr, 'on', True)
            return

        if payload == 'off':
            cec_send('36', addr)
            mqtt_send(addr, 'off', True)
            return

        raise Exception("Unknown command (%s)" % payload)


def mqtt_send(topic: Union[str, int], value: str, retain=False):
    mqtt_client.publish(config['mqtt']['prefix'] + '/cec/' + str(topic), value, retain=retain)


def cec_on_source_activated(*args):
    print('source activated', *args)
    pass


def cec_on_message(level, time, message):
    if level != cec.CEC_LOG_TRAFFIC:
        return 0
    if (message.startswith(">>")):
        print(f"[{time}]\t{message}")

    return 0
    # Send raw command to mqtt
    m = re.search('>> ([0-9a-f:]+)', message)
    if m:
        mqtt_send('rx', m.group(1))

    # Report Power Status
    m = re.search('>> ([0-9a-f])[0-9a-f]:90:([0-9a-f]{2})', message)
    if m:
        id = int(m.group(1), 16)
        # power = cec_client.PowerStatusToString(int(m.group(2)))
        power = 'on' if (m.group(2) == '00') or (m.group(2) == '02') else 'off'
        mqtt_send(id, power, True)
        return

    # Device Vendor ID
    m = re.search('>> ([0-9a-f])[0-9a-f]:87', message)
    if m:
        id = int(m.group(1), 16)
        power = 'on'
        mqtt_send(id, power, True)
        return

    # Report Physical Address
    m = re.search('>> ([0-9a-f])[0-9a-f]:84', message)
    if m:
        id = int(m.group(1), 16)
        power = 'on'
        mqtt_send(id, power, True)
        return


def cec_send(cmd, id=None):
    command = cmd if id is None else f'{device_type}{hex(id)[2:]}:{cmd}'
    command = command.lower()
    print(f'Command: {command}')
    c = cec_client.CommandFromString(command)
    cec_client.Transmit(c)


def cec_refresh():
    try:
        # for id in config['cec']['devices'].split(','):
            # cec_send('8F', id=int(id))
        cec_send('8F', 0)

    except Exception as e:
        print("Error during refreshing: ", str(e))


def cleanup():
    cec_client.Close()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


def parse_config():
    parser = ConfigParser.ConfigParser()
    if parser.read("config.ini"):

        # Load all sections and overwrite default configuration
        for section in parser.sections():
            config[section].update(dict(parser.items(section)))

    # Environment variables
    for section in config:
        for key, value in config[section].items():
            env = os.getenv(section.upper() + '_' + key.upper())
            if env:
                config[section][key] = type(value)(env)


def log_callback(level, time, message):
  return 0

def init_cec():
    cec_config = cec.libcec_configuration()
    cec_config.strDeviceName = "cec-mqtt"
    cec_config.bActivateSource = False
    cec_config.deviceTypes.Add(device_type)
    cec_config.clientVersion = cec.LIBCEC_VERSION_CURRENT
    # cec_config.bAutodetectAddress = True
    # cec_config.logicalAddresses.Set(3)
    # cec_config.SetLogCallback(cec_on_message)
    cec_config.SetLogCallback(log_callback)
    client = cec.ICECAdapter.Create(cec_config)
    if not client.Open(config['cec']['port']):
        raise Exception("Could not connect to cec adapter")

    # addresses: cec.cec_logical_addresses = client.GetLogicalAddresses()
    # str_out = 'Addresses controlled by libCEC: '
    # i = 0
    # not_first = False
    # while i < 15:
    #     if addresses.IsSet(i):
    #         if not_first:
    #             str_out += ', '
    #         str_out += client.LogicalAddressToString(i)
    #         if client.IsActiveSource(i):
    #             str_out += ' (*)'
    #         not_first = True
    #     i += 1
    # print(str_out)
    time.sleep(2)
    return client


def init_mqtt():
    client = mqtt.Client('cec-mqtt')
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message
    client.on_log = mqtt_on_log
    conf = config['mqtt']
    print(f'Connecting to MQTT server {conf["user"]}:{conf["password"]}@{conf["broker"]}:{conf["port"]}')
    if config['mqtt']['user']:
        client.username_pw_set(config['mqtt']['user'], password=config['mqtt']['password'])
    client.connect(config['mqtt']['broker'], int(config['mqtt']['port']), 60)
    client.enable_logger()
    client.loop_start()
    return client


try:
    try:
        parse_config()
    except Exception as e:
        print('ERROR: Could not configure:', str(e))
        exit(1)

    print('Initializing CEC...')
    try:
        cec_client = init_cec()
    except Exception as e:
        print('ERROR: Could not initialise CEC:', str(e))
        exit(1)

    print('Initializing MQTT...')
    mqtt_client = init_mqtt()

    print('Starting main loop...')
    while True:
        cec_refresh()
        time.sleep(10)

except KeyboardInterrupt:
    cleanup()

except RuntimeError as e:
    cleanup()
    raise e
