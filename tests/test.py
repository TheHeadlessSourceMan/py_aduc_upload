import sys
import os
os.environ['PYTHONPATH'].()
sys.path.append('../')
from py_aduc_upload import AducConnection

def test_verify_shift():
    ad=AducConnection()
    shifted=ad._verifyShift([0x01<<b for b in range(8)])
    print(['0x%02x'%s for s in shifted])

def test_checksum()->bool:
    ad=AducConnection()
    tests=[ # (data,expected)
        ([0x05,0x52,0x00,0x00,0x00,0x01],0x00),
        ([],0x),
        ([06 45 00 00 00 00 01 b4 00 00 00 00 00 00   ...E.....´......	
    00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   ................	
    00 07 07 07 0e 06 45 00 00 00 00 01],0xb4)
        ]
    ret=True
    for data,expected in tests:
        result=ad._checksum(data) # ignore pylint:protected-access
        if result==expected:
            isok="PASS"
        else:
            isok="FAIL"
            ret=False
        print(f'{data} = {result} expected {expected} ... {isok}')
    return ret

test_checksum()
