from py_aduc_upload import AducConnection

def test_verify_shift():
    ad=AducConnection()
    shifted=ad._verifyShift([0x01<<b for b in range(8)])
    print(['0x%02x'%s for s in shifted])

def test_checksum():
    ad=AducConnection()
    print(ad._checksum([0x05,0x52,0x00,0x00,0x00,0x01]))