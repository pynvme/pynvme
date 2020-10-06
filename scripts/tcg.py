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
import warnings

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
        assert self.pos > 56  # larger than header
        self.buf[52:] = struct.pack('>I', self.pos-56)
        while self.pos % 4:
            # padding to dword
            self.append_u8(0)
        self.buf[16:] = struct.pack('>I', self.pos-20)
        self.buf[40:] = struct.pack('>I', self.pos-44)
        assert self.pos < 2048

        # send packet
        logging.debug(self.buf.dump(256))
        self.nvme0.security_send(self.buf, self.comid).waitdone()
        return self

    def append_u8(self, val):
        self.buf[self.pos] = val
        self.pos += 1

    def append_u16(self, val):
        self.buf[self.pos:] = struct.pack('>H', val)
        self.pos += 2

    def append_u32(self, val):
        self.buf[self.pos:] = struct.pack('>I', val)
        self.pos += 4

    def append_u64(self, val):
        self.buf[self.pos:] = struct.pack('>Q', val)
        self.pos += 8

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
            self.append_u8(int(val))

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
            elif atom < 0x100000000:
                # medium: 4-byte int
                self.append_u8(0x84)
                self.append_u32(atom)
            else:
                # long: 8-byte int
                self.append_u8(0x88)
                self.append_u64(atom)
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

    def start_anybody_adminsp_session(self, hsn):
        self._start_session(hsn)
        self.append_token_uid(OPAL_UID.ADMINSP)
        self.append_token(OPAL_TOKEN.TRUE)
        self.append_token(OPAL_TOKEN.ENDLIST)
        return self

    def start_adminsp_session(self, hsn, key):
        self._start_session(hsn)
        self.append_token_uid(OPAL_UID.ADMINSP)
        self.append_token(OPAL_TOKEN.TRUE)
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

    def start_auth_session(self, hsn, user_id, key):
        self._start_session(hsn)
        self.append_token_uid(OPAL_UID.LOCKINGSP)
        self.append_token(OPAL_TOKEN.TRUE)
        self.append_token(OPAL_TOKEN.STARTNAME)
        self.append_token(0)
        self.append_token_atom(key)
        self.append_token_list(OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.STARTNAME,
                               3)
        if user_id == 0:
            self.append_token_uid(OPAL_UID.ADMIN1)
        elif user_id == 1:
            self.append_token_uid(OPAL_UID.USER1)
        elif user_id == 2:
            self.append_token_uid(OPAL_UID.USER2)
        else:
            assert False, "not supported user id %d" % user_id
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

    def get_locking_sp_lifecycle(self, hsn, tsn):
        self.append_token(OPAL_TOKEN.CALL)
        self.append_token_uid(OPAL_UID.LOCKINGSP)
        self.append_token_method(OPAL_METHOD.GET)
        self.append_token_list(OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.STARTCOLUMN,
                               OPAL_TOKEN.LIFECYCLE,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.ENDCOLUMN,
                               OPAL_TOKEN.LIFECYCLE,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST,
                               OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self

    def activate(self, hsn, tsn):
        self.append_token(OPAL_TOKEN.CALL)
        self.append_token_uid(OPAL_UID.LOCKINGSP)
        self.append_token_method(OPAL_METHOD.ACTIVATE)
        self.append_token_list(OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self

    def setup_range(self, hsn, tsn, range, slba=0, nlb=0):
        range_uid = opal_uid_table[OPAL_UID.LOCKINGRANGE_GLOBAL][:]
        if range:  # not global
            range_uid[5] = 3
            range_uid[7] = range

        self.append_token(OPAL_TOKEN.CALL)
        self.append_u8(0xa0+len(range_uid))
        self.append_token_list(*range_uid)
        self.append_token_method(OPAL_METHOD.SET)
        self.append_token_list(OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.VALUES,
                               OPAL_TOKEN.STARTLIST)
        
        if range:
            self.append_token_list(OPAL_TOKEN.STARTNAME,
                                   OPAL_TOKEN.RANGESTART)
            self.append_token_atom(slba)
            self.append_token_list(OPAL_TOKEN.ENDNAME,
                                   OPAL_TOKEN.STARTNAME,
                                   OPAL_TOKEN.RANGELENGTH)
            self.append_token_atom(nlb)
            self.append_token_list(OPAL_TOKEN.ENDNAME)
            
        self.append_token_list(OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.READLOCKENABLED,
                               OPAL_TOKEN.TRUE,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.WRITELOCKENABLED,
                               OPAL_TOKEN.TRUE,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self

    def gen_new_key(self, hsn, tsn, range, prev_data):
        self.append_token(OPAL_TOKEN.CALL)
        self.append_u8(0xa0+len(prev_data))
        self.append_token_list(*prev_data)
        self.append_token_method(OPAL_METHOD.GENKEY)
        self.append_token_list(OPAL_TOKEN.STARTLIST, OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self

    def get_active_key(self, hsn, tsn, range):
        range_uid = opal_uid_table[OPAL_UID.LOCKINGRANGE_GLOBAL][:]
        if range:  # not global
            range_uid[5] = 3
            range_uid[7] = range

        self.append_token(OPAL_TOKEN.CALL)
        self.append_u8(0xa0+len(range_uid))
        self.append_token_list(*range_uid)
        self.append_token_method(OPAL_METHOD.GET)
        self.append_token_list(OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.STARTCOLUMN,
                               OPAL_TOKEN.ACTIVEKEY,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.ENDCOLUMN,
                               OPAL_TOKEN.ACTIVEKEY,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST,
                               OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self

    def lock_unlock_range(self, hsn, tsn, range, rlock, wlock):
        range_uid = opal_uid_table[OPAL_UID.LOCKINGRANGE_GLOBAL][:]
        if range:  # not global
            range_uid[5] = 3
            range_uid[7] = range

        self.append_token(OPAL_TOKEN.CALL)
        self.append_u8(0xa0+len(range_uid))
        self.append_token_list(*range_uid)
        self.append_token_method(OPAL_METHOD.SET)
        self.append_token_list(OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.VALUES,
                               OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.READLOCKED,
                               rlock,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.WRITELOCKED,
                               wlock,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self

    def add_user_to_range(self, hsn, tsn, user, range, passwd, can_write=True):
        user_uid = opal_uid_table[OPAL_UID.USER1][:]
        user_uid[7] = user
        range_uid = opal_uid_table[OPAL_UID.LOCKINGRANGE_ACE_RDLOCKED+can_write][:]
        range_uid[7] = range
        auth_ref_uid = opal_uid_table[OPAL_UID.HALF_AUTHORITY_OBJ_REF][:4]
        boolean_ace_uid = opal_uid_table[OPAL_UID.HALF_BOOLEAN_ACE][:4]

        self.append_token(OPAL_TOKEN.CALL)
        self.append_u8(0xa0+len(range_uid))
        self.append_token_list(*range_uid)
        self.append_token_method(OPAL_METHOD.SET)
        self.append_token_list(OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.VALUES,
                               OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.BOOLEAN_EXPR,
                               OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME)

        self.append_u8(0xa0+len(auth_ref_uid))
        self.append_token_list(*auth_ref_uid)
        self.append_u8(0xa0+len(user_uid))
        self.append_token_list(*user_uid)
        self.append_token_list(OPAL_TOKEN.ENDNAME, OPAL_TOKEN.STARTNAME)
        self.append_u8(0xa0+len(auth_ref_uid))
        self.append_token_list(*auth_ref_uid)
        self.append_u8(0xa0+len(user_uid))
        self.append_token_list(*user_uid)
        self.append_token_list(OPAL_TOKEN.ENDNAME, OPAL_TOKEN.STARTNAME)
        self.append_u8(0xa0+len(boolean_ace_uid))
        self.append_token_list(*boolean_ace_uid)
        self.append_token_list(OPAL_TOKEN.TRUE,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST)
        self.buf[20:] = struct.pack('>I', tsn)
        self.buf[24:] = struct.pack('>I', hsn)
        return self

    def enable_user(self, hsn, tsn, user_id):
        user_uid = opal_uid_table[OPAL_UID.USER1][:]
        user_uid[7] = user_id

        self.append_token(OPAL_TOKEN.CALL)
        self.append_u8(0xa0+len(user_uid))
        self.append_token_list(*user_uid)
        self.append_token_method(OPAL_METHOD.SET)
        self.append_token_list(OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.VALUES,
                               OPAL_TOKEN.STARTLIST,
                               OPAL_TOKEN.STARTNAME,
                               OPAL_TOKEN.AUTH_ENABLE,
                               OPAL_TOKEN.TRUE,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST,
                               OPAL_TOKEN.ENDNAME,
                               OPAL_TOKEN.ENDLIST)
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

    def set_new_passwd(self, hsn, tsn, user_id, new_passwd):
        self.append_token(OPAL_TOKEN.CALL)
        if user_id == 0:
            self.append_token_uid(OPAL_UID.C_PIN_ADMIN1)
        elif user_id == 1:
            self.append_token_uid(OPAL_UID.C_PIN_USER1)
        else:
            assert False, "not supported user id %d" % user_id
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
                               0)  # host properties list
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
        self.parsed = []

    def receive(self, check_status=True):
        self.nvme0.security_receive(self.buf, self.comid).waitdone()
        logging.debug(self.buf.dump(256))

        def _parse_token(ptr, len, bytes):
            if bytes:
                # byte sequence
                self.parsed.append(self.buf[ptr+1:ptr+1+len])
            else:
                # int
                if len == 2:
                    pattern = ">H"
                elif len == 4:
                    pattern = ">I"
                else:
                    logging.info(len)
                    assert False
                l = struct.unpack(pattern, self.buf[ptr+1:ptr+1+len])
                self.parsed.append(l[0])

        # parse the buffer
        ptr = 0x38
        _size = struct.unpack(">H", self.buf[0x36:0x38])[0]
        while ptr < 0x38+_size:
            ch = self.buf.data(ptr)

            if ch < 0x80:
                # tiny
                self.parsed.append(ch)
            elif ch >= 0x80 and ch < 0xc0:
                # short atom
                _len = ch & 0xf
                _parse_token(ptr, _len, ch & 0x20)
                ptr += _len
            elif ch >= 0xc0 and ch < 0xe0:
                # medium
                _len = ((ch & 7) << 8)+self.buf.data(ptr+1)
                ptr += 1
                _parse_token(ptr, _len, ch & 0x10)
                ptr += _len
            elif ch >= 0xe0 and ch < 0xe4:
                # medium
                _len = self.buf.data(ptr+1, ptr+4)
                ptr += 3
                _parse_token(ptr, _len, ch & 0x2)
                ptr += _len

            ptr += 1

        # check status
        logging.debug(self.parsed)
        if check_status and len(self.parsed) >= 3:
            if self.parsed[-3]:
                warnings.warn("TCG response error: "+str(self.parsed))
        return self

    def level0_discovery(self):
        comid = 0
        total_length, ver, _ = struct.unpack('>IIQ', self.buf[:16])
        total_length += 4
        offset = 48
        while offset < total_length:
            feature, version, length = struct.unpack(
                '>HBB', self.buf[offset:offset+4])
            version >>= 4
            length += 4

            # parse discovery response buffer
            if feature == 0x0303 or \
               feature == 0x0302:
                # pyrite 2, or pyrite 1
                comid = struct.unpack('>H', self.buf[offset+4:offset+6])[0]

            offset += length
        assert offset == total_length
        assert comid, "no pyrite feature found"
        return comid

    def start_session(self):
        return self.parsed[2], self.parsed[3]

    def get_c_pin_msid(self):
        length = struct.unpack(">B", self.buf[0x3c:0x3d])[0]
        length = length & 0xf
        return self.parsed[1]

    def get_active_key(self):
        return self.parsed[1]


def test_properties(nvme0):
    host_properties = {
        b"MaxComPacketSize": 4096,
        b"MaxPacketSize": 4076,
        b"MaxIndTokenSize": 4040,
        b"MaxPackets": 1,
        b"MaxSubPackets": 1,
        b"MaxMethods": 1,
    }
    comid = Response(nvme0).receive(False).level0_discovery()
    Command(nvme0, comid).properties().send()
    Response(nvme0, comid).receive(False)
    Command(nvme0, comid).properties(host_properties).send()
    Response(nvme0, comid).receive(False)


def test_tcg_user_range(subsystem, nvme0, nvme0n1, qpair, buf, new_passwd=b'123456'):
    # subsystem.power_cycle()
    # nvme0.reset()

    nvme0n1.write(qpair, buf, 0).waitdone()
    nvme0n1.write(qpair, buf, 128).waitdone()
    nvme0n1.read(qpair, buf, 0).waitdone()
    nvme0n1.read(qpair, buf, 128).waitdone()

    comid = Response(nvme0).receive(False).level0_discovery()

    logging.info("test: take ownership")
    Command(nvme0, comid).start_anybody_adminsp_session(0x69).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    logging.debug("hsn 0x%x, tsn 0x%x" % (hsn, tsn))
    Command(nvme0, comid).get_msid_cpin_pin(hsn, tsn).send()
    password = Response(nvme0, comid).receive().get_c_pin_msid()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()

    logging.info("test: set password")
    Command(nvme0, comid).start_adminsp_session(0x69, password).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).set_sid_cpin_pin(hsn, tsn, new_passwd).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()

    logging.info("test: activate locking sp")
    Command(nvme0, comid).start_adminsp_session(0x69, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).get_locking_sp_lifecycle(hsn, tsn).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).activate(hsn, tsn).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()

    logging.info("test: setup range")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).setup_range(hsn, tsn, 1, 0, 128).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()

    logging.info("test: enable user")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).enable_user(hsn, tsn, 1).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()

    logging.info("test: change passwd")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).set_new_passwd(hsn, tsn, 1, b"654321").send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()

    logging.info("test: user session")
    Command(nvme0, comid).start_auth_session(0x69, 1, b"654321").send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).set_new_passwd(hsn, tsn, 1, b"111111").send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()

    logging.info("test: add user to range, readonly")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).add_user_to_range(hsn, tsn, 1, 1, new_passwd, False).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()

    logging.info("test: add user to range, readwrite")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).add_user_to_range(hsn, tsn, 1, 1, new_passwd, True).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()

    logging.info("test: unlock range, none")
    Command(nvme0, comid).start_auth_session(0x69, 1, b"111111").send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).lock_unlock_range(hsn, tsn, 1, True, True).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.read(qpair, buf, 0).waitdone()
    nvme0n1.read(qpair, buf, 128).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.write(qpair, buf, 0).waitdone()
    nvme0n1.write(qpair, buf, 128).waitdone()

    logging.info("test: unlock range, write only")
    Command(nvme0, comid).start_auth_session(0x69, 1, b"111111").send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).lock_unlock_range(hsn, tsn, 1, True, False).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.read(qpair, buf, 0).waitdone()
    nvme0n1.read(qpair, buf, 128).waitdone()
    nvme0n1.write(qpair, buf, 0).waitdone()
    nvme0n1.write(qpair, buf, 128).waitdone()

    logging.info("test: unlock range, read only")
    Command(nvme0, comid).start_auth_session(0x69, 1, b"111111").send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).lock_unlock_range(hsn, tsn, 1, False, True).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()
    nvme0n1.read(qpair, buf, 128).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.write(qpair, buf, 0).waitdone()
    nvme0n1.write(qpair, buf, 128).waitdone()

    logging.info("test: unlock range, read/write")
    Command(nvme0, comid).start_auth_session(0x69, 1, b"111111").send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).lock_unlock_range(hsn, tsn, 1, False, False).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.write(qpair, buf, 0).waitdone()
    nvme0n1.write(qpair, buf, 1).waitdone()
    nvme0n1.write(qpair, buf, 128).waitdone()
    nvme0n1.read(qpair, buf, 0).waitdone()
    logging.info(buf.dump(16))
    nvme0n1.read(qpair, buf, 1).waitdone()
    logging.info(buf.dump(16))
    nvme0n1.read(qpair, buf, 128).waitdone()
    logging.info(buf.dump(16))

    logging.info("test: erase range")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).get_active_key(hsn, tsn, 1).send()
    prev_data = Response(nvme0, comid).receive().get_active_key()
    Command(nvme0, comid).gen_new_key(hsn, tsn, 1, prev_data).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 1).waitdone()
    logging.info(buf.dump(16))
    nvme0n1.read(qpair, buf, 128).waitdone()
    logging.info(buf.dump(16))

    logging.info("test: revert")
    orig_timeout = nvme0.timeout
    nvme0.timeout = 100000
    Command(nvme0, comid).start_adminsp_session(0x69, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).revert_tper(hsn, tsn).send()
    Response(nvme0, comid).receive()
    # No "end session" for revert tper
    nvme0.timeout = orig_timeout
    nvme0n1.read(qpair, buf, 1).waitdone()
    logging.info(buf.dump(16))
    nvme0n1.read(qpair, buf, 128).waitdone()
    logging.info(buf.dump(16))


