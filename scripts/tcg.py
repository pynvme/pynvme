#
#  BSD LICENSE
#
#  Copyright (c) Crane Chu <cranechu@gmail.com>
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#    * Neither the name of Intel Corporation nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# -*- coding: utf-8 -*-


import enum
import time
import pytest
import struct 
import logging

from nvme import *


class OPAL_TOKEN(enum.IntEnum):
    TRUE = 0x01
    FALSE = 0x00
    TABLE = 0x00
    STARTROW = 0x01
    ENDROW = 0x02
    STARTCOLUMN = 0x03
    ENDCOLUMN = 0x04
    VALUES = 0x01
    PIN = 0x03
    RANGESTART = 0x03
    RANGELENGTH = 0x04
    READLOCKENABLED = 0x05
    WRITELOCKENABLED = 0x06
    READLOCKED = 0x07
    WRITELOCKED = 0x08
    ACTIVEKEY = 0x0A
    MAXRANGES = 0x04
    MBRENABLE = 0x01
    MBRDONE = 0x02
    HOSTPROPERTIES = 0x00
    STARTLIST = 0xF0
    ENDLIST = 0xF1
    STARTNAME = 0xF2
    ENDNAME = 0xF3
    CALL = 0xF8
    ENDOFDATA = 0xF9
    ENDOFSESSION = 0xFA
    STARTTRANSACTON = 0xFB
    ENDTRANSACTON = 0xFC
    EMPTYATOM = 0xFF
    WHERE = 0x00
    LIFECYCLE = 0x06
    AUTH_ENABLE = 0x05
    BOOLEAN_EXPR = 0x03

        
class OPAL_UID(enum.IntEnum):
    # user
    SMUID = 0
    THISSP = 1 
    ADMINSP = 2
    LOCKINGSP = 3 
    ANYBODY = 4
    SID = 5
    ADMIN1 = 6
    USER1 = 7
    USER2 = 8

    # table
    LOCKINGRANGE_GLOBAL = 9
    LOCKINGRANGE_ACE_RDLOCKED = 10
    LOCKINGRANGE_ACE_WRLOCKED = 11
    MBRCONTROL = 12
    MBR = 13
    AUTHORITY_TABLE = 14
    C_PIN_TABLE = 15
    LOCKING_INFO_TABLE = 16
    PSID = 17

    # C_PIN
    C_PIN_MSID = 18
    C_PIN_SID = 19
    C_PIN_ADMIN1 = 20 
    C_PIN_USER1 = 21

    # half
    HALF_AUTHORITY_OBJ_REF = 22
    HALF_BOOLEAN_ACE = 23


class OPAL_METHOD(enum.IntEnum):
    PROPERTIES = 0
    STARTSESSION = 1
    REVERT = 2
    ACTIVATE = 3
    NEXT = 4
    GETACL = 5
    GENKEY = 6
    REVERTSP = 7
    GET = 8
    SET = 9
    AUTHENTICATE = 10
    RANDOM = 11


