import pytest
import nvme as d

import os
import openpyxl

def test_generate_report_xlsx():
    wb = openpyxl.load_workbook(filename='scripts/performance/report_template.xlsx')
    sheet = wb['pynvme']
    line = 0

    # copy report.csv into excel file
    with open("report.csv", "r") as f:
        for value in f.readlines():
            line += 1
            value = value[:-1]
            try:
                value = float(value)
            except:
                pass

            # write to the cell of the excel file
            sheet['C%d' % line] = value

    # save the file
    wb.save(filename='performance_report.xlsx')
    os.remove("report.csv")
