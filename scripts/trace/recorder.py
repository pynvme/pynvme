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


#!/usr/bin/python3

import os
import sys
import time
import math
import shutil
import logging
import zipfile

import matplotlib.pyplot as plt
import multiprocessing as mp
import PySimpleGUI as sg
import numpy as np

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


def create_trace_file(dirname_full, dirname, current_dir, openfiles):
    if dirname != current_dir:
        # create new folders for trace files
        current_dir = dirname
        os.makedirs(dirname_full)
        for i in range(4):
            filename = dirname_full+'/%d'%(i+1)
            print("create minute trace file %s" % filename)
            openfiles[filename] = open(filename, 'w')
            
    return current_dir


def trace_io_file(usec, line, openfile):
    # trace file by mintue and qid

    usec = str(usec)
    if line[0] == 'trims':
        nrange = int(line[1])
        line = line[2:]
        for i in range(nrange):
            openfile.write(' '.join([usec, 'trims', line[2*i], line[2*i+1]]) + os.linesep)
        # verify the trace file format
        assert int(line[nrange*2]) == nrange
    elif line[0] == 'write' or line[0] == 'read':
        openfile.write(' '.join([usec, *line]) + os.linesep)
    elif line[0] == 'flush':
        openfile.write(' '.join([usec, 'flush', '0', '0']) + os.linesep)

        
def trace_io_diagram(line, usec, X, Y, C):        
    # io sequence diagram
    if line[0] == 'trims':
        nrange = int(line[1])
        line = line[2:]
        for i in range(nrange):
            X.append(usec/1000000)
            Y.append(int(line[2*i]))
            a = min(0.99, 0.5+math.log(1+int(line[2*i+1]), 2)/20)
            C.append((0, 0, 1, a))
    elif line[0] == 'write' or line[0] == 'read':
        X.append(usec/1000000)
        Y.append(int(line[1]))
        a = min(0.99, 0.3+math.log(1+int(line[2]), 2)/10)
        if line[0] == 'write':
            C.append((1, 0, 0, a))
        elif line[0] == 'read':
            C.append((0, 1, 0, a))
            

def generate_trace_file(base_dir, zip_filename):
    # compress all trace files into a single zip file
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                zf.write(os.path.join(root, file))


def watermark_text(input_image_path, output_image_path, text, pos):
    photo = Image.open(input_image_path)
    drawing = ImageDraw.Draw(photo)
    font = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", 96)
    drawing.text(pos, text, fill=(0, 0, 255), font=font)
    photo.save(output_image_path)

        
# generate io sequence picture
def generate_trace_diagram(X, Y, C, trace_filename):
    plt.scatter(X, Y, c=C, s=0.3)
    raw_trace_filename = 'raw_'+trace_filename
    
    plt.xlabel('seconds')
    plt.ylabel('LBA')
    plt.xlim(left=0)
    plt.ylim(0, 128*1024*1024*1024//512)
    plt.tight_layout()
    
    plt.savefig(raw_trace_filename, bbox_inches='tight', dpi=600)
    plt.show()

    # add the pynvme watermark
    watermark_text(raw_trace_filename, trace_filename,
                   text='replay this trace file with pynvme',
                   pos=(800, 30))
    os.remove(raw_trace_filename)


def recorder_run(queue, base_dir, X, Y, C):
    # remove tmp files
    try:
        shutil.rmtree(base_dir)
    except:
        pass
    os.makedirs(base_dir)

    time_base = int(sys.stdin.readline().split()[1])
    counter = 0
    current_dir = None
    openfiles = {}
    print("trace time base %d" % time_base)
    for l in sys.stdin:
        try:
            return queue.get_nowait()
        except:
            pass

        if 'pynvme' in l:
            _, usec, qid, *line = l.split()
            global_usec = int(usec)-time_base
            dirname = str(global_usec//300000000)
            usec = global_usec%300000000
            dirname_full = base_dir+'/'+dirname
            current_dir = create_trace_file(dirname_full,
                                            dirname,
                                            current_dir,
                                            openfiles)
            filename = dirname_full+'/%d'%int(qid)
            trace_io_file(usec, line, openfiles[filename])

            # draw head io diagram
            counter += 1
            if counter<1000*1000*10 and counter%100 == 0:
                trace_io_diagram(line, global_usec, X, Y, C)


def recorder_stop_save(queue, base_dir, X, Y, C):
    print("generating IO trace file ...")
    zip_filename = "/tmp/pynvme_trace.zip"
    generate_trace_file(base_dir, zip_filename)
    
    trace_filename = 'pynvme_%s.trace.png' % time.strftime("%Y%m%d%H%M%S")
    generate_trace_diagram(X, Y, C, trace_filename)
    
    # merge zip into the picture
    with open(trace_filename, "ab") as myfile, \
         open(zip_filename, "rb") as file2:
        myfile.write(file2.read())

    print("trace file generated: " + trace_filename)

    # remove tmp files
    shutil.rmtree(base_dir)
    os.remove(zip_filename)

    for l in sys.stdin:
        try:
            return queue.get_nowait()
        except:
            #print(l, end = '')
            pass


def subprocess_gui(rqueue):
    state = 0
    msg = ["stop and save the trace", "start the trace"]
    while state is not None:
        ret = sg.PopupOKCancel(msg[state%2], "",
                               font = ("Helvetica", 18))
        if ret == "OK":
            state += 1
            rqueue.put(state)
        else:
            rqueue.put(None)
            return


if __name__ == "__main__":
    base_dir = '/tmp/pynvme_trace'
    queue = mp.Queue()
    p = mp.Process(target = subprocess_gui, args = (queue, ))
    p.start()
    
    while True:
        X = [] # time
        Y = [] # slba
        C = [] # nlba

        state = recorder_run(queue, base_dir, X, Y, C)
        if state is None:
            break
        
        state = recorder_stop_save(queue, base_dir, X, Y, C)
        if state is None:
            break

    p.join()
