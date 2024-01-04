#!/usr/bin/env python3
"""
Programatically update #define's
"""
import typing
import os
import datetime


def cppQuote(s:typing.Any)->str:
    """
    Return anything as a properly quoted and escaped c string.
    """
    return '"'+str(s)\
        .replace('\\',r'\\').replace('\t',r'\t').replace('\r',r'\r')\
        .replace('\n',r'\n').replace('\0',r'\0').replace('"',r'\"')+'"'


def getPoundDefines(
    filenames:typing.Union[str,typing.Iterable[str]],
    defaults:typing.Optional[typing.Dict[str,str]]=None
    )->typing.Dict[str,str]:
    """
    get all #defines from c files.

    :filenames: one or more filenames

    returns a dict
    """
    if defaults is not None:
        ret=dict(defaults)
    else:
        ret={}
    if isinstance(filenames,str):
        filenames=[filenames]
    for filename in filenames:
        with open(filename,'rb') as f:
            code=f.read().decode('utf-8',errors="ignore")
        for line in code.split('\n'):
            line=line.split('//',1)[0].split(maxsplit=2)
            if len(line)>1 and line[0]=='#define':
                if len(line)>2:
                    ret[line[1]]=line[2]
                else:
                    ret[line[1]]=''
    return ret


def replacePoundDefinesInFile(filename:str,
    name2val:typing.Dict[str,typing.Union[int,float,bool,str]],
    quotestrings=True
    )->None:
    """
    Opens/creates a c++ file and changes/adds a series of #define statements

    :filename: existing data to replace #defines in
    :quotestrings: enclose passed in str values in "".  (default=True) if False,
        you can do "clever" things like replacePoundDefines('x.h','MY_MACRO(x)':'printf("%d",x)')

    NOTE: Does not enforce all caps names.  That's on you.
    NOTE: Attempts to use existing line endings.
    NOTE: Will add a newline at the end of the file if not present.
    """
    filename=os.path.abspath(os.path.expandvars(filename))
    code=''
    try:
        with open(filename,'rb') as f:
            code=f.read().decode('ascii')
    except FileNotFoundError:
        pass
    code=replacePoundDefinesInCode(code,name2val,quotestrings)
    with open(filename,'wb') as f:
        f.write(code.encode('ascii'))


def replacePoundDefinesInCode(existingCode:str='',
    name2val:typing.Optional[typing.Dict[str,typing.Union[int,float,bool,str]]]=None,
    quotestrings=True
    )->str:
    """
    Optionally takes existing c++ code and changes/adds a series of #define statements

    :existingCode: existing data to replace #defines in
    :quotestrings: enclose passed in str values in "".  (default=True) if False,
        you can do "clever" things like replacePoundDefines('x.h','MY_MACRO(x)':'printf("%d",x)')

    NOTE: Does not enforce all caps names.  That's on you.
    NOTE: Attempts to use existing line endings.
    NOTE: Will add a newline at the end of the file if not present.
    """
    if name2val is None:
        return existingCode
    def fixval(val):
        if quotestrings and isinstance(val,str):
            return cppQuote(val)
        return str(val)
    newData:typing.List[str]=[]
    replaced:typing.Set[str]=set()
    insertAt=None # if there are new items, insert here
    crlf=existingCode.find('\r')>=0
    if crlf:
        data=existingCode.replace('\r','').split('\n')
    else:
        data=existingCode.split('\n')
    for lineNo,line in enumerate(data):
        if line.startswith('#define'):
            lineparts=line.split(maxsplit=3)
            name=lineparts[1].split('(',1)[0]
            replacedLine=False
            for k,v in name2val.items():
                name2=k.split('(',1)[0].strip()
                if name==name2:
                    newData.append(f'#define {k} {fixval(v)}')
                    replacedLine=True
                    replaced.add(k)
            if not replacedLine:
                newData.append(line)
            insertAt=lineNo+1
        elif line.startswith('#'):
            insertAt=lineNo+1
            newData.append(line)
        else:
            newData.append(line)
    if insertAt is None:
        # didn't find a natural place to insert more #define's
        # try to stuff it after any head comments
        insertAt=0
        blockcomment=False
        for lineNo,line in enumerate(data):
            line=line.strip()
            if not line:
                pass
            if line.startswith('/*'):
                blockcomment=True
            elif line.startswith('//'):
                insertAt=lineNo+1
            elif blockcomment:
                if line.endswith('*/'):
                    insertAt=lineNo+1
            else:
                break
    # add everything not found
    for k,v in name2val.items():
        if k not in replaced:
            newData.insert(insertAt,f'#define {k} {fixval(v)}')
    # add terminating newline
    if not newData or newData[-1].strip():
        newData.append('')
    if crlf:
        return '\r\n'.join(newData)
    return '\n'.join(newData)


