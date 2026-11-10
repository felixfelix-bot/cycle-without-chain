#!/usr/bin/env python3
"""
Render the parallel-hybrid vs series-hybrid comparison as a PNG.

Pure-Python PNG writer (no matplotlib/PIL dependency) so it runs anywhere.
Draws:  left  = SERIES hybrid (the chainless idea)
        right = PARALLEL hybrid (the recommendation)

Geometry is in an 1600x1000 canvas.
"""

import struct
import zlib

W, H = 1600, 1000
BG = (18, 20, 26)
PANEL = (28, 32, 42)
CHAIN_COL = (120, 200, 140)     # mechanical = green
ELEC_COL = (240, 190, 90)       # electrical = amber
LOST_COL = (235, 105, 95)       # loss = red
TXT = (232, 236, 245)
DIM = (150, 158, 175)
WHITE = (255, 255, 255)

px = bytearray()

def new_canvas():
    global px
    px = bytearray()
    for _ in range(W * H):
        px.extend(BG)

def setpx(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i] = c[0]; px[i+1] = c[1]; px[i+2] = c[2]

def rect(x0, y0, x1, y1, c):
    x0, x1 = max(0, int(x0)), min(W-1, int(x1))
    y0, y1 = max(0, int(y0)), min(H-1, int(y1))
    for y in range(y0, y1+1):
        base = (y * W) * 3
        for x in range(x0, x1+1):
            i = base + x*3
            px[i] = c[0]; px[i+1] = c[1]; px[i+2] = c[2]

def rect_a(x0, y0, x1, y1, c, a):
    """alpha blend"""
    x0, x1 = max(0, int(x0)), min(W-1, int(x1))
    y0, y1 = max(0, int(y0)), min(H-1, int(y1))
    for y in range(y0, y1+1):
        base = (y * W) * 3
        for x in range(x0, x1+1):
            i = base + x*3
            px[i]   = int(px[i]   * (1-a) + c[0] * a)
            px[i+1] = int(px[i+1] * (1-a) + c[1] * a)
            px[i+2] = int(px[i+2] * (1-a) + c[2] * a)

def rrect(x0, y0, x1, y1, r, c, fill=True, thick=3):
    """rounded rect outline or fill"""
    if fill:
        rect(x0+r, y0, x1-r, y1, c)
        rect(x0, y0+r, x0+r-1, y1-r, c)
        rect(x1-r+1, y0+r, x1, y1-r, c)
        for dx in range(r):
            for dy in range(r):
                if (dx-r)**2 + (dy-r)**2 <= r*r:
                    setpx(x0+r-dx-1, y0+r-dy-1, c)   # TL
                    setpx(x1-r+dx, y0+r-dy-1, c)     # TR
                    setpx(x0+r-dx-1, y1-r+dy, c)     # BL
                    setpx(x1-r+dx, y1-r+dy, c)       # BR
    else:
        for t in range(thick):
            rect(x0+r, y0+t, x1-r, y0+t, c)
            rect(x0+r, y1-t, x1-r, y1-t, c)
            rect(x0+t, y0+r, x0+t, y1-r, c)
            rect(x1-t, y0+r, x1-t, y1-r, c)
        for k in range(r):
            for t in range(thick):
                # approximate arc
                rr = r - k
                for dx in range(r):
                    dy = int((rr*rr - (r-t)**2) ** 0.5) if rr*rr-(r-t)**2 >= 0 else 0
                    setpx(x0+r-dx, y0+r-dy, c)
                    setpx(x1-r+dx, y0+r-dy, c)
                    setpx(x0+r-dx, y1-r+dy, c)
                    setpx(x1-r+dx, y1-r+dy, c)
                break

