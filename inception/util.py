'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2012  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jun 19, 2011

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy <n@tropy.org>
'''
from inception import cfg
from subprocess import call
import binascii
import os
import platform
import sys
import subprocess
import time


def hexstr2bytes(s):
    '''
    Takes a string of hexadecimal characters preceded by '0x' and returns the
    corresponding byte string. That is, '0x41' becomes b'A'
    '''
    if isinstance(s, str) and s.startswith('0x'):
        s = s.replace('0x', '') # Remove '0x' strings from hex string
        if len(s) % 2 == 1: s = '0' + s # Pad with zero if odd-length string
        return binascii.unhexlify(bytes(s, sys.getdefaultencoding()))
    else:
        raise BytesWarning('Not a string starting with \'0x\': {0}'.format(s))
    

def bytes2hexstr(b):
    '''
    Takes a string of bytes and returns a string with the corresponding
    hexadecimal representation. Example: b'A' becomes '0x41'
    '''
    if isinstance(b, bytes):
        return '0x' + bytes.decode(binascii.hexlify(b))
    else:
        raise BytesWarning('Not a byte string')
        

def bytelen(s):
    '''
    Returns the byte length of an integer
    '''
    return (len(hex(s))) // 2


def int2binhex(i):
    '''
    Converts positive integer to its binary hexadecimal representation
    '''
    if i < 0:
        raise TypeError('Not a positive integer: {0}'.format(i))
    return hexstr2bytes(hex(i))


def open_file(filename, mode):
    '''
    Opens a file that are a part of the package. The file must be in the folder
    tree beneath the main package
    '''
    this_dir, this_filename = os.path.split(__file__) #@UnusedVariable
    path = os.path.join(this_dir, filename)
    return open(path, mode)
    

def get_termsize():
    try:
        with open(os.devnull, 'w') as fnull:
            r, c = subprocess.check_output(['stty','size'], stderr = fnull).split() #@UnusedVariable
        cfg.termwidth = int(c)
        return int(c)
    except:
        warn('Cannot detect terminal column width')
        return cfg.termwidth

def print_wrapped(s, indent = True, end_newline = True):
    '''
    Prints a line and wraps each line at terminal width
    '''
    if not indent:
        default_indent = cfg.wrapper.subsequent_indent # Save default indent
        cfg.wrapper.subsequent_indent = ''
    wrapped = '\n'.join(cfg.wrapper.wrap(str(s)))
    if not end_newline:
        print(wrapped, end = ' ')
    else:
        print(wrapped)
    if not indent:
        cfg.wrapper.subsequent_indent = default_indent # Restore default indent


def info(s, sign = '*'):
    '''
    Print an informational message with '*' as a sign
    '''
    print_wrapped('[{0}] {1}'.format(sign, s))


def poll(s, sign = '?'):
    '''
    Prints a question to the user
    '''
    print_wrapped('[{0}] {1}'.format(sign, s), end_newline = False)
    
    
def warn(s, sign = '!'):
    '''
    Prints a warning message with '!' as a sign
    '''
    print_wrapped('[{0}] {1}'.format(sign, s))
    
    
def fail(err = None):
    '''
    Called if Inception fails. Optional parameter is an error message string.
    '''
    if err: warn(err)
    warn('Attack unsuccessful')
    sys.exit(1)


def separator():
    '''
    Prints a separator line with the width of the terminal
    '''
    print('-' * cfg.termwidth)
    

def parse_unit(size):
    '''
    Parses input in the form of a number and a (optional) unit and returns the
    size in either multiplies of the page size (if no unit is given) or the
    size in KiB, MiB or GiB
    '''
    size = size.lower()
    if size.find('kib') != -1 or size.find('kb') != -1:
        size = int(size.rstrip(' kib')) * cfg.KiB
    elif size.find('mib') != -1 or size.find('mb') != -1:
        size = int(size.rstrip(' mib')) * cfg.MiB
    elif size.find('gib') != -1 or size.find('gb') != -1:
        size = int(size.rstrip(' gib')) * cfg.GiB
    else:
        size = int(size) * cfg.PAGESIZE
    return size


def needtoavoid(address):
    '''
    Checks if the address given as parameter is within the memory regions that
    the tool should avoid to make sure no kernel panics are induced at the
    target
    '''
    avoid = []
    if cfg.apple_target:
        avoid = cfg.apple_avoid # Avoid this region if dumping from Macs
    else:
        avoid = cfg.avoid # Avoid this region if dumping memory from PCs
    return avoid[0] <= address <= avoid[1] and not cfg.filemode


def detectos():
    '''
    Detects host operating system
    '''
    return platform.system()


def unload_fw_ip():
    '''
    Unloads IP over FireWire modules if present on OS X
    '''
    poll('IOFireWireIP on OS X may cause kernel panics. Unload? [Y/n]: ')
    unload = input().lower()
    if unload in ['y', '']:
        status = call('kextunload /System/Library/Extensions/IOFireWireIP.kext',
                      shell=True)
        if status == 0:
            info('IOFireWireIP.kext unloaded')
            info('To reload: sudo kextload /System/Library/Extensions/' +
                 'IOFireWireIP.kext')
        else:
            fail('Could not unload IOFireWireIP.kext')


def restart():
    '''
    Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function.
    '''
    python = sys.executable
    os.execl(python, python, * sys.argv)


class MemoryFile:
    '''
    File that exposes a similar interface as the FireWire class. Used for
    reading from RAM memory files of memory dumps
    '''

    def __init__(self, file_name, pagesize):
        '''
        Constructor
        '''
        self.file = open(file_name, mode='r+b')
        self.pagesize = pagesize
    
    def read(self, addr, numb, buf=None):
        self.file.seek(addr)
        return self.file.read(numb)  
    
    def readv(self, req):
        for r in req:
            self.file.seek(r[0])
            yield (r[0], self.file.read(r[1]))
    
    def write(self, addr, buf):
        if cfg.forcewrite:
            poll('Are you sure you want to write to file [y/N]? ')
            answer = input().lower()
            if answer in ['y', 'yes']:
                self.file.seek(addr)
                self.file.write(buf)
        else:
            warn('File not patched. To enable file writing, use the ' +
                 '--force-write switch')
    
    def close(self):
        self.file.close()
    
    
class ProgressBar:
    '''
    Builds and display a text-based progress bar
    
    Based on https://gist.github.com/3306295
    '''

    def __init__(self, min_value=0, max_value=100, total_width=80, 
                 print_data = False):
        '''
        Initializes the progress bar
        '''
        self.progbar = ''   # This holds the progress bar string
        self.old_progbar = ''
        self.min = min_value
        self.max = max_value
        self.span = max_value - min_value
        self.width = total_width - len(' 4096 MiB (100%)')
        self.unit = cfg.MiB
        self.unit_name = 'MiB'
        self.print_data = print_data
        if self.print_data:
            self.data_width = total_width // 5
            if self.data_width % 2 != 0:
                self.data_width = self.data_width + 1
            self.width = self.width - (len(' {}') + self.data_width)
        else:
            self.data_width = 0
        self.amount = 0       # When amount == max, we are 100% done 
        self.update_amount(0)  # Build progress bar string


    def append_amount(self, append):
        '''
        Increases the current amount of the value of append and 
        updates the progress bar to new ammount
        '''
        self.update_amount(self.amount + append)
    
    def update_percentage(self, new_percentage):
        '''
        Updates the progress bar to the new percentage
        '''
        self.update_amount((new_percentage * float(self.max)) / 100.0)
        

    def update_amount(self, new_amount=0, data = b'\x00'):
        '''
        Update the progress bar with the new amount (with min and max
        values set at initialization; if it is over or under, it takes the
        min or max value as a default
        '''
        if new_amount < self.min: new_amount = self.min
        if new_amount > self.max: new_amount = self.max
        self.amount = new_amount
        rel_amount = new_amount - self.min

        # Figure out the new percent done, round to an integer
        diff_from_min = float(self.amount - self.min)
        percent_done = (diff_from_min / float(self.span)) * 100.0
        percent_done = int(round(percent_done))

        # Figure out how many hash bars the percentage should be
        all_full = self.width - 2
        num_hashes = (percent_done / 100.0) * all_full
        num_hashes = int(round(num_hashes))

        # Build a progress bar with an arrow of equal signs; special cases for
        # empty and full
        if num_hashes == 0:
            self.progbar = '[>{0}]'.format(' ' * (all_full - 1))
        elif num_hashes == all_full:
            self.progbar = '[{0}]'.format('=' * all_full)
        else:
            self.progbar = '[{0}>{1}]'.format('=' * (num_hashes - 1),
                                              ' ' * (all_full - num_hashes))

        # Generate string
        percent_str = '{0:>4d} {1} ({2:>3}%)'.format(rel_amount // self.unit,
                                                     self.unit_name,
                                                     percent_done)
        
        # If we are to print data, append it
        if self.print_data:
            data_hex = bytes.decode(binascii.hexlify(data))
            data_str = ' {{{0:0>{1}.{1}}}}'.format(data_hex, self.data_width)
            percent_str = percent_str + data_str    

        # Slice the percentage into the bar
        self.progbar = ' '.join([self.progbar, percent_str])
    
    def draw(self):
        '''
        Draws the progress bar if it has changed from it's previous value
        '''
        if self.progbar != self.old_progbar:
            self.old_progbar = self.progbar
            sys.stdout.write(self.progbar + '\r')
            sys.stdout.flush() # force updating of screen

    def __str__(self):
        '''
        Returns the current progress bar
        '''
        return str(self.progbar)
    

class BeachBall:
    '''
    An ASCII beach ball
    '''
    
    def __init__(self, max_frequency = 0.1):
        self.states = ['-', '\\', '|', '/']
        self.state = 0
        self.max_frequency = max_frequency
        self.time_drawn = time.time()
        
    def draw(self, force = False):
        '''
        Draws the beach ball if the dime delta since last draw is greater than
        the max_frequency
        '''
        now = time.time()
        if self.max_frequency < now - self.time_drawn or force:
            self.state = (self.state + 1) % len(self.states)
            print('[{0}]\r'.format(self.states[self.state]), end = '')
            sys.stdout.flush()
            self.time_drawn = now