opal_uid_table = {
    OPAL_UID.SMUID: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff],
    OPAL_UID.THISSP: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01],
    OPAL_UID.ADMINSP: [0x00, 0x00, 0x02, 0x05, 0x00, 0x00, 0x00, 0x01],
    OPAL_UID.LOCKINGSP: [0x00, 0x00, 0x02, 0x05, 0x00, 0x00, 0x00, 0x02],
    OPAL_UID.ANYBODY: [0x00, 0x00, 0x00, 0x09, 0x00, 0x00, 0x00, 0x01],
    OPAL_UID.SID: [0x00, 0x00, 0x00, 0x09, 0x00, 0x00, 0x00, 0x06],
    OPAL_UID.ADMIN1: [0x00, 0x00, 0x00, 0x09, 0x00, 0x01, 0x00, 0x01],
    OPAL_UID.USER1: [0x00, 0x00, 0x00, 0x09, 0x00, 0x03, 0x00, 0x01],
    OPAL_UID.USER2: [0x00, 0x00, 0x00, 0x09, 0x00, 0x03, 0x00, 0x02],
    OPAL_UID.LOCKINGRANGE_GLOBAL: [0x00, 0x00, 0x08, 0x02, 0x00, 0x00, 0x00, 0x01],
    OPAL_UID.LOCKINGRANGE_ACE_RDLOCKED: [0x00, 0x00, 0x00, 0x08, 0x00, 0x03, 0xE0, 0x01],
    OPAL_UID.LOCKINGRANGE_ACE_WRLOCKED: [0x00, 0x00, 0x00, 0x08, 0x00, 0x03, 0xE8, 0x01],
    OPAL_UID.MBRCONTROL: [0x00, 0x00, 0x08, 0x03, 0x00, 0x00, 0x00, 0x01],
    OPAL_UID.MBR: [0x00, 0x00, 0x08, 0x04, 0x00, 0x00, 0x00, 0x00],
    OPAL_UID.AUTHORITY_TABLE: [0x00, 0x00, 0x00, 0x09, 0x00, 0x00, 0x00, 0x00],
    OPAL_UID.C_PIN_TABLE: [0x00, 0x00, 0x00, 0x0B, 0x00, 0x00, 0x00, 0x00],
    OPAL_UID.LOCKING_INFO_TABLE: [0x00, 0x00, 0x08, 0x01, 0x00, 0x00, 0x00, 0x01],
    OPAL_UID.PSID: [0x00, 0x00, 0x00, 0x09, 0x00, 0x01, 0xff, 0x01],
    OPAL_UID.C_PIN_MSID: [0x00, 0x00, 0x00, 0x0B, 0x00, 0x00, 0x84, 0x02],
    OPAL_UID.C_PIN_SID: [0x00, 0x00, 0x00, 0x0B, 0x00, 0x00, 0x00, 0x01],
    OPAL_UID.C_PIN_ADMIN1: [0x00, 0x00, 0x00, 0x0B, 0x00, 0x01, 0x00, 0x01],
    OPAL_UID.C_PIN_USER1: [0x00, 0x00, 0x00, 0x0B, 0x00, 0x03, 0x00, 0x01],
    OPAL_UID.HALF_AUTHORITY_OBJ_REF: [0x00, 0x00, 0x0C, 0x05, 0xff, 0xff, 0xff, 0xff],
    OPAL_UID.HALF_BOOLEAN_ACE: [0x00, 0x00, 0x04, 0x0E, 0xff, 0xff, 0xff, 0xff]
}


opal_method_table = {
    OPAL_METHOD.PROPERTIES: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x01],
    OPAL_METHOD.STARTSESSION: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x02],
    OPAL_METHOD.REVERT: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x02, 0x02],
    OPAL_METHOD.ACTIVATE: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x02, 0x03],
    OPAL_METHOD.NEXT: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x08],
    OPAL_METHOD.GETACL: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x0d],
    OPAL_METHOD.GENKEY: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x10],
    OPAL_METHOD.REVERTSP: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x11],
    OPAL_METHOD.GET: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x16],
    OPAL_METHOD.SET: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x17],
    OPAL_METHOD.AUTHENTICATE: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x1c],
    OPAL_METHOD.RANDOM: [0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x06, 0x01]
}