def hline(x0, x1, y, c, thick=4):
    rect(x0, y - thick//2, x1, y + thick//2, c)

def vline(x, y0, y1, c, thick=4):
    rect(x - thick//2, y0, x + thick//2, y1, c)

def arrow(x0, y0, x1, y1, c, thick=5, head=14):
    # simple: horizontal or vertical only
    if y0 == y1:
        d = 1 if x1 > x0 else -1
        hline(min(x0, x1), max(x0, x1) - d*head, y0, c, thick)
        for i in range(head):
            hw = int((head - i) * 0.6)
            rect(x1 - d*i - (0 if d > 0 else 0), y0 - hw, x1 - d*i, y0 + hw, c)
    else:
        d = 1 if y1 > y0 else -1
        vline(x0, min(y0, y1), max(y0, y1) - d*head, c, thick)
        for i in range(head):
            hw = int((head - i) * 0.6)
            rect(x0 - hw, y1 - d*i - (0 if d > 0 else 0), x0 + hw, y1 - d*i, c)

def circle(cx, cy, r, c, fill=True, thick=3):
    if fill:
        for y in range(cy-r, cy+r+1):
            for x in range(cx-r, cx+r+1):
                if (x-cx)**2 + (y-cy)**2 <= r*r:
                    setpx(x, y, c)
    else:
        for y in range(cy-r, cy+r+1):
            for x in range(cx-r, cx+r+1):
                d2 = (x-cx)**2 + (y-cy)**2
                if (r-thick)**2 <= d2 <= r*r:
                    setpx(x, y, c)

# ---------------------------------------------------------------- 5x7 font
FONT = {
 'A':["01110","10001","10001","11111","10001","10001","10001"],
 'B':["11110","10001","10001","11110","10001","10001","11110"],
 'C':["01110","10001","10000","10000","10000","10001","01110"],
 'D':["11110","10001","10001","10001","10001","10001","11110"],
 'E':["11111","10000","10000","11110","10000","10000","11111"],
 'F':["11111","10000","10000","11110","10000","10000","10000"],
 'G':["01110","10001","10000","10111","10001","10001","01111"],
 'H':["10001","10001","10001","11111","10001","10001","10001"],
 'I':["01110","00100","00100","00100","00100","00100","01110"],
 'J':["00111","00010","00010","00010","00010","10010","01100"],
 'K':["10001","10010","10100","11000","10100","10010","10001"],
 'L':["10000","10000","10000","10000","10000","10000","11111"],
 'M':["10001","11011","10101","10101","10001","10001","10001"],
 'N':["10001","11001","10101","10011","10001","10001","10001"],
 'O':["01110","10001","10001","10001","10001","10001","01110"],
 'P':["11110","10001","10001","11110","10000","10000","10000"],
 'Q':["01110","10001","10001","10001","10101","10010","01101"],
 'R':["11110","10001","10001","11110","10100","10010","10001"],
 'S':["01111","10000","10000","01110","00001","00001","11110"],
 'T':["11111","00100","00100","00100","00100","00100","00100"],
 'U':["10001","10001","10001","10001","10001","10001","01110"],
 'V':["10001","10001","10001","10001","10001","01010","00100"],
 'W':["10001","10001","10001","10101","10101","11011","10001"],
 'X':["10001","10001","01010","00100","01010","10001","10001"],
 'Y':["10001","10001","01010","00100","00100","00100","00100"],
 'Z':["11111","00001","00010","00100","01000","10000","11111"],
 '0':["01110","10001","10011","10101","11001","10001","01110"],
 '1':["00100","01100","00100","00100","00100","00100","01110"],
 '2':["01110","10001","00001","00010","00100","01000","11111"],
 '3':["11110","00001","00001","01110","00001","00001","11110"],
 '4':["00010","00110","01010","10010","11111","00010","00010"],
 '5':["11111","10000","11110","00001","00001","10001","01110"],
 '6':["00110","01000","10000","11110","10001","10001","01110"],
 '7':["11111","00001","00010","00100","01000","01000","01000"],
 '8':["01110","10001","10001","01110","10001","10001","01110"],
 '9':["01110","10001","10001","01111","00001","00010","01100"],
 ' ':["00000"]*7,
 '%':["11001","11010","00010","00100","01000","01011","10011"],
 '.':["00000","00000","00000","00000","00000","01100","01100"],
 ',':["00000","00000","00000","00000","01100","01100","11000"],
 ':':["00000","01100","01100","00000","01100","01100","00000"],
 '-':["00000","00000","00000","11111","00000","00000","00000"],
 '/':["00001","00010","00010","00100","01000","01000","10000"],
 '=':["00000","00000","11111","00000","11111","00000","00000"],
 '>':["01000","00100","00010","00001","00010","00100","01000"],
 '<':["00010","00100","01000","10000","01000","00100","00010"],
 '(':["00010","00100","01000","01000","01000","00100","00010"],
 ')':["01000","00100","00010","00010","00010","00100","01000"],
 '+':["00000","00100","00100","11111","00100","00100","00000"],
 '!':["00100","00100","00100","00100","00100","00000","00100"],
 "'":["00100","00100","00000","00000","00000","00000","00000"],
}

def text(x, y, s, c=TXT, sc=3):
    cx = x
    for ch in s.upper():
        g = FONT.get(ch, FONT[' '])
        for ry, row in enumerate(g):
            for rx, bit in enumerate(row):
                if bit == '1':
                    rect(cx + rx*sc, y + ry*sc,
                         cx + rx*sc + sc - 1, y + ry*sc + sc - 1, c)
        cx += 6 * sc
    return cx

def textw(s, sc=3):
    return len(s) * 6 * sc

def ctext(cx, y, s, c=TXT, sc=3):
    text(cx - textw(s, sc)//2, y, s, c, sc)

def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw.extend(px[y*W*3:(y+1)*W*3])
    comp = zlib.compress(bytes(raw), 9)
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', ihdr))
        f.write(chunk(b'IDAT', comp))
        f.write(chunk(b'IEND', b''))

# ============================================================== DRAW
new_canvas()

# title
ctext(W//2, 26, "TWO WAYS TO BUILD AN E-BIKE", WHITE, 5)
ctext(W//2, 70, "LEFT: THE CHAINLESS IDEA   /   RIGHT: THE RECOMMENDATION", DIM, 3)

# panels
rrect(36, 110, 776, 940, 18, PANEL, fill=True)
rrect(824, 110, 1564, 940, 18, PANEL, fill=True)

ctext(406, 132, "SERIES HYBRID  (CHAINLESS)", LOST_COL, 4)
ctext(406, 172, "ALL RIDER POWER GOES THROUGH THE ELECTRIC CHAIN", DIM, 2)

ctext(1194, 132, "PARALLEL HYBRID  (RECOMMENDED)", CHAIN_COL, 4)
ctext(1194, 172, "CHAIN KEEPS THE RIDER ON A DIRECT MECHANICAL PATH", DIM, 2)

# ---------------------------------------------------- LEFT: series
LX = 100
# crank
circle(170, 300, 46, (60, 66, 82))
circle(170, 300, 46, WHITE, fill=False, thick=3)
ctext(170, 290, "PEDAL", WHITE, 2)
ctext(170, 312, "CRANK", WHITE, 2)
# arrow to generator
arrow(220, 300, 300, 300, CHAIN_COL)
ctext(262, 272, "BELT", CHAIN_COL, 2)
ctext(262, 326, "20:1", CHAIN_COL, 2)

# generator
rrect(306, 236, 486, 364, 12, (52, 58, 74), fill=True)
rrect(306, 236, 486, 364, 12, ELEC_COL, fill=False, thick=3)
ctext(396, 258, "GENERATOR", WHITE, 2)
ctext(396, 288, "ALTERNATOR", ELEC_COL, 2)
ctext(396, 318, "42%", LOST_COL, 3)

arrow(492, 300, 560, 300, ELEC_COL)
# rectifier
rrect(566, 258, 700, 342, 10, (52, 58, 74), fill=True)
rrect(566, 258, 700, 342, 10, ELEC_COL, fill=False, thick=3)
ctext(633, 278, "DC BUS", WHITE, 2)
ctext(633, 306, "96%", DIM, 2)

# battery + caps down
arrow(633, 348, 633, 420, ELEC_COL)
rrect(520, 426, 746, 520, 12, (52, 58, 74), fill=True)
rrect(520, 426, 746, 520, 12, ELEC_COL, fill=False, thick=3)
ctext(633, 446, "BATTERY OR CAPS", WHITE, 2)
ctext(633, 476, "92%", DIM, 3)

# to controller
arrow(633, 526, 633, 596, ELEC_COL)
rrect(520, 602, 746, 686, 12, (52, 58, 74), fill=True)
rrect(520, 602, 746, 686, 12, ELEC_COL, fill=False, thick=3)
ctext(633, 622, "MOTOR CTRL", WHITE, 2)
ctext(633, 650, "95%", DIM, 2)

arrow(633, 692, 633, 762, ELEC_COL)
# hub motor
circle(633, 830, 62, (60, 66, 82))
circle(633, 830, 62, ELEC_COL, fill=False, thick=3)
ctext(633, 820, "HUB", WHITE, 2)
ctext(633, 842, "MOTOR", WHITE, 2)
ctext(633, 872, "90%", DIM, 2)

# big loss label
rrect(120, 700, 470, 900, 14, (48, 30, 34), fill=True)
ctext(295, 720, "RESULT", LOST_COL, 3)
ctext(295, 758, "32% PEDALS", LOST_COL, 3)
ctext(295, 792, "TO ROAD", LOST_COL, 3)
text(150, 830, "CAR ALT VARIANT", DIM, 2)
text(150, 856, "42% PEDAL GEN UNIT", DIM, 2)
text(150, 882, "61% BEST-CASE PM", DIM, 2)

# ---------------------------------------------------- RIGHT: parallel
RX = 880
# crank
circle(950, 300, 46, (60, 66, 82))
circle(950, 300, 46, WHITE, fill=False, thick=3)
ctext(950, 290, "PEDAL", WHITE, 2)
ctext(950, 312, "CRANK", WHITE, 2)

# chain straight to wheel  (green, thick, prominent)
arrow(1000, 300, 1310, 300, CHAIN_COL, thick=7, head=18)
ctext(1155, 266, "CHAIN 96%", CHAIN_COL, 3)
ctext(1155, 330, "MECHANICAL - DIRECT", CHAIN_COL, 2)

# rear wheel
circle(1380, 300, 66, (60, 66, 82))
circle(1380, 300, 66, CHAIN_COL, fill=False, thick=4)
ctext(1440, 296, "REAR", WHITE, 2)
ctext(1440, 318, "WHEEL", WHITE, 2)

# battery
rrect(880, 440, 1080, 534, 12, (52, 58, 74), fill=True)
rrect(880, 440, 1080, 534, 12, ELEC_COL, fill=False, thick=3)
ctext(980, 460, "LFP PACK", WHITE, 2)
ctext(980, 490, "480 WH", DIM, 2)

arrow(986, 540, 986, 610, ELEC_COL)
rrect(880, 616, 1080, 700, 12, (52, 58, 74), fill=True)
rrect(880, 616, 1080, 700, 12, ELEC_COL, fill=False, thick=3)
ctext(980, 636, "MOTOR CTRL", WHITE, 2)
ctext(980, 664, "95%", DIM, 2)

arrow(1086, 658, 1300, 658, ELEC_COL)
ctext(1190, 624, "86% BATTERY TO WHEEL", ELEC_COL, 2)

# motor in the hub -> wheel
circle(1380, 300, 66, (60, 66, 82))
arrow(1300, 380, 1360, 380, ELEC_COL)
ctext(1190, 380, "", DIM, 2)

# note the motor is IN the wheel - draw small hub
circle(1380, 300, 26, (90, 76, 44))
circle(1380, 300, 26, ELEC_COL, fill=False, thick=3)
ctext(1380, 296, "HUB", WHITE, 1)

# regen arrow back up
arrow(1380, 440, 1380, 380, LOST_COL, thick=4, head=12)
ctext(1380, 410, "", DIM, 1)

# efficiency result box
rrect(880, 740, 1520, 906, 14, (28, 44, 34), fill=True)
ctext(1200, 758, "RESULT", CHAIN_COL, 3)
text(910, 794, "RIDER PATH   96%   (NEVER TOUCHES ELECTRICS)", CHAIN_COL, 2)
text(910, 824, "MOTOR PATH   86%   BATTERY TO WHEEL", ELEC_COL, 2)
text(910, 854, "REGEN ROUND TRIP  63%", DIM, 2)
text(910, 884, "COAST DRAG ONLY 2 W  =  1.4% OF CRUISE", DIM, 2)

# bottom legend
rrect(36, 952, 1564, 990, 8, (24, 28, 36), fill=True)
rect(60, 966, 92, 976, CHAIN_COL)
text(104, 962, "MECHANICAL", DIM, 2)
rect(300, 966, 332, 976, ELEC_COL)
text(344, 962, "ELECTRICAL", DIM, 2)
rect(540, 966, 572, 976, LOST_COL)
text(584, 962, "LOSS / SHORTFALL", DIM, 2)
text(830, 962, "EFFICIENCIES ARE CITED MEASURED VALUES", DIM, 2)

write_png('/home/c08r4d0r/repos/cycle-without-chain/docs/analysis/parallel-vs-series.png')
print("wrote png")