def updateVersionInFile(
    filename:str='version.h',
    version:typing.Optional[str]=None,
    buildDate:typing.Union[None,str,datetime.datetime]=datetime.datetime.now(),
    name2val:typing.Optional[typing.Dict[str,typing.Union[int,float,bool,str]]]=None,
    quotestrings:bool=True):
    """
    Optionally takes existing c++ code and changes/adds a series of #define statements
    especially VERSION and/or BUILD_DATE

    This can also do other replacements as well by using replacePoundDefinesInFile()

    :existingCode: existing data to replace #defines in
    :version: version to update. can be None.
    :buildDate: build date to update. can be None. default is now()
    :quotestrings: enclose passed in str values in "".  (default=True) if False,
        you can do "clever" things like replacePoundDefines('x.h','MY_MACRO(x)':'printf("%d",x)')
        This does not affect VERSION or BUILD_DATE, which are always strings

    NOTE: Does not enforce all caps names.  That's on you.
    NOTE: Attempts to use existing line endings.
    NOTE: Will add a newline at the end of the file if not present.
    """
    code=''
    filename=os.path.abspath(os.path.expandvars(filename))
    try:
        with open(filename,'rb') as f:
            code=f.read().decode('ascii')
    except FileNotFoundError:
        pass
    code=updateVersionInCode(code,version,buildDate,name2val,quotestrings)
    with open(filename,'wb') as f:
        f.write(code.encode('ascii'))


def updateVersionInCode(
    existingCode:str='',
    version:typing.Optional[str]=None,
    buildDate:typing.Union[None,str,datetime.datetime]=datetime.datetime.now(),
    name2val:typing.Optional[typing.Dict[str,typing.Union[int,float,bool,str]]]=None,
    quotestrings:bool=True
    )->str:
    """
    Optionally takes existing c++ code and changes/adds a series of #define statements
    especially VERSION and/or BUILD_DATE

    This can also do other replacements as well by using replacePoundDefinesInCode()

    :existingCode: existing data to replace #defines in
    :version: version to update. can be None.
    :buildDate: build date to update. can be None. default is now()
    :quotestrings: enclose passed in str values in "".  (default=True) if False,
        you can do "clever" things like replacePoundDefines('x.h','MY_MACRO(x)':'printf("%d",x)')
        This does not affect VERSION or BUILD_DATE, which are always strings

    NOTE: Does not enforce all caps names.  That's on you.
    NOTE: Attempts to use existing line endings.
    NOTE: Will add a newline at the end of the file if not present.
    """
    if name2val is None:
        name2val={}
    else:
        name2val=dict(name2val)
    if version is not None:
        if not quotestrings:
            # quote it ourselves
            version=cppQuote(version)
        name2val['VERSION']=version
    if buildDate is not None:
        if not isinstance(buildDate,str):
            buildDate=buildDate.astimezone().isoformat()
        if not quotestrings:
            # quote it ourselves
            buildDate=cppQuote(buildDate)
        name2val['BUILD_DATE']=buildDate
    return replacePoundDefinesInCode(existingCode,name2val,quotestrings)


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    printhelp=False
    filename=''
    version:typing.Optional[str]=None
    buildDate:typing.Union[None,str,datetime.datetime]=None
    name2val:typing.Dict[str,str]={}
    quotestrings:bool=False
    justValue=False
    definesToGet:typing.List[str]=[]
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            avl=av[0].lower()
            if avl=='-h':
                printhelp=True
            elif avl=='-d':
                pass # deal with this later
            if avl=='-v':
                justValue=True
            elif avl=='--version':
                version=av[1].strip()
            elif avl=='--build_date':
                if len(av)>1:
                    buildDate=av[1].strip()
                else:
                    buildDate=datetime.datetime.now().astimezone()
            elif avl in ('--get_define','--get_defines'):
                if len(av)>1:
                    for item in av[1].split(','):
                        definesToGet.append(item.strip())
                else:
                    definesToGet.append('*')
            elif av[0].startswith('--'):
                if len(av)>1:
                    name2val[av[0][2:]]=av[1]
                else:
                    name2val[av[0][2:]]='true'
            else:
                printhelp=True
        else:
            filename=arg
    if not filename:
        printhelp=True
    elif filename=='STDIN':
        code=sys.stdin.read()
        code=updateVersionInCode(code,version,buildDate,name2val,quotestrings) # type: ignore
        print(code)
    else:
        updateVersionInFile(filename,version,buildDate,name2val,quotestrings) # type: ignore
    if '-d' in args:
        if buildDate is None:
            print(datetime.datetime.now().astimezone().isoformat())
        elif isinstance(buildDate,str):
            print(buildDate)
        else:
            print(buildDate.astimezone().isoformat())
        printhelp=False
    if definesToGet:
        defines=getPoundDefines(filename)
        if '*' in definesToGet:
            definesToGet=[str(k) for k in defines.keys()]
        for item in definesToGet:
            val=defines.get(item)
            if justValue:
                if val[0]=='"':
                    val=val.replace('"','')
                elif val[0]=="'":
                    val=val.replace("'",'')
                print(f"{val}")
            else:
                print(f"{item} = {val}")
    if printhelp:
        print('USEAGE:')
        print('  update_pound_defines [options] [filename]')
        print('OPTIONS:')
        print('  -h .................... this help')
        print('  -d  ................... dump the build date')
        print('  --version= ............ update the version')
        print('  --build_date[=date]  .. update the build date')
        print('                          if date not specified, use now()')
        print('  --[name]=[val]  ....... update anything else')
        print('  --get_define[s][=name] . get a defined value from the file')
        print('                          happens after everything is set')
        print('                          can have multiple get_define options')
        print('                          if name not specified, get all')
        print('                          will not run C preprocesor, but gets value as-is')
        print('  -v .................... make get_define show just the value(not the name=)')
        print('FILENAME:')
        print('  If the filename is STDIN it will read the file bytes from standard in')
        print('  and dump the result back to standard out')
        return 1
    return 0


if __name__=='__main__':
    import sys
    sys.exit(cmdline(sys.argv[1:]))