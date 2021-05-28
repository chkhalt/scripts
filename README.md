## **sysmap2elf:**  
Generates a dummy ELF file importing symbols from System-map.   
The file can be imported on gdb using the command "symbol-file".

```bash
# from host: start linux using qemu
$ qemu-system-x86_64 -m 2048 -drive file=packer-virtualbox.vmdk -snapshot -monitor stdio -s
QEMU 5.2.0 monitor - type 'help' for more information
(qemu)

# from guest: log and type 
$ sudo grep startup_64 /proc/kallsyms 
ffffffff9dc00000 T startup_64             # -> use this in the following command
ffffffff9dc00040 T secondary_startup_64
ffffffff9dc00045 T secondary_startup_64_no_verify
ffffffff9dc002f0 T __startup_64
ffffffff9dc006e0 T startup_64_setup_env

# from host: generate elf from System-map
$ sudo cat /proc/kallsyms > System-map-`uname -r`
$ ./sysmap2elf.py System-map-arch-5.12.4-arch1-2 --startup 0xffffffff9dc00000 -o vmlinux.elf

# start remote debugging
$ gdb -q
(gdb) target remote localhost:1234
Remote debugging using localhost:1234
warning: No executable has been specified and target does not support
determining executable automatically.  Try using the "file" command.
0xffffffff9208f67e in ?? ()

# import symbols
(gdb) symbol-file vmlinux.elf 
Reading symbols from vmlinux.elf...
(No debugging symbols found in vmlinux.elf)
(gdb) x/10i $rip
=> 0xffffffff9208f67e <native_safe_halt+14>:    ret    
   0xffffffff9208f67f <native_safe_halt+15>:    nop
   0xffffffff9208f680 <native_halt>:    jmp    0xffffffff9208f68c <native_halt+12>
   0xffffffff9208f685 <native_halt+5>:  verw   0x579bf6(%rip)        # 0xffffffff92609282 <ds.1>
   0xffffffff9208f68c <native_halt+12>: hlt    
   0xffffffff9208f68d <native_halt+13>: ret    
   0xffffffff9208f68e <native_halt+14>: int3   
   0xffffffff9208f68f <native_halt+15>: int3   
   0xffffffff9208f690 <cpu_idle_poll.isra.0>:   data16 data16 data16 xchg %ax,%ax
   0xffffffff9208f695 <cpu_idle_poll.isra.0+5>: push   %rbx
(gdb) b __x64_sys_bpf 
Breakpoint 1 at 0xffffffff917d2f00
(gdb) x/10i __x64_sys_bpf 
   0xffffffff917d2f00 <__x64_sys_bpf>:  data16 data16 data16 xchg %ax,%ax
   0xffffffff917d2f05 <__x64_sys_bpf+5>:        mov    0x68(%rdi),%rsi
   0xffffffff917d2f09 <__x64_sys_bpf+9>:        mov    0x60(%rdi),%edx
   0xffffffff917d2f0c <__x64_sys_bpf+12>:       mov    0x70(%rdi),%edi
   0xffffffff917d2f0f <__x64_sys_bpf+15>:       jmp    0xffffffff917d0ef0 <__do_sys_bpf>
   0xffffffff917d2f14 <__x64_sys_bpf+20>:       data16 nopw %cs:0x0(%rax,%rax,1)
   0xffffffff917d2f1f <__x64_sys_bpf+31>:       nop
   0xffffffff917d2f20 <__ia32_sys_bpf>: data16 data16 data16 xchg %ax,%ax
   0xffffffff917d2f25 <__ia32_sys_bpf+5>:       mov    0x58(%rdi),%esi
   0xffffffff917d2f28 <__ia32_sys_bpf+8>:       mov    0x60(%rdi),%edx
(gdb) 



```