class Command(object):
    def __init__(self, nvme0, comid):
        self.buf = Buffer(2048, "TCG Command Buffer")
        self.nvme0 = nvme0
        self.comid = comid
        self.buf[:8] = struct.pack('>IHH', 0, comid, 0)
        self.pos = 0x38  # append position

    def send(self, append_end_tokens=True):
        if append_end_tokens:
            self.append_token_list(OPAL_TOKEN.ENDOFDATA,
                                   OPAL_TOKEN.STARTLIST,
                                   0, 0, 0,
                                   OPAL_TOKEN.ENDLIST)

        # fill length
        assert self.pos > 56 # larger than header
        self.buf[52:] = struct.pack('>I', self.pos-56)
        while self.pos%4:
            # padding to dword
            self.append_u8(0)
        self.buf[16:] = struct.pack('>I', self.pos-20)
        self.buf[40:] = struct.pack('>I', self.pos-44)
        assert self.pos < 2048
        
        # send packet
        logging.debug(self.buf.dump(512))
        self.nvme0.security_send(self.buf, self.comid).waitdone()
        return self

    def append_u8(self, val):
        self.buf[self.pos] = val
        self.pos += 1

    def append_u16(self, val):
        self.buf[self.pos:] = struct.pack('>H', val)
        self.pos += 2

    def append_token(self, token):
        self.append_u8(token)

    def append_token_uid(self, u):
        uid = opal_uid_table[u]
        self.append_u8(0xa0+len(uid))
        self.append_token_list(*uid)
        
    def append_token_method(self, m):
        method = opal_method_table[m]
        self.append_u8(0xa0+len(method))
        self.append_token_list(*method)

    def append_token_list(self, *val_list):
        for val in val_list:
            self.append_u8(val)

    def append_token_atom(self, atom):
        if type(atom) == int:
            if atom < 64:
                # tiny
                self.append_u8(atom)
            elif atom < 0x100:
                # short: 1-byte int
                self.append_u8(0x81)
                self.append_u8(atom)
            elif atom < 0x10000:
                # short: 2-byte int
                self.append_u8(0x82)
                self.append_u16(atom)
            else:
                # TODO: medium and long atom
                assert False
        else:
            assert type(atom) == bytes
            if len(atom) < 16:
                # short
                self.append_u8(0xa0 + len(atom))
            elif len(atom):
                # medium
                self.append_u8(0xd0)
                self.append_u8(len(atom))
            self.append_token_list(*list(atom))

    def _start_session(self, hsn):
        self.append_token(OPAL_TOKEN.CALL)
        self.append_token_uid(OPAL_UID.SMUID)
        self.append_token_method(OPAL_METHOD.STARTSESSION)
        self.append_token(OPAL_TOKEN.STARTLIST)
        self.append_token_atom(hsn)
        self.append_token_uid(OPAL_UID.ADMINSP)
        self.append_token(OPAL_TOKEN.TRUE)

    def start_anybody_adminsp_session(self, hsn):
        self._start_session(hsn)
        self.append_token(OPAL_TOKEN.ENDLIST)
        return self

    def start_adminsp_session(self, hsn, key):
        self._start_session(hsn)
        self.append_token(OPAL_TOKEN.STARTNAME)
        self.append_token(0)
        self.append_token_atom(key)
        self.append_token_list(OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.STARTNAME,
                               3)
        self.append_token_uid(OPAL_UID.SID)
        self.append_token(OPAL_TOKEN.ENDNAME)
        self.append_token(OPAL_TOKEN.ENDLIST)
        return self
    
    def revert_tper(self, hsn, tsn):
        self.append_token(OPAL_TOKEN.CALL)
        self.append_token_uid(OPAL_UID.ADMINSP)
        self.append_token_method(OPAL_METHOD.REVERT)
        self.append_token(OPAL_TOKEN.STARTLIST)
        self.append_token(OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self
    
    def set_sid_cpin_pin(self, hsn, tsn, new_passwd):
        self.append_token(OPAL_TOKEN.CALL)
        self.append_token_uid(OPAL_UID.C_PIN_SID)
        self.append_token_method(OPAL_METHOD.SET)
        self.append_token_list(OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.VALUES,
                               OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.PIN)
        self.append_token_atom(new_passwd)
        self.append_token_list(OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self
    
    def get_msid_cpin_pin(self, hsn, tsn):
        self.append_token(OPAL_TOKEN.CALL)
        self.append_token_uid(OPAL_UID.C_PIN_MSID)
        self.append_token_method(OPAL_METHOD.GET)
        self.append_token_list(OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.STARTCOLUMN,
                               OPAL_TOKEN.PIN,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.ENDCOLUMN,
                               OPAL_TOKEN.PIN,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST,
                               OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self
    
    def end_session(self, hsn, tsn):
        self.append_u8(OPAL_TOKEN.ENDOFSESSION)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self

    def properties(self, host_properties={}):
        self.append_token(OPAL_TOKEN.CALL)
        self.append_token_uid(OPAL_UID.SMUID)
        self.append_token_method(OPAL_METHOD.PROPERTIES)
        self.append_token_list(OPAL_TOKEN.STARTLIST, 
                               OPAL_TOKEN.STARTNAME,
                               0)   #host properties list
        self.append_token(OPAL_TOKEN.STARTLIST)

        for k in host_properties:
            self.append_token(OPAL_TOKEN.STARTNAME)
            self.append_token_atom(k)
            self.append_token_atom(host_properties[k])
            self.append_token(OPAL_TOKEN.ENDNAME)

        self.append_token(OPAL_TOKEN.ENDLIST)
        self.append_token(OPAL_TOKEN.ENDNAME)
        self.append_token(OPAL_TOKEN.ENDLIST)
        
        return self

    
class Response(object):
    def __init__(self, nvme0, comid=1):
        self.nvme0 = nvme0
        self.comid = comid
        self.buf = Buffer(2048, "TCG Response Buffer")

    def receive(self):
        self.nvme0.security_receive(self.buf, self.comid).waitdone()
        logging.debug(self.buf.dump(512))
        return self
    
    def level0_discovery(self):
        total_length, ver, _ = struct.unpack('>IIQ', self.buf[:16])
        total_length += 4
        offset = 48
        while offset < total_length:
            feature, version, length = struct.unpack('>HBB', self.buf[offset:offset+4])
            version >>= 4
            length += 4

            # parse discovery response buffer
            if feature == 0x0303 or \
               feature == 0x0302:
                # pyrite 2, or pyrite 1
                comid, = struct.unpack('>H', self.buf[offset+4:offset+6])
                
            offset += length
        assert offset == total_length
        return comid

    def start_session(self):
        hsn = struct.unpack(">I", self.buf[0x4d:0x51])
        tsn = struct.unpack(">I", self.buf[0x52:0x56])
        return hsn[0], tsn[0]

    def get_c_pin_msid(self):
        length = struct.unpack(">B", self.buf[0x3d:0x3e])[0]
        return self.buf[0x3e:0x3e+length]


def test_properties(nvme0):
    host_properties = {
        b"MaxComPacketSize": 4096,
        b"MaxPacketSize": 4076,
        b"MaxIndTokenSize": 4040, 
        b"MaxPackets": 1, 
        b"MaxSubPackets": 1, 
        b"MaxMethods": 1,
    }
    comid = Response(nvme0).receive().level0_discovery()
    Command(nvme0, comid).properties().send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).properties(host_properties).send()
    Response(nvme0, comid).receive()

    
def test_take_ownership_and_revert_tper(nvme0, new_passwd=b'123456'):
    comid = Response(nvme0).receive().level0_discovery()

    Command(nvme0, comid).start_anybody_adminsp_session(0x65).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).get_msid_cpin_pin(hsn, tsn).send()
    password = Response(nvme0, comid).receive().get_c_pin_msid()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()

    Command(nvme0, comid).start_adminsp_session(0x66, password).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).set_sid_cpin_pin(hsn, tsn, new_passwd).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    
    Command(nvme0, comid).start_adminsp_session(0x69, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).revert_tper(hsn, tsn).send()
    Response(nvme0, comid).receive()
    # No "end session" for revert tper
