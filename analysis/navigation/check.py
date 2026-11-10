"""Bounded design checks. Pin freedom is not AF, routing or real-time validation."""
from pathlib import Path
import re
import math

ROOT = Path(__file__).resolve().parents[2]
RESERVED = {'52': 'SPI2_SCK/PB13', '53': 'SPI2_MISO/PB14',
            '54': 'SPI2_MOSI/PB15', '51': 'IMU_CS/PB12',
            '85': 'IMU_DRDY/PD3', '79': 'USART3_TX/PC10',
            '80': 'USART3_RX/PC11', '5': 'PPS/PE6', '86': 'BARO_CS/PD4'}
PENDING = {'4': 'FSR_SAMPLE_ENABLE/PE5'}

def netlist_pins(path=None):
    """Read U17 nodes in KiCad E netlist, ignoring explicit unconnected nets."""
    text = Path(path or ROOT / 'hardware/powerboard-reva/exports/powerboard-reva.net').read_text()
    used = {}
    for block in re.split(r'\(net \(code ', text)[1:]:
        match = re.search(r'\(name "([^"]+)"\)', block)
        if match is None: raise ValueError('missing net name')
        name = match.group(1)
        if name.startswith('unconnected-'): continue
        for pin in re.findall(r'\(node \(ref "U17"\) \(pin "(\d+)"\)', block):
            used[pin] = name
    if len(used) < 40: raise ValueError('unexpected/incomplete MCU netlist')
    return used

def conflicts(used, proposed):
    return sorted(set(proposed) & (set(used) | set(PENDING)), key=int)

def energy_wh(volts, milliamps, hours):
    if any(not math.isfinite(x) or x < 0 for x in (volts, milliamps, hours)):
        raise ValueError('finite non-negative inputs required')
    return volts * milliamps * hours / 1000

def spi_us(byte_count, hz):
    if byte_count < 0 or hz <= 0: raise ValueError('invalid SPI parameters')
    return byte_count * 8 / hz * 1_000_000

def uart_8n1_capacity(baud):
    """Payload bytes/s: one start + eight data + one stop bit per byte."""
    if not math.isfinite(baud) or baud <= 0:
        raise ValueError("finite positive baud required")
    return baud / 10

def log_bytes_per_second():
    # Assumptions: IMU 416Hz*32B, GNSS 10Hz*100B, wheel 50Hz*16B.
    return 416 * 32 + 10 * 100 + 50 * 16

if __name__ == '__main__':
    collision = conflicts(netlist_pins(), RESERVED)
    print('provisional pin conflicts:', collision)
    print('sensor-only 3.3V typical-current proxy Wh/1h:', energy_wh(3.3, 12.3532, 1))
    print('16-byte burst at 4MHz us:', spi_us(16, 4_000_000))
    print('logging B/s:', log_bytes_per_second())
    raise SystemExit(bool(collision))
