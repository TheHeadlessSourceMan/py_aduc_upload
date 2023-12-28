import typing
import win32file
import subprocess

def processUsingPort(port:str)->str:
    """
    NOTE: Works on Windows only
    """
    port=port[3:]
    def queryall(portType:str):
        try:
            for n in range(1000):
                dev=f'\\Device\\{portType}{n}'
                print(dev)
                p=win32file.QueryDosDevice(dev)
                print(p)
        except Exception as e:
            print(e)
    queryall('Serial')
    queryall('VCP')
    queryall('Silabser')

def processes(processName:str='PuTTY.exe'):
    """
    returns [pid,mem,cpu]
    """
    ret=[]
    cmd=["TASKLIST","/V","/NH","/FO","CSV","/FI",f"imagename eq {processName}"]
    po=subprocess.Popen(cmd,stdout=subprocess.PIPE)
    out,_=po.communicate()
    if out.find(b'No tasks are running')<0:
        for line in out.decode('utf-8',errors='ignore').strip().split('\n'):
            line=line.strip()[1:-1].split('","')
            mem=line[4].replace(',','').replace(' ','')
            mem=mem.replace('K','000').replace('M','000000').replace('G','000000000')
            ret.append((int(line[1]),int(mem),int(line[7].replace(':',''))))
    return ret

PORT_DEVICE_CLASS="{4D36E978-E325-11CE-BFC1-08002BE10318}"
def enumDevices(deviceClass:str)->typing.List[typing.Dict[str,str]]:
    cmd=['pnputil','/enum-devices','/connected','/class',deviceClass]
    po=subprocess.Popen(cmd,stdout=subprocess.PIPE)
    out,_=po.communicate()
    ret=[]
    for section in out.decode('utf-8',errors='ignore').strip().replace('\r','').split('\n\n')[1:]:
        vals={}
        for line in section.split('\n'):
            if not line:
                break
            line=line.split(':',1)
            vals[line[0].strip().replace(' ','')]=line[1].strip()
        print(win32file.QueryDosDevice(vals['InstanceID']))
        ret.append(vals)
    return ret

print(enumDevices(PORT_DEVICE_CLASS))