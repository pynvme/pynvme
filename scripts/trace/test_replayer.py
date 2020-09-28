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


import pytest
import logging
import zipfile

import nvme as d

import PySimpleGUI as sg


def test_replay_pynvme_trace(nvme0, nvme0n1, accelerator=1.0):
    filename = sg.PopupGetFile('select the trace file to replay', 'pynvme')
    if filename:
        logging.info(filename)

        # format before replay
        nvme0n1.format(512)
        
        responce_time = [0]*1000000
        replay_logfile(filename, nvme0n1, nvme0.mdts, accelerator, responce_time)

        import matplotlib.pyplot as plt
        plt.plot(responce_time)
        plt.xlabel('useconds')
        plt.ylabel('# IO')
        plt.xlim(1, len(responce_time))
        plt.ylim(bottom=1)
        plt.xscale('log')
        plt.yscale('log')
        plt.title(filename)
        plt.tight_layout()

        plt.show()


def replay_logfile(filename, nvme0n1, mdts, accelerator, responce_time):
    zfile = zipfile.ZipFile(filename)
    files = zfile.namelist()
    files.sort()
    
    fid = nvme0n1.id_data(26)%16
    format_support = nvme0n1.id_data(128+fid*4+3, 128+fid*4)
    data_size = (1<<((format_support>>16)&0xff))
    max_lba = mdts//data_size
    logging.info(max_lba)

    opcode = {b'flush': 0,
              b'write': 1,
              b'read': 2,
              b'write_zeroes': 8,
              b'trims': 9}

    output_percentile_latency = dict.fromkeys([99.9])
    
    # replay 4 trace at once for 4 qid
    progress = 0
    sg.OneLineProgressMeter('pynvme replayer',
                            progress, len(files),
                            'progress',
                            orientation='h')

    for start in range(0, len(files), 4):
        ioworkers = []

        # start 4 ioworkers
        io_sequences = [[], [], [], []]
        for i in range(4):
            filepath = files[start+i]
            for line in zfile.open(filepath):
                line = line.split()
                time = int(float(line[0])/accelerator)
                op = opcode[line[1]]
                slba = int(line[2])
                nlba = int(line[3])
                if b'write' in line or b'read' in  line:
                    while nlba:
                        n = min(nlba, max_lba)
                        io_sequences[i].append((time, op, slba, n))
                        slba += n
                        nlba -= n
                else:
                    io_sequences[i].append((time, op, slba, nlba))

            # add a dummy io to force ioworker run
            io_sequences[i].append((300*1000000/accelerator, 0, 0, 1))

        for i in range(4):
            logging.info("replaying IO in trace file %d" % (start+i))
            w = nvme0n1.ioworker(io_sequence=io_sequences[i],
                                 output_percentile_latency=output_percentile_latency,
                                 ptype=0xbeef, pvalue=100).start()
            ioworkers.append(w)

        # wait all ioworkers complete
        rs = [[], [], [], []]
        for i, w in enumerate(ioworkers):
            rs[i] = w.close()

        for i in range(4):
            for j in range(1000000):
                responce_time[j] += rs[i].latency_distribution[j]

            # GUI progress
            progress += 1
            sg.OneLineProgressMeter('pynvme replayer',
                                    progress, len(files),
                                    'progress',
                                    orientation='h')            
