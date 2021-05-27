#!/usr/bin/env python
# -*- coding: utf-8 -*-

''' sysmap2elf.py
    Creates a dummy kernel image (vmlinux), importing symbols from system-map file
    The result image can be imported on gdb by using the command: symbol-file
'''

import os
import sys
import struct
import argparse
from binascii import unhexlify


# elf defs
SHN_UNDEF = 0
STB_GLOBAL = 1
STT_NOTYPE = 0
STT_OBJECT = 1
STT_FUNC = 2
SHT_NULL = 0
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3

# system-map types
SYSTEM_MAP_TYPES = {
    'B': STT_OBJECT,
    'b': STT_OBJECT,
    'D': STT_OBJECT,
    'd': STT_OBJECT,
    'R': STT_OBJECT,
    'r': STT_OBJECT,
    'T': STT_FUNC,
    't': STT_FUNC
}

# system-map type to elfsym type
def elfsymtype(sys_map_type):
    return SYSTEM_MAP_TYPES.get(sys_map_type, STT_NOTYPE)

def elf64_st_info(b, t):
    return ((b << 4) + (t & 0xf))

# dummy elf file
class Elf64Sym:
    def __init__(self, virt_base_addr, image_size):
        ehdr = '7f454c46020101000000000000000000'
        ehdr += '03003e00010000000000000000000000'
        ehdr += '00000000000000004000000000000000'
        ehdr += '00000000400038000000400005000400'
        self.__ehdr = unhexlify(ehdr)

        # section headers
        self.__shdr = struct.pack('<IIQQQQIIQQ', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        self.__shdr += struct.pack('<IIQQQQIIQQ', 1, SHT_PROGBITS, 7,
            virt_base_addr, 0x180, image_size, 0, 0, 16, 0)

        self.__shdr += struct.pack('<IIQQQQIIQQ', 10, SHT_SYMTAB, 0, 0, 0,
            0, 3, 0, 8, 24)

        self.__shdr += struct.pack('<IIQQQQIIQQ', 18, SHT_STRTAB, 0, 0, 0,
            0, 0, 0, 1, 0)

        self.__shdr += struct.pack('<IIQQQQIIQQ', 26, SHT_STRTAB, 0, 0, 0,
            0, 0, 0, 1, 0)

        # for now, all symbols will point to a single flat fixed-size section
        self.__text = b'\x90' * image_size
        self.__symtab = []
        self.__strtab = []
        self.__shstrtab = b'\x00.vmlinux\x00.symtab\x00.strtab\x00.shstrtab\x00'

        # fixups for sh_offset and sh_size
        self.__shdr_fixup = [
            [0xd8, 0x180+image_size],
            [0xe0, 0],

            [0x118, 0x180+image_size],
            [0x120, 0],

            [0x158, 0x180+image_size],
            [0x160, len(self.__shstrtab)]
        ]

        self.addsym('', STT_NOTYPE, 0)

    def addsym(self, sym_name, sym_type, sym_value):
        self.__strtab.append(sym_name)
        self.__symtab.append([0, elf64_st_info(STB_GLOBAL, sym_type), 0,
            1, sym_value, 0])

        self.__shdr_fixup[1][1] += 24
        self.__shdr_fixup[2][1] += 24
        self.__shdr_fixup[3][1] += len(sym_name) + 1
        self.__shdr_fixup[4][1] += 24 + len(sym_name) + 1

    def save(self, filename):
        elf_symtab_data = []
        elf_strtab_data = []
        elf_strtab_size = 0

        # set symtab and strtab
        for i in range(len(self.__strtab)):
            name = self.__strtab[i]
            sym = self.__symtab[i]

            strtab_entry = name.encode('utf-8') + unhexlify('00')
            elf_strtab_size += len(strtab_entry)
            elf_strtab_data.append(strtab_entry)
            sym[0] = elf_strtab_size - len(name) - 1

            data = struct.pack('<I', sym[0])
            data += struct.pack('B',  sym[1])
            data += struct.pack('B',  sym[2])
            data += struct.pack('<H', sym[3])
            data += struct.pack('<Q', sym[4])
            data += struct.pack('<Q', sym[5])
            elf_symtab_data.append(data)

        # save file
        with open(filename, 'wb') as f:
            f.write(self.__ehdr)
            f.write(self.__shdr)
            f.write(self.__text)
            f.write(unhexlify('').join(elf_symtab_data))
            f.write(unhexlify('').join(elf_strtab_data))
            f.write(self.__shstrtab)

            # apply fixup
            for off, value in self.__shdr_fixup:
                f.seek(off)
                f.write(struct.pack('<Q', value))

def sysmap_parse_line(line):
    s = line.split()
    return s[0], s[1], s[2]

def get_startup_64_addr(system_map_path):
    with open(system_map_path) as sysmap:
        for line in sysmap:
            sym_addr, sym_type, sym_name = sysmap_parse_line(line)
            if sym_name == 'startup_64':
                return int(sym_addr, 16)
    return None

def gen_kernel_syms(system_map_path, virt_base, out_path):
    old_virt_base = get_startup_64_addr(system_map_path)
    if not old_virt_base:
        print('Error: symbol "startup_64" not found')
        return False

    elfsym = Elf64Sym(virt_base, 0x3200000)
    with open(system_map_path) as sysmap:
        for line in sysmap:
            sym_addr, sym_type, sym_name = sysmap_parse_line(line)
            sym_addr = int(sym_addr, 16)
            if sym_addr >= old_virt_base:
                new_sym_addr = sym_addr - old_virt_base + virt_base
                elfsym.addsym(sym_name, elfsymtype(sym_type), new_sym_addr)

    elfsym.save(out_path)
    return True

def _int(var):
    return int(var, 0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-o', metavar='output',  default='vmlinux.elf',
            help='output filename [default=vmlinux.elf]')
    parser.add_argument('--startup', metavar='startup', type=_int,
            default=0xffffffff81000000, help='startup address [0xffffffff81000000]')
    parser.add_argument('sysmap', metavar='SYSTEM-MAP-FILE', help='filename')

    args = parser.parse_args()
    if not os.path.isfile(args.sysmap):
        print('Error: file not found: %s' % args.sysmap)
        sys.exit(1)

    gen_kernel_syms(args.sysmap, args.startup, args.o)

