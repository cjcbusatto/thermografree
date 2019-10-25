import sys
import math
import numpy as np


# got from table with table number 114 in defs.h
TABLE_OFFSET = 1024
ADEXPBITS = 6
TAEQUIDISTANCE = 100
ADEQUIDISTANCE = 64

# files corresponding to table.c table
TABLE_FILE = 'table.csv'
IDX_TAS_FILE = 'idx_tas.csv'
IDX_ADS_FILE = 'idx_ads.csv'


table = np.loadtxt(TABLE_FILE, delimiter=',')
idx_tas = np.loadtxt(IDX_TAS_FILE, delimiter=',')
idx_ads = np.loadtxt(IDX_ADS_FILE, delimiter=',')


def get_col_left(ta):
    for col_left in range(0, len(idx_tas)-1):
        if idx_tas[col_left] <= ta and  idx_tas[col_left+1] > ta:
            break

    return col_left


def get_row_top(ad):
    row = int(round(ad + TABLE_OFFSET))
    row_top = row >> ADEXPBITS
    return row_top


def interpolate(rt, cl, dta, ad):
    val = ad + TABLE_OFFSET

    vx = (table[rt, cl+1] - table[rt, cl]) * (dta / TAEQUIDISTANCE) + table[rt, cl]
    vy = (table[rt+1, cl+1] - table[rt+1, cl]) * (dta / TAEQUIDISTANCE) + table[rt+1, cl]
    t = (vy - vx) * (val - idx_ads[rt]) / ADEQUIDISTANCE + vx

    return t


def get_temperature(ta, ad):
    col_left = get_col_left(ta)
    row_top = get_row_top(ad)
    dta = ta - idx_tas[col_left]

    t = interpolate(row_top, col_left, dta, ad)
    return t
    # print(t/10 - 273)


if __name__ == "__main__":
    ta = float(sys.argv[1])
    ad = float(sys.argv[2])

    t = get_temperature(ta, ad)





