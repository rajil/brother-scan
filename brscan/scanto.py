import subprocess
import os
import datetime
import wand.image
import glob
import time
import tempfile
import shutil
from pathlib import PurePath, Path

def pnmtopdf(pnmfile, pdffile, resolution=None):
    with wand.image.Image(filename=pnmfile, resolution=resolution) as pnm:
        with pnm.convert('pdf') as pdf:
            pdf.save(filename=pdffile)
    os.remove(pnmfile)

scan_options = {
    'device': '--device-name',
    'resolution': '--resolution',
    'mode': '--mode',
    'source': '--source',
    'brightness': '--brightness',
    'contrast': '--contrast',
    'width': '-x',
    'height': '-y',
    'left': '-l',
    'top': '-t',
}

def add_scan_options(cmd, options):
    for name, arg in scan_options.items():
        if name in options:
            cmd += [arg, str(options[name])]
    cmd = [ str(c) for c in cmd ]

def scanto(func, options):
    print('scanto %s %s'%(func, options))
    options = options.copy()

    dst = tempfile.mkdtemp()
    if not 'dir' in options:
        options['dir'] = '/tmp'
    consumedir = options['dir']

    if not 'tmpdir' in options:
        options['tmpdir'] = '/tmp/duplex'
    tmpdir = options['tmpdir']

    os.makedirs(dst, exist_ok=True)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    adf = options.pop('adf', False)
    duplex = options.pop('duplex', False)
    if duplex:
        os.makedirs(tmpdir, exist_ok=True)

    if adf:
        if not duplex:
            cmd = ['scanadf',
                   '--output-file', os.path.join(dst, 'scan_%s_%%d.pnm'%(now))]
        else:
            cmd = ['scanadf',
                   '--output-file', os.path.join(tmpdir, 'scan_%s_%%d.pnm'%(now))]
        add_scan_options(cmd, options)
        print('# ' + ' '.join(cmd))
        subprocess.call(cmd)
        pnmfiles = []
        pdffiles = []

        if not duplex:
            for pnmfile in glob.glob(os.path.join(dst, 'scan_%s_*.pnm'%(now))):
                pdffile = '%s.pdf'%(pnmfile[:-4])
                pnmtopdf(pnmfile, pdffile, options['resolution'])
                pnmfiles.append(pnmfile)
                #pdffiles.append(pdffile)
                pdffiles.insert(0,pdffile)
        else:
            for pnmfile in glob.glob(os.path.join(tmpdir, 'scan_%s_*.pnm'%(now))):
                pdffile = '%s.pdf'%(pnmfile[:-4])
                pnmtopdf(pnmfile, pdffile, options['resolution'])
                pnmfiles.append(pnmfile)
                pdffiles.append(pdffile)

        if not duplex:
            cmd = ['pdfunite'] + pdffiles + [os.path.join(consumedir, 'scan_%s.pdf'%(now))]
        else:
            if os.path.exists(os.path.join(tmpdir, 'odd.pdf')):
                cmd = ['pdfunite'] + pdffiles + [os.path.join(tmpdir, 'even.pdf')]
            else:
                cmd = ['pdfunite'] + pdffiles + [os.path.join(tmpdir, 'odd.pdf')]

        print('# ' + ' '.join(cmd))
        subprocess.call(cmd)
        time.sleep(3)
        if duplex:
            if os.path.exists(os.path.join(tmpdir, 'even.pdf')):
                cmdS = 'pdftk A=' + os.path.join(tmpdir, 'odd.pdf') + ' B=' + os.path.join(tmpdir, 'even.pdf') + ' shuffle Aend-1 B output ' + os.path.join(consumedir, 'scan_%s.pdf'%(now))
                subprocess.call(cmdS, shell=True)
                os.remove(os.path.join(tmpdir, 'even.pdf'))
                os.remove(os.path.join(tmpdir, 'odd.pdf'))
        for f in pdffiles:
            os.remove(f)
        shutil.rmtree(dst)
    else:
        cmd = ['scanimage']
        add_scan_options(cmd, options)
        pnmfile = os.path.join(dst, 'scan_%s.pnm'%(now))
        with open(pnmfile, 'w') as pnm:
            print('# ' + ' '.join(cmd))
            process = subprocess.Popen(cmd, stdout=pnm)
            process.wait()
        pdffile = PurePath(consumedir, '%s.pdf'% (Path(pnmfile).name[:-4]))
        pnmtopdf(pnmfile, pdffile, options['resolution'])
        print('Wrote', pdffile)
        shutil.rmtree(dst)