def test_tcg_admin_global(subsystem, nvme0, nvme0n1, qpair, buf, new_passwd=b'123456'):
    # subsystem.power_cycle()
    # nvme0.reset()

    nvme0n1.write(qpair, buf, 0).waitdone()
    nvme0n1.write(qpair, buf, 128).waitdone()
    nvme0n1.read(qpair, buf, 0).waitdone()
    nvme0n1.read(qpair, buf, 128).waitdone()

    comid = Response(nvme0).receive(False).level0_discovery()

    logging.info("test: take ownership")
    Command(nvme0, comid).start_anybody_adminsp_session(0x69).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    logging.debug("hsn 0x%x, tsn 0x%x" % (hsn, tsn))
    Command(nvme0, comid).get_msid_cpin_pin(hsn, tsn).send()
    password = Response(nvme0, comid).receive().get_c_pin_msid()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()

    logging.info("test: set password")
    Command(nvme0, comid).start_adminsp_session(0x69, password).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).set_sid_cpin_pin(hsn, tsn, new_passwd).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()

    logging.info("test: activate locking sp")
    Command(nvme0, comid).start_adminsp_session(0x69, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).get_locking_sp_lifecycle(hsn, tsn).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).activate(hsn, tsn).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()

    logging.info("test: setup range global")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).setup_range(hsn, tsn, 0).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()
    
    logging.info("test: unlock range, none")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).lock_unlock_range(hsn, tsn, 0, True, True).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.read(qpair, buf, 0).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.read(qpair, buf, 128).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.write(qpair, buf, 0).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.write(qpair, buf, 128).waitdone()

    logging.info("test: unlock range, readonly")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).lock_unlock_range(hsn, tsn, 0, False, True).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.read(qpair, buf, 0).waitdone()
    nvme0n1.read(qpair, buf, 128).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.write(qpair, buf, 0).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.write(qpair, buf, 128).waitdone()

    logging.info("test: unlock range, write only")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).lock_unlock_range(hsn, tsn, 0, True, False).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.read(qpair, buf, 0).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/86"):
        nvme0n1.read(qpair, buf, 128).waitdone()
    nvme0n1.write(qpair, buf, 0).waitdone()
    nvme0n1.write(qpair, buf, 128).waitdone()
        
    logging.info("test: unlock range, read write")
    Command(nvme0, comid).start_auth_session(0x69, 0, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).lock_unlock_range(hsn, tsn, 0, False, False).send()
    Response(nvme0, comid).receive()
    Command(nvme0, comid).end_session(hsn, tsn).send(False)
    Response(nvme0, comid).receive()
    nvme0n1.write(qpair, buf, 0, 8).waitdone()
    nvme0n1.write(qpair, buf, 128, 8).waitdone()
    nvme0n1.read(qpair, buf, 1).waitdone()
    assert buf[0] == 1
    nvme0n1.read(qpair, buf, 128).waitdone()
    assert buf[0] == 128
        
    logging.info("test: revert")
    orig_timeout = nvme0.timeout
    nvme0.timeout = 100000
    Command(nvme0, comid).start_adminsp_session(0x69, new_passwd).send()
    hsn, tsn = Response(nvme0, comid).receive().start_session()
    Command(nvme0, comid).revert_tper(hsn, tsn).send()
    Response(nvme0, comid).receive()
    # No "end session" for revert tper
    nvme0.timeout = orig_timeout
    nvme0n1.read(qpair, buf, 1).waitdone()
    assert buf[0] == 0
    nvme0n1.read(qpair, buf, 128).waitdone()
    assert buf[0] == 0
