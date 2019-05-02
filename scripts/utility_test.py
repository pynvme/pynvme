import pytest
import logging

import nvme as d


def test_format(nvme0: d.Controller, nvme0n1):
    nvme0.format(0).waitdone()

    
def test_gui(nvme0):
    import PySimpleGUI as sg
    event, (filename,) = sg.Window('Get filename example'). Layout([[sg.Text('Filename')], [sg.Input(), sg.FileBrowse()], [sg.OK(), sg.Cancel()] ]).Read()
    logging.info(filename)
    
