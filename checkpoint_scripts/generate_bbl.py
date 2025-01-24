import os
import shutil
import subprocess
import os
import subprocess
import shutil
from config import BaseConfig
from typing import Tuple, List
from find_dynamic_lib import get_libraries_str
import subprocess

class RootfsBuilder(BaseConfig):
    def __init__(self, archive_buffer_layout, spec_info, path_env_vars_to_check=None, env_vars_to_check=None):
        """Initialize Builder with optional environment variables to check."""
        super().__init__(path_env_vars_to_check=path_env_vars_to_check, env_vars_to_check=env_vars_to_check)
        self.kernel_list: List[Tuple[str, str]] = []
        self.host_initramfs_list: List[Tuple[str, str]] = []
        self.opensbi_fw_payload: List[Tuple[str, str]] = []
        self.gcpt_bin_list: List[Tuple[str, str]] = []
        self.initramfs_list: List[Tuple[str, str]] = []
        self.rcs_list: list[Tuple[str, str]] = []
        self.config.update(
            **{
                "archive_buffer_layout": {
                    "scripts": archive_buffer_layout.get("scripts"),
                    "elf": archive_buffer_layout.get("elf"),
                    "logs_build": archive_buffer_layout.get("logs_build"),
                    "opensbi": archive_buffer_layout.get("opensbi"),
                    "linux": archive_buffer_layout.get("linux"),
                    "host_linux": archive_buffer_layout.get("host_linux"),
                    "gcpt": archive_buffer_layout.get("gcpt"),
                    "gcpt_bins": archive_buffer_layout.get("gcpt_bins"),
                    "assembly": archive_buffer_layout.get("assembly"),
                    "binary_archive": archive_buffer_layout.get("binary_archive"),
                },
                "spec_info": spec_info,
# original func is: https://github.com/OpenXiangShan/riscv-rootfs/blob/da983ec95858dfd6f30e9feadd534b79db37e618/rootfsimg/spec_gen.py#L499
                "default_initramfs_file": [
                    "dir /bin 755 0 0", "dir /etc 755 0 0", "dir /dev 755 0 0",
                    "dir /lib 755 0 0", "dir /proc 755 0 0", "dir /sbin 755 0 0",
                    "dir /sys 755 0 0", "dir /tmp 755 0 0", "dir /usr 755 0 0",
                    "dir /mnt 755 0 0", "dir /usr/bin 755 0 0", "dir /usr/lib 755 0 0",
                    "dir /usr/sbin 755 0 0", "dir /var 755 0 0", "dir /var/tmp 755 0 0",
                    "dir /root 755 0 0", "dir /var/log 755 0 0", "",
                    "nod /dev/console 644 0 0 c 5 1", "nod /dev/null 644 0 0 c 1 3", "",
                    "nod /dev/urandom 644 0 0 c 1 9", "nod /dev/random 644 0 0 c 1 8",
                    "", "# busybox",
                    "file /bin/busybox ${RISCV_ROOTFS_HOME}/rootfsimg/build/busybox 755 0 0",
                    "file /etc/inittab ${RISCV_ROOTFS_HOME}/rootfsimg/inittab-spec 755 0 0",
                    "slink /init /bin/busybox 755 0 0",
                    "slink /sbin/mdev /bin/busybox 755 0 0",
                    "", "# SPEC common",
                    "dir /spec_common 755 0 0",
                    "file /spec_common/before_workload ${RISCV_ROOTFS_HOME}/rootfsimg/build/before_workload 755 0 0",
                    "file /spec_common/trap ${RISCV_ROOTFS_HOME}/rootfsimg/build/trap 755 0 0",
                    "file /spec_common/qemu_trap ${RISCV_ROOTFS_HOME}/rootfsimg/build/qemu_trap 755 0 0",
                    "", "# SPEC"
#, "dir /spec 755 0 0",
#        "file /spec/run.sh ${RISCV_ROOTFS_HOME}/rootfsimg/run.sh 755 0 0"
                ],
                "default_initramfs_dirs": [
                    "dir /bin 755 0 0",
                    "dir /sbin 755 0 0",
                    "dir /usr 755 0 0",
                    "dir /usr/lib 755 0 0",
                    "dir /usr/bin 755 0 0",
                    "dir /usr/sbin 755 0 0",
                    "dir /etc 755 0 0",
                    "dir /etc/init.d 755 0 0",
                    "dir /dev 755 0 0",
                    "dir /proc 755 0 0",
                    "dir /sys 755 0 0",
                    "dir /lib 755 0 0",
                    "dir /tmp 755 0 0",
                    "dir /mnt 755 0 0",
                    "dir /var 755 0 0",
                    "dir /var/tmp 755 0 0",
                    "dir /root 755 0 0",
                    "dir /var/log 755 0 0",
                    "dir /apps 755 0 0",
                    "",
                    "nod /dev/console 644 0 0 c 5 1",
                    "nod /dev/null 644 0 0 c 1 3", "",
                    "nod /dev/urandom 644 0 0 c 1 9",
                    "nod /dev/random 644 0 0 c 1 8",
                ],
                "default_initramfs_busybox": [
                    "",  # /bin
                    "file /bin/busybox ${RISCV_ROOTFS_HOME}/rootfsimg/build/busybox 755 0 0",
                    "file /etc/fstab ${RISCV_ROOTFS_HOME}/rootfsimg/fstab 755 0 0",
                    "slink /init /bin/busybox 755 0 0",
                    "slink /bin/arch /bin/busybox 755 0 0",
                    "slink /bin/ash /bin/busybox 755 0 0",
                    "slink /bin/base64 /bin/busybox 755 0 0",
                    "slink /bin/bash /bin/busybox 755 0 0",
                    "slink /bin/cat /bin/busybox 755 0 0",
                    "slink /bin/chattr /bin/busybox 755 0 0",
                    "slink /bin/chgrp /bin/busybox 755 0 0",
                    "slink /bin/chmod /bin/busybox 755 0 0",
                    "slink /bin/chown /bin/busybox 755 0 0",
                    "slink /bin/conspy /bin/busybox 755 0 0",
                    "slink /bin/cp /bin/busybox 755 0 0",
                    "slink /bin/cpio /bin/busybox 755 0 0",
                    "slink /bin/cttyhack /bin/busybox 755 0 0",
                    "slink /bin/date /bin/busybox 755 0 0",
                    "slink /bin/dd /bin/busybox 755 0 0",
                    "slink /bin/df /bin/busybox 755 0 0",
                    "slink /bin/dmesg /bin/busybox 755 0 0",
                    "slink /bin/dnsdomainname /bin/busybox 755 0 0",
                    "slink /bin/dumpkmap /bin/busybox 755 0 0",
                    "slink /bin/echo /bin/busybox 755 0 0",
                    "slink /bin/ed /bin/busybox 755 0 0",
                    "slink /bin/egrep /bin/busybox 755 0 0",
                    "slink /bin/false /bin/busybox 755 0 0",
                    "slink /bin/fatattr /bin/busybox 755 0 0",
                    "slink /bin/fgrep /bin/busybox 755 0 0",
                    "slink /bin/fsync /bin/busybox 755 0 0",
                    "slink /bin/getopt /bin/busybox 755 0 0",
                    "slink /bin/grep /bin/busybox 755 0 0",
                    "slink /bin/gunzip /bin/busybox 755 0 0",
                    "slink /bin/gzip /bin/busybox 755 0 0",
                    "slink /bin/hostname /bin/busybox 755 0 0",
                    "slink /bin/hush /bin/busybox 755 0 0",
                    "slink /bin/iostat /bin/busybox 755 0 0",
                    "slink /bin/kbd_mode /bin/busybox 755 0 0",
                    "slink /bin/kill /bin/busybox 755 0 0",
                    "slink /bin/link /bin/busybox 755 0 0",
                    "slink /bin/linux32 /bin/busybox 755 0 0",
                    "slink /bin/linux64 /bin/busybox 755 0 0",
                    "slink /bin/ln /bin/busybox 755 0 0",
                    "slink /bin/login /bin/busybox 755 0 0",
                    "slink /bin/ls /bin/busybox 755 0 0",
                    "slink /bin/lsattr /bin/busybox 755 0 0",
                    "slink /bin/lzop /bin/busybox 755 0 0",
                    "slink /bin/mkdir /bin/busybox 755 0 0",
                    "slink /bin/mknod /bin/busybox 755 0 0",
                    "slink /bin/mktemp /bin/busybox 755 0 0",
                    "slink /bin/mount /bin/busybox 755 0 0",
                    "slink /bin/mpstat /bin/busybox 755 0 0",
                    "slink /bin/mv /bin/busybox 755 0 0",
                    "slink /bin/netstat /bin/busybox 755 0 0",
                    "slink /bin/nice /bin/busybox 755 0 0",
                    "slink /bin/nuke /bin/busybox 755 0 0",
                    "slink /bin/pidof /bin/busybox 755 0 0",
                    "slink /bin/ping /bin/busybox 755 0 0",
                    "slink /bin/printenv /bin/busybox 755 0 0",
                    "slink /bin/ps /bin/busybox 755 0 0",
                    "slink /bin/pwd /bin/busybox 755 0 0",
                    "slink /bin/resume /bin/busybox 755 0 0",
                    "slink /bin/rm /bin/busybox 755 0 0",
                    "slink /bin/rmdir /bin/busybox 755 0 0",
                    "slink /bin/sed /bin/busybox 755 0 0",
                    "slink /bin/setpriv /bin/busybox 755 0 0",
                    "slink /bin/setserial /bin/busybox 755 0 0",
                    "slink /bin/sh /bin/busybox 755 0 0",
                    "slink /bin/sleep /bin/busybox 755 0 0",
                    "slink /bin/stat /bin/busybox 755 0 0",
                    "slink /bin/stty /bin/busybox 755 0 0",
                    "slink /bin/su /bin/busybox 755 0 0",
                    "slink /bin/sync /bin/busybox 755 0 0",
                    "slink /bin/tar /bin/busybox 755 0 0",
                    "slink /bin/touch /bin/busybox 755 0 0",
                    "slink /bin/true /bin/busybox 755 0 0",
                    "slink /bin/umount /bin/busybox 755 0 0",
                    "slink /bin/uname /bin/busybox 755 0 0",
                    "slink /bin/uncompress /bin/busybox 755 0 0",
                    "slink /bin/usleep /bin/busybox 755 0 0",
                    "slink /bin/vi /bin/busybox 755 0 0",
                    "slink /bin/watch /bin/busybox 755 0 0",
                    "slink /bin/zcat /bin/busybox 755 0 0",
                    "" # /linuxrc
                    "slink /linuxrc /bin/busybox 755 0 0",
                    "" # /sbin
                    "slink /sbin/arp /bin/busybox 755 0 0",
                    "slink /sbin/blkid /bin/busybox 755 0 0",
                    "slink /sbin/blockdev /bin/busybox 755 0 0",
                    "slink /sbin/bootchartd /bin/busybox 755 0 0",
                    "slink /sbin/devmem /bin/busybox 755 0 0",
                    "slink /sbin/fbsplash /bin/busybox 755 0 0",
                    "slink /sbin/fdisk /bin/busybox 755 0 0",
                    "slink /sbin/fsck /bin/busybox 755 0 0",
                    "slink /sbin/fstrim /bin/busybox 755 0 0",
                    "slink /sbin/getty /bin/busybox 755 0 0",
                    "slink /sbin/halt /bin/busybox 755 0 0",
                    "slink /sbin/hwclock /bin/busybox 755 0 0",
                    "slink /sbin/ifconfig /bin/busybox 755 0 0",
                    "slink /sbin/ifdown /bin/busybox 755 0 0",
                    "slink /sbin/ifup /bin/busybox 755 0 0",
                    "slink /sbin/init /bin/busybox 755 0 0",
                    "slink /sbin/insmod /bin/busybox 755 0 0",
                    "slink /sbin/ip /bin/busybox 755 0 0",
                    "slink /sbin/ipaddr /bin/busybox 755 0 0",
                    "slink /sbin/iplink /bin/busybox 755 0 0",
                    "slink /sbin/ipneigh /bin/busybox 755 0 0",
                    "slink /sbin/iproute /bin/busybox 755 0 0",
                    "slink /sbin/iprule /bin/busybox 755 0 0",
                    "slink /sbin/iptunnel /bin/busybox 755 0 0",
                    "slink /sbin/klogd /bin/busybox 755 0 0",
                    "slink /sbin/loadkmap /bin/busybox 755 0 0",
                    "slink /sbin/logread /bin/busybox 755 0 0",
                    "slink /sbin/losetup /bin/busybox 755 0 0",
                    "slink /sbin/lsmod /bin/busybox 755 0 0",
                    "slink /sbin/makedevs /bin/busybox 755 0 0",
                    "slink /sbin/mkdosfs /bin/busybox 755 0 0",
                    "slink /sbin/mke2fs /bin/busybox 755 0 0",
                    "slink /sbin/mkfs.ext2 /bin/busybox 755 0 0",
                    "slink /sbin/mkfs.vfat /bin/busybox 755 0 0",
                    "slink /sbin/mkswap /bin/busybox 755 0 0",
                    "slink /sbin/modinfo /bin/busybox 755 0 0",
                    "slink /sbin/poweroff /bin/busybox 755 0 0",
                    "slink /sbin/reboot /bin/busybox 755 0 0",
                    "slink /sbin/rmmod /bin/busybox 755 0 0",
                    "slink /sbin/route /bin/busybox 755 0 0",
                    "slink /sbin/run-init /bin/busybox 755 0 0",
                    "slink /sbin/setconsole /bin/busybox 755 0 0",
                    "slink /sbin/sulogin /bin/busybox 755 0 0",
                    "slink /sbin/swapoff /bin/busybox 755 0 0",
                    "slink /sbin/swapon /bin/busybox 755 0 0",
                    "slink /sbin/switch_root /bin/busybox 755 0 0",
                    "slink /sbin/sysctl /bin/busybox 755 0 0",
                    "slink /sbin/syslogd /bin/busybox 755 0 0",
                    "slink /sbin/tc /bin/busybox 755 0 0",
                    "slink /sbin/uevent /bin/busybox 755 0 0",
                    "", # /usr/bin
                    "slink /usr/bin/[ /bin/busybox 755 0 0",
                    "slink /usr/bin/[[ /bin/busybox 755 0 0",
                    "slink /usr/bin/ar /bin/busybox 755 0 0",
                    "slink /usr/bin/awk /bin/busybox 755 0 0",
                    "slink /usr/bin/basename /bin/busybox 755 0 0",
                    "slink /usr/bin/bc /bin/busybox 755 0 0",
                    "slink /usr/bin/blkdiscard /bin/busybox 755 0 0",
                    "slink /usr/bin/bunzip2 /bin/busybox 755 0 0",
                    "slink /usr/bin/bzcat /bin/busybox 755 0 0",
                    "slink /usr/bin/bzip2 /bin/busybox 755 0 0",
                    "slink /usr/bin/cal /bin/busybox 755 0 0",
                    "slink /usr/bin/chpst /bin/busybox 755 0 0",
                    "slink /usr/bin/chvt /bin/busybox 755 0 0",
                    "slink /usr/bin/cksum /bin/busybox 755 0 0",
                    "slink /usr/bin/clear /bin/busybox 755 0 0",
                    "slink /usr/bin/cmp /bin/busybox 755 0 0",
                    "slink /usr/bin/comm /bin/busybox 755 0 0",
                    "slink /usr/bin/cryptpw /bin/busybox 755 0 0",
                    "slink /usr/bin/cut /bin/busybox 755 0 0",
                    "slink /usr/bin/deallocvt /bin/busybox 755 0 0",
                    "slink /usr/bin/diff /bin/busybox 755 0 0",
                    "slink /usr/bin/dirname /bin/busybox 755 0 0",
                    "slink /usr/bin/dos2unix /bin/busybox 755 0 0",
                    "slink /usr/bin/du /bin/busybox 755 0 0",
                    "slink /usr/bin/env /bin/busybox 755 0 0",
                    "slink /usr/bin/envdir /bin/busybox 755 0 0",
                    "slink /usr/bin/envuidgid /bin/busybox 755 0 0",
                    "slink /usr/bin/expand /bin/busybox 755 0 0",
                    "slink /usr/bin/expr /bin/busybox 755 0 0",
                    "slink /usr/bin/factor /bin/busybox 755 0 0",
                    "slink /usr/bin/fallocate /bin/busybox 755 0 0",
                    "slink /usr/bin/fgconsole /bin/busybox 755 0 0",
                    "slink /usr/bin/find /bin/busybox 755 0 0",
                    "slink /usr/bin/fold /bin/busybox 755 0 0",
                    "slink /usr/bin/free /bin/busybox 755 0 0",
                    "slink /usr/bin/ftpget /bin/busybox 755 0 0",
                    "slink /usr/bin/ftpput /bin/busybox 755 0 0",
                    "slink /usr/bin/fuser /bin/busybox 755 0 0",
                    "slink /usr/bin/groups /bin/busybox 755 0 0",
                    "slink /usr/bin/hd /bin/busybox 755 0 0",
                    "slink /usr/bin/head /bin/busybox 755 0 0",
                    "slink /usr/bin/hexdump /bin/busybox 755 0 0",
                    "slink /usr/bin/hexedit /bin/busybox 755 0 0",
                    "slink /usr/bin/hostid /bin/busybox 755 0 0",
                    "slink /usr/bin/id /bin/busybox 755 0 0",
                    "slink /usr/bin/install /bin/busybox 755 0 0",
                    "slink /usr/bin/killall /bin/busybox 755 0 0",
                    "slink /usr/bin/last /bin/busybox 755 0 0",
                    "slink /usr/bin/less /bin/busybox 755 0 0",
                    "slink /usr/bin/logger /bin/busybox 755 0 0",
                    "slink /usr/bin/logname /bin/busybox 755 0 0",
                    "slink /usr/bin/lsof /bin/busybox 755 0 0",
                    "slink /usr/bin/lspci /bin/busybox 755 0 0",
                    "slink /usr/bin/lsscsi /bin/busybox 755 0 0",
                    "slink /usr/bin/lsusb /bin/busybox 755 0 0",
                    "slink /usr/bin/lzcat /bin/busybox 755 0 0",
                    "slink /usr/bin/lzma /bin/busybox 755 0 0",
                    "slink /usr/bin/man /bin/busybox 755 0 0",
                    "slink /usr/bin/md5sum /bin/busybox 755 0 0",
                    "slink /usr/bin/mesg /bin/busybox 755 0 0",
                    "slink /usr/bin/microcom /bin/busybox 755 0 0",
                    "slink /usr/bin/mkfifo /bin/busybox 755 0 0",
                    "slink /usr/bin/mkpasswd /bin/busybox 755 0 0",
                    "slink /usr/bin/nc /bin/busybox 755 0 0",
                    "slink /usr/bin/netcat /bin/busybox 755 0 0",
                    "slink /usr/bin/nl /bin/busybox 755 0 0",
                    "slink /usr/bin/nmeter /bin/busybox 755 0 0",
                    "slink /usr/bin/nohup /bin/busybox 755 0 0",
                    "slink /usr/bin/nproc /bin/busybox 755 0 0",
                    "slink /usr/bin/nsenter /bin/busybox 755 0 0",
                    "slink /usr/bin/nslookup /bin/busybox 755 0 0",
                    "slink /usr/bin/od /bin/busybox 755 0 0",
                    "slink /usr/bin/openvt /bin/busybox 755 0 0",
                    "slink /usr/bin/passwd /bin/busybox 755 0 0",
                    "slink /usr/bin/paste /bin/busybox 755 0 0",
                    "slink /usr/bin/patch /bin/busybox 755 0 0",
                    "slink /usr/bin/pgrep /bin/busybox 755 0 0",
                    "slink /usr/bin/pkill /bin/busybox 755 0 0",
                    "slink /usr/bin/pmap /bin/busybox 755 0 0",
                    "slink /usr/bin/printf /bin/busybox 755 0 0",
                    "slink /usr/bin/pstree /bin/busybox 755 0 0",
                    "slink /usr/bin/pwdx /bin/busybox 755 0 0",
                    "slink /usr/bin/readlink /bin/busybox 755 0 0",
                    "slink /usr/bin/realpath /bin/busybox 755 0 0",
                    "slink /usr/bin/reset /bin/busybox 755 0 0",
                    "slink /usr/bin/resize /bin/busybox 755 0 0",
                    "slink /usr/bin/runsv /bin/busybox 755 0 0",
                    "slink /usr/bin/runsvdir /bin/busybox 755 0 0",
                    "slink /usr/bin/seq /bin/busybox 755 0 0",
                    "slink /usr/bin/setfattr /bin/busybox 755 0 0",
                    "slink /usr/bin/setkeycodes /bin/busybox 755 0 0",
                    "slink /usr/bin/setuidgid /bin/busybox 755 0 0",
                    "slink /usr/bin/sha1sum /bin/busybox 755 0 0",
                    "slink /usr/bin/sha256sum /bin/busybox 755 0 0",
                    "slink /usr/bin/sha3sum /bin/busybox 755 0 0",
                    "slink /usr/bin/sha512sum /bin/busybox 755 0 0",
                    "slink /usr/bin/showkey /bin/busybox 755 0 0",
                    "slink /usr/bin/shred /bin/busybox 755 0 0",
                    "slink /usr/bin/shuf /bin/busybox 755 0 0",
                    "slink /usr/bin/smemcap /bin/busybox 755 0 0",
                    "slink /usr/bin/softlimit /bin/busybox 755 0 0",
                    "slink /usr/bin/sort /bin/busybox 755 0 0",
                    "slink /usr/bin/split /bin/busybox 755 0 0",
                    "slink /usr/bin/ssl_client /bin/busybox 755 0 0",
                    "slink /usr/bin/sum /bin/busybox 755 0 0",
                    "slink /usr/bin/sv /bin/busybox 755 0 0",
                    "slink /usr/bin/svc /bin/busybox 755 0 0",
                    "slink /usr/bin/svok /bin/busybox 755 0 0",
                    "slink /usr/bin/tac /bin/busybox 755 0 0",
                    "slink /usr/bin/tail /bin/busybox 755 0 0",
                    "slink /usr/bin/taskset /bin/busybox 755 0 0",
                    "slink /usr/bin/tee /bin/busybox 755 0 0",
                    "slink /usr/bin/telnet /bin/busybox 755 0 0",
                    "slink /usr/bin/test /bin/busybox 755 0 0",
                    "slink /usr/bin/tftp /bin/busybox 755 0 0",
                    "slink /usr/bin/time /bin/busybox 755 0 0",
                    "slink /usr/bin/top /bin/busybox 755 0 0",
                    "slink /usr/bin/tr /bin/busybox 755 0 0",
                    "slink /usr/bin/truncate /bin/busybox 755 0 0",
                    "slink /usr/bin/ts /bin/busybox 755 0 0",
                    "slink /usr/bin/tty /bin/busybox 755 0 0",
                    "slink /usr/bin/unexpand /bin/busybox 755 0 0",
                    "slink /usr/bin/uniq /bin/busybox 755 0 0",
                    "slink /usr/bin/unix2dos /bin/busybox 755 0 0",
                    "slink /usr/bin/unlink /bin/busybox 755 0 0",
                    "slink /usr/bin/unlzma /bin/busybox 755 0 0",
                    "slink /usr/bin/unshare /bin/busybox 755 0 0",
                    "slink /usr/bin/unxz /bin/busybox 755 0 0",
                    "slink /usr/bin/unzip /bin/busybox 755 0 0",
                    "slink /usr/bin/uptime /bin/busybox 755 0 0",
                    "slink /usr/bin/users /bin/busybox 755 0 0",
                    "slink /usr/bin/uudecode /bin/busybox 755 0 0",
                    "slink /usr/bin/uuencode /bin/busybox 755 0 0",
                    "slink /usr/bin/vlock /bin/busybox 755 0 0",
                    "slink /usr/bin/w /bin/busybox 755 0 0",
                    "slink /usr/bin/wc /bin/busybox 755 0 0",
                    "slink /usr/bin/wget /bin/busybox 755 0 0",
                    "slink /usr/bin/which /bin/busybox 755 0 0",
                    "slink /usr/bin/who /bin/busybox 755 0 0",
                    "slink /usr/bin/whoami /bin/busybox 755 0 0",
                    "slink /usr/bin/whois /bin/busybox 755 0 0",
                    "slink /usr/bin/xargs /bin/busybox 755 0 0",
                    "slink /usr/bin/xxd /bin/busybox 755 0 0",
                    "slink /usr/bin/xz /bin/busybox 755 0 0",
                    "slink /usr/bin/xzcat /bin/busybox 755 0 0",
                    "slink /usr/bin/yes /bin/busybox 755 0 0",
                    "", #/usr/sbin
                    "slink /usr/sbin/addgroup /bin/busybox 755 0 0",
                    "slink /usr/sbin/add-shell /bin/busybox 755 0 0",
                    "slink /usr/sbin/adduser /bin/busybox 755 0 0",
                    "slink /usr/sbin/arping /bin/busybox 755 0 0",
                    "slink /usr/sbin/brctl /bin/busybox 755 0 0",
                    "slink /usr/sbin/chpasswd /bin/busybox 755 0 0",
                    "slink /usr/sbin/chroot /bin/busybox 755 0 0",
                    "slink /usr/sbin/delgroup /bin/busybox 755 0 0",
                    "slink /usr/sbin/deluser /bin/busybox 755 0 0",
                    "slink /usr/sbin/fbset /bin/busybox 755 0 0",
                    "slink /usr/sbin/fsfreeze /bin/busybox 755 0 0",
                    "slink /usr/sbin/i2cdetect /bin/busybox 755 0 0",
                    "slink /usr/sbin/i2cdump /bin/busybox 755 0 0",
                    "slink /usr/sbin/i2cget /bin/busybox 755 0 0",
                    "slink /usr/sbin/i2cset /bin/busybox 755 0 0",
                    "slink /usr/sbin/i2ctransfer /bin/busybox 755 0 0",
                    "slink /usr/sbin/killall5 /bin/busybox 755 0 0",
                    "slink /usr/sbin/loadfont /bin/busybox 755 0 0",
                    "slink /usr/sbin/nbd-client /bin/busybox 755 0 0",
                    "slink /usr/sbin/nologin /bin/busybox 755 0 0",
                    "slink /usr/sbin/partprobe /bin/busybox 755 0 0",
                    "slink /usr/sbin/powertop /bin/busybox 755 0 0",
                    "slink /usr/sbin/remove-shell /bin/busybox 755 0 0",
                    "slink /usr/sbin/setfont /bin/busybox 755 0 0",
                    "slink /usr/sbin/setlogcons /bin/busybox 755 0 0",
                    "slink /usr/sbin/svlogd /bin/busybox 755 0 0",
                    "slink /usr/sbin/telnetd /bin/busybox 755 0 0",
                    "slink /usr/sbin/ubirename /bin/busybox 755 0 0",
                    "",
                ],
                "default_initramfs_libs": [
                    "# libraries",
                    "file /lib/ld-linux-riscv64-lp64d.so.1 ${RISCV}/sysroot/lib/ld-linux-riscv64-lp64d.so.1 755 0 0",
                    "file /lib/libc.so.6 ${RISCV}/sysroot/lib/libc.so.6 755 0 0",
                    "file /lib/libresolv.so.2 ${RISCV}/sysroot/lib/libresolv.so.2 755 0 0",
                    "file /lib/libm.so.6 ${RISCV}/sysroot/lib/libm.so.6 755 0 0",
                    "file /lib/libdl.so.2 ${RISCV}/sysroot/lib/libdl.so.2 755 0 0",
                    "file /lib/libpthread.so.0 ${RISCV}/sysroot/lib/libpthread.so.0 755 0 0",
                    "",
                ],
            }
        )


    def prepare_rcS(self, guest_memory, guest_cpus, spec, scripts_archive_folder):
        lines = []
        lines.append("#! /bin/sh")
        lines.append("set -x")
        lines.append("/bin/mount -a")
        lines.append("mkdir -p /dev")
        lines.append("/bin/mount -t devtmpfs devtmpfs /dev")

        lines.append(f'/apps/lkvm-static run -m {guest_memory} -c{guest_cpus} --console serial -p "earlycon=sbi" -k /apps/guest_Image --debug')
        with open(os.path.join(scripts_archive_folder, "{}_rcS-spec.txt".format(spec)), "w", encoding="utf-8") as f:
            f.writelines(map(lambda x: x + "\n", lines))

        self.rcs_list.append((spec, os.path.join(scripts_archive_folder, f"{spec}_rcS-spec.txt")))
        
    def prepare_rootfs(self, spec, using_cpu2017, using_jemalloc, copies, with_nemu_trap, redirect_output, emu):
        archive_buffer_layout = self.config["archive_buffer_layout"]
        self.__generate_initramfs(archive_buffer_layout["scripts"], archive_buffer_layout["elf"], spec, os.path.join(self.config["path_env_vars"]["RISCV_ROOTFS_HOME"], "rootfsimg"), using_cpu2017, using_jemalloc, copies)
        self.__generate_run_scripts(spec, copies, redirect_output, using_cpu2017, with_nemu_trap, os.path.join(self.config["path_env_vars"]["RISCV_ROOTFS_HOME"], "rootfsimg"), archive_buffer_layout["scripts"], emu)


# original func is: https://github.com/OpenXiangShan/riscv-rootfs/blob/da983ec95858dfd6f30e9feadd534b79db37e618/rootfsimg/spec_gen.py#L544
    def traverse_path(self, path, stack=""):
        all_dirs, all_files = [], []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            item_stack = os.path.join(stack, item)
            if os.path.isfile(item_path):
                all_files.append(item_stack)
            else:
                all_dirs.append(item_stack)
                sub_dirs, sub_files = self.traverse_path(item_path, item_stack)
                all_dirs.extend(sub_dirs)
                all_files.extend(sub_files)
        return (all_dirs, all_files)

    def __generate_host_initramfs_files(self, guest_Image_path):
        host_initramfs_files = [
            "file /apps/lkvm-static ${RISCV_ROOTFS_HOME}/apps/lkvm-static 755 0 0",
            f"file /apps/guest_Image {guest_Image_path} 755 0 0"
        ]
        return host_initramfs_files

    def __generate_host_initramfs(self, scripts_archive_folder, spec):
        host_initramfs = [x for lst in (self.config["default_initramfs_dirs"], self.config["default_initramfs_busybox"], self.config["default_initramfs_libs"], self.__generate_host_initramfs_files(self.kernel_list.pop()[1])) for x in lst]
        host_initramfs.append(f"file /etc/init.d/rcS {self.rcs_list.pop()[1]} 755 0 0")
        with open(
                os.path.join(scripts_archive_folder,
                             "{}_host_initramfs-spec.txt".format(spec)), "w", encoding="utf-8") as f:
            f.writelines(map(lambda x: x + "\n", host_initramfs))

        self.host_initramfs_list.append((spec, os.path.join(scripts_archive_folder, f"{spec}_host_initramfs-spec.txt")))

# original func is: https://github.com/OpenXiangShan/riscv-rootfs/blob/c61a659b454e5b038b5374a9091b29ad4995f13f/rootfsimg/spec_gen.py#L558
    def __generate_initramfs(self, scripts_archive_folder, elf_folder, spec, dest_path, using_cpu2017=False, using_jemalloc=True, copies=1):
        spec_config = self.config["spec_info"]

        lines = self.config["default_initramfs_file"].copy()
        lines += ["# libraries"]
        lines += get_libraries_str(self.config["path_env_vars"]["RISCV"], using_jemalloc)
        if not isinstance(lines, list):
            raise ValueError("lines not a list type value")

        spec_files = spec_config[spec]["files"]

        if using_cpu2017:
            cpu20xx_run_dir = self.config["path_env_vars"]["CPU2017_RUN_DIR"]
        else:
            cpu20xx_run_dir = self.config["path_env_vars"]["CPU2006_RUN_DIR"]

        for i in range(0, copies):
            lines.append(f"dir /spec{i} 755 0 0")

        lines.append(f"file /spec0/run.sh {scripts_archive_folder}/{spec}_run.sh 755 0 0")

        for i in range(0, copies):
            elf_file_abspath = os.path.realpath(f"{elf_folder}/{spec_config[spec]['base_name']}")
            lines.append(f"file /spec{i}/{spec_config[spec]['base_name']} {elf_file_abspath} 755 0 0")

        for i, filename in enumerate(spec_files):
            if len(filename.split()) == 1:
                for j in range(0, copies):
                    target_filename = f"file /spec{j}/{filename.split('/')[-1]} {cpu20xx_run_dir}/{filename} 755 0 0"
                    lines.append(target_filename)

            elif len(filename.split()) == 3:
                node_type, name, path = filename.split()

                if node_type != "dir":
                    print(f"unknown filename: {filename}")
                    continue

                all_dirs, all_files = self.traverse_path(f"{cpu20xx_run_dir}{path}")

                for i in range(0, copies):
                    lines.append(f"dir /spec{i}/{name} 755 0 0")
                for sub_dir in all_dirs:
                    for i in range(0, copies):
                        lines.append(f"dir /spec{i}/{name}/{sub_dir} 755 0 0")
                for file in all_files:
                    for i in range(0, copies):
                        lines.append(f"file /spec{i}/{name}/{file} {cpu20xx_run_dir}{path}/{file} 755 0 0")
            else:
                print(f"unknown filename: {filename}")

        for i in range(0, int(copies)):
                lines.append(f"file /spec{i}/task{i}.sh {scripts_archive_folder}/{spec}_task{i}.sh 755 0 0")


#        with open(os.path.join(dest_path, "initramfs-spec.txt"), "w", encoding="utf-8") as f:
#            f.writelines(map(lambda x: x + "\n", lines))

        with open(
                os.path.join(scripts_archive_folder,
                             "{}_initramfs-spec.txt".format(spec)), "w", encoding="utf-8") as f:
            f.writelines(map(lambda x: x + "\n", lines))

        self.initramfs_list.append((spec, os.path.join(scripts_archive_folder, f"{spec}_initramfs-spec.txt")))

# original func is: https://github.com/OpenXiangShan/riscv-rootfs/blob/c61a659b454e5b038b5374a9091b29ad4995f13f/rootfsimg/spec_gen.py#L585
    def __generate_run_scripts(self, spec, copies, redirect_output, using_cpu2017, with_nemu_trap, run_scripts_dest_path, run_scripts_archive_path, emu):
        spec_config = self.config["spec_info"]
        lines = []
        lines.append("#!/bin/sh")

        if using_cpu2017:
            SPEC_20XX = "SPEC2017"
        else:
            SPEC_20XX = "SPEC2006"

        spec_bin = spec_config[spec]["base_name"]
        spec_cmd = " ".join(
            spec_config[spec]["args"])

        lines.append(f"echo '===== Start running {SPEC_20XX} ====='")
        lines.append(f"echo '======== BEGIN {spec} ========'")
        lines.append("export LD_LIBRARY_PATH=/lib:$LD_LIBRARY_PATH")
        lines.append("head -c 10 /dev/random | hexdump")
        lines.append("set -x")

        for i in range(0, copies):
            lines.append(f"md5sum /spec{i}/{spec_bin}")

        output_redirect = (" ").join([">", "out.log", "2>", "err.log"]) if redirect_output else ""
        force_output_redirect = (" ").join([">", "out.log", "2>", "err.log"])

        output_redirect_workload_list_cpu2006 = ['xalancbmk']
        output_redirect_workload_list_cpu2017 = ['perlbench', "povray", "xalancbmk", "leela"]

        taskN = []
        for i in range(0, int(copies)):
            taskN.append("#!/bin/sh")
            taskN.append("set -x")
            taskN.append(f"echo '===== Start running TASK{i} ====='")
            taskN.append("ulimit -s unlimited")
            taskN.append("date -R")
            if with_nemu_trap:
                taskN.append("/spec_common/before_workload")

            if using_cpu2017:
                if spec_bin in output_redirect_workload_list_cpu2017:
                    taskN.append(f'cd /spec{i} && ./{spec_bin} {spec_cmd} {force_output_redirect} ')
                else:
                    taskN.append(f'cd /spec{i} && ./{spec_bin} {spec_cmd} {output_redirect} ')
            else:
                if spec_bin in output_redirect_workload_list_cpu2006:
                    taskN.append(f'cd /spec{i} && ./{spec_bin} {spec_cmd} {force_output_redirect} ')
                else:
                    taskN.append(f'cd /spec{i} && ./{spec_bin} {spec_cmd} {output_redirect} ')

            taskN.append("date -R")
            if with_nemu_trap:
                if emu == "NEMU":
                    taskN.append("/spec_common/trap")
                else:
                    taskN.append("/spec_common/qemu_trap")

            backend_run = '&'

            lines.append(f"/bin/busybox taskset -c {i} /spec{i}/task{i}.sh {backend_run}")
            lines.append(f"PID{i}=$!")

#            with open(os.path.join(run_scripts_dest_path, f"task{i}.sh"), "w", encoding="utf-8") as f:
#                f.writelines(map(lambda x: x + "\n", taskN))

            with open(os.path.join(run_scripts_archive_path, f"{spec}_task{i}.sh"), "w", encoding="utf-8") as f:
                f.writelines(map(lambda x: x + "\n", taskN))
            taskN = []
        for i in range(0, int(copies)):
            lines.append(f"wait $PID{i}")

        lines.append("ls /spec")
        lines.append(f"echo '======== END   {spec} ========'")
        lines.append(f"echo '===== Finish running {SPEC_20XX} ====='")

#        with open(os.path.join(run_scripts_dest_path, "run.sh"), "w", encoding="utf-8") as f:
#            f.writelines(map(lambda x: x + "\n", lines))

        with open(
                os.path.join(run_scripts_archive_path,
                             "{}_run.sh".format(spec)), "w", encoding="utf-8") as f:
            f.writelines(map(lambda x: x + "\n", lines))

    @staticmethod
    def run_commands(commands, cwd, out_log, err_log):
        """Run a series of commands in a specified directory, logging output and errors."""
        with open(out_log, "a", encoding="utf-8") as out, open(err_log, "a", encoding="utf-8") as err:
            for command in commands:
                if cwd is not None:
                    res = subprocess.run(command, cwd=cwd, stdout=out, stderr=err, check=True)
                else:
                    res = subprocess.run(command, stdout=out, stderr=err, check=True)
                res.check_returncode()

    def build_spec_bbl(self, spec, build_log_folder, spec_bin_folder, bin_suffix, assembly_folder, qemu_payload):
        PK_HOME = self.path_env_vars.get("RISCV_PK_HOME")
        if not PK_HOME:
            raise EnvironmentError("Environment variable RISCV_PK_HOME is not set or not initialized.")
        GCPT_HOME = self.path_env_vars.get("GCPT_HOME")
        if not GCPT_HOME:
            raise EnvironmentError("Environment variable RISCV_PK_HOME is not set or not initialized.")

        if qemu_payload:
            print(f"build qemu payload: {spec}-gcpt-bbl-linux-spec...")
        else:
            print(f"build nemu payload: {spec}-bbl-linux-spec...")

        out_log = os.path.join(build_log_folder, f"build-{spec}-out.log")
        err_log = os.path.join(build_log_folder, f"build-{spec}-err.log")

        pk_commands = [["make", "clean"], ["make", "-j70"]]
        self.run_commands(pk_commands, self.path_env_vars.get("RISCV_PK_HOME"), out_log, err_log)
        self.copy(PK_HOME, spec, bin_suffix, [
            ("build/bbl.bin", "", spec_bin_folder),
            ("build/bbl.txt", ".pk.s", assembly_folder),
            ("build/vmlinux.txt", ".vmlinux.s", assembly_folder)
        ])

        if qemu_payload:
            gcpt_commands = [["make", "clean"], ["make", "USING_QEMU_DUAL_CORE_SYSTEM=1", f"GCPT_PAYLOAD_PATH={os.path.join(PK_HOME, 'build', 'bbl.bin')}", "-j10"]]

            self.run_commands(gcpt_commands, GCPT_HOME, out_log, err_log)
            self.copy(GCPT_HOME, spec, bin_suffix, [
                ("build/gcpt.bin", "", spec_bin_folder),
            ])

    def build_host_linux_kernel(self, spec, bin_suffix):
        archive_buffer_layout = self.config["archive_buffer_layout"]
        HOST_LINUX_HOME = self.path_env_vars.get("LINUX_HOME")
        if not HOST_LINUX_HOME:
            raise EnvironmentError("Environment variable LINUX_HOME is not set or not initialized.")
        ROOTFSIMG = self.path_env_vars.get("RISCV_ROOTFS_HOME")
        if not ROOTFSIMG:
            raise EnvironmentError("Environment variable RISCV_ROOTFS_HOME is not set or not initialized.")
        ARCH = self.env_vars.get("ARCH")
        if not ARCH or ARCH != "riscv":
            raise EnvironmentError("Environment variable ARCH is not set or not initialized.")

        out_log = os.path.join(archive_buffer_layout["logs_build"], f"build-host-kernel-with-{spec}-out.log")
        err_log = os.path.join(archive_buffer_layout["logs_build"], f"build-host-kernel-with-{spec}-err.log")


        prepare_linux_config = [
            ["make", "-C", HOST_LINUX_HOME, f"O={archive_buffer_layout['host_linux']}", "xiangshanhost_defconfig"],
        ]
        shared_linux_command = [
            ["make", "-C", HOST_LINUX_HOME, f"O={archive_buffer_layout['host_linux']}", "-j70"]
        ]

        self.run_commands(prepare_linux_config, None, out_log, err_log)
        config_file = os.path.join(archive_buffer_layout['linux'], ".config")
        _, initramfs_file_path = self.host_initramfs_list.pop()

        try:
            with open(config_file, 'r', encoding="utf-8") as f:
                lines = f.readlines()

            with open(config_file, 'w', encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("CONFIG_INITRAMFS_SOURCE="):
                        f.write(f'CONFIG_INITRAMFS_SOURCE="{initramfs_file_path}"\n')
                    else:
                        f.write(line)
        except FileNotFoundError:
            print(f"File {config_file} not found")
            exit(1)
        except Exception as e:
            print(f"An error occured: {e}")
            exit(1)
        self.run_commands(shared_linux_command, None, out_log, err_log)

        if not isinstance(archive_buffer_layout["binary_archive"], str):
            raise ValueError("binary_archive value is not str")

        self.copy(archive_buffer_layout['linux'], spec, bin_suffix, [
            ("arch/riscv/boot/Image", "._hostImage", archive_buffer_layout["binary_archive"]),
        ])

        self.kernel_list.append((spec, f"{archive_buffer_layout['binary_archive']}/{spec}{bin_suffix}._hostImage"))


    def build_linux_kernel(self, spec, bin_suffix):
        archive_buffer_layout = self.config["archive_buffer_layout"]
        LINUX_HOME = self.path_env_vars.get("LINUX_HOME")
        if not LINUX_HOME:
            raise EnvironmentError("Environment variable LINUX_HOME is not set or not initialized.")
        RISCV_ROOTFS_HOME = self.path_env_vars.get("RISCV_ROOTFS_HOME")
        if not RISCV_ROOTFS_HOME:
            raise EnvironmentError("Environment variable RISCV_ROOTFS_HOME is not set or not initialized.")
        ARCH = self.env_vars.get("ARCH")
        if not ARCH or ARCH != "riscv":
            raise EnvironmentError("Environment variable ARCH is not set or not initialized.")

        out_log = os.path.join(archive_buffer_layout["logs_build"], f"build-kernel-with-{spec}-out.log")
        err_log = os.path.join(archive_buffer_layout["logs_build"], f"build-kernel-with-{spec}-err.log")


        prepare_linux_config = [
            ["make", "-C", LINUX_HOME, f"O={archive_buffer_layout['linux']}", "xiangshan_defconfig"],
        ]
        shared_linux_command = [
            ["make", "-C", LINUX_HOME, f"O={archive_buffer_layout['linux']}", "-j70"]
        ]

        self.run_commands(prepare_linux_config, None, out_log, err_log)
        config_file = os.path.join(archive_buffer_layout['linux'], ".config")
        _, initramfs_file_path = self.initramfs_list.pop()

        try:
            with open(config_file, 'r', encoding="utf-8") as f:
                lines = f.readlines()

            with open(config_file, 'w', encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("CONFIG_INITRAMFS_SOURCE="):
                        f.write(f'CONFIG_INITRAMFS_SOURCE="{initramfs_file_path}"\n')
                    else:
                        f.write(line)
        except FileNotFoundError:
            print(f"File {config_file} not found")
            exit(1)
        except Exception as e:
            print(f"An error occured: {e}")
            exit(1)
        self.run_commands(shared_linux_command, None, out_log, err_log)

        if not isinstance(archive_buffer_layout["binary_archive"], str):
            raise ValueError("binary_archive value is not str")

        self.copy(archive_buffer_layout['linux'], spec, bin_suffix, [
            ("arch/riscv/boot/Image", ".Image", archive_buffer_layout["binary_archive"]),
        ])

        self.kernel_list.append((spec, f"{archive_buffer_layout['binary_archive']}/{spec}{bin_suffix}.Image"))

    def build_opensbi(self, copies, spec, bin_suffix):
        archive_buffer_layout = self.config["archive_buffer_layout"]

        OPENSBI_HOME = self.path_env_vars.get("OPENSBI_HOME")
        if not OPENSBI_HOME:
            raise EnvironmentError("Environment variable OPENSBI_HOME is not set or not initialized.")
        XIANGSHAN_FDT = self.path_env_vars.get("XIANGSHAN_FDT")
        if not XIANGSHAN_FDT:
            raise EnvironmentError("Environment variable XIANGSHAN_FDT is not set or not initialized.")

        if not isinstance(archive_buffer_layout["logs_build"], str):
            raise ValueError(f"The 'logs_build' key in bbl generate config must be a string and must exist.")

        out_log = os.path.join(archive_buffer_layout["logs_build"], f"build-opensbi-with-{spec}-out.log")
        err_log = os.path.join(archive_buffer_layout["logs_build"], f"build-opensbi-with-{spec}-err.log")

        _, fw_payload_bin = self.kernel_list.pop()
        fw_payload_bin_size = os.path.getsize(fw_payload_bin)
        fw_payload_fdt_addr = (((fw_payload_bin_size + 0x800000) + 0xfffff) // 0x100000) * 0x100000
        fw_payload_fdt_addr = fw_payload_fdt_addr + 0x80000000
        print(f"SPEC: {spec}, file size: {fw_payload_bin_size:X}, fw_payload_fdt_addr: {fw_payload_fdt_addr:X}")

        shared_opensbi_command = []
        if os.path.exists(f"{archive_buffer_layout['opensbi']}/build"):
            shared_opensbi_command.append(["rm", "-rf", f"{archive_buffer_layout['opensbi']}/build"])

        if copies == 1:
            fw_payload_offset = 0x100000
        else:
            fw_payload_offset = 0x700000

        shared_opensbi_command.append(
            ["make", "-C", OPENSBI_HOME, f"O={archive_buffer_layout['opensbi']}/build", "PLATFORM=generic", f"FW_PAYLOAD_PATH={fw_payload_bin}", f"FW_FDT_PATH={XIANGSHAN_FDT}", f"FW_PAYLOAD_OFFSET={fw_payload_offset}", f"FW_PAYLOAD_FDT_ADDR={fw_payload_fdt_addr}", "-j10"])

        self.run_commands(shared_opensbi_command, None, out_log, err_log)
        self.copy(archive_buffer_layout["opensbi"], spec, bin_suffix, [
            ("build/platform/generic/firmware/fw_payload.bin", ".fw_payload.bin", archive_buffer_layout["binary_archive"]),
        ])

        self.opensbi_fw_payload.append((spec, f"{archive_buffer_layout['binary_archive']}/{spec}{bin_suffix}.fw_payload.bin"))

    def build_gcpt(self, copies, spec, gcpt_bin_suffix):
        archive_buffer_layout = self.config["archive_buffer_layout"]

        GCPT_HOME = self.path_env_vars.get("GCPT_HOME")
        if not GCPT_HOME:
            raise EnvironmentError("Environment variable GCPT_HOME is not set or not initialized.")

        if not isinstance(archive_buffer_layout["logs_build"], str):
            raise ValueError(f"The 'logs_build' key in bbl generate config must be a string and must exist.")

        out_log = os.path.join(archive_buffer_layout["logs_build"], f"build-gcpt-with-{spec}-out.log")
        err_log = os.path.join(archive_buffer_layout["logs_build"], f"build-gcpt-with-{spec}-err.log")

        _, fw_payload_path = self.opensbi_fw_payload.pop()

        shared_gcpt_commands = []
        shared_gcpt_commands.append(["make", "-C", GCPT_HOME, f"O={archive_buffer_layout['gcpt']}", "clean"])
        if copies == 1:
            shared_gcpt_commands.append(["make", "-C", GCPT_HOME, f"O={archive_buffer_layout['gcpt']}", f'GCPT_PAYLOAD_PATH={fw_payload_path}'])
        else:
            shared_gcpt_commands.append(["make", "-C", GCPT_HOME, f"O={archive_buffer_layout['gcpt']}", f'GCPT_PAYLOAD_PATH={fw_payload_path}', "USING_QEMU_DUAL_CORE_SYSTEM=1"])

        if not isinstance(archive_buffer_layout["gcpt_bins"], str):
            raise ValueError(f"The 'gcpt_bins' key in bbl generate config must be a string and must exist.")

        if not isinstance(archive_buffer_layout["assembly"], str):
            raise ValueError(f"The 'gcpt_bins' key in bbl generate config must be a string and must exist.")

        self.run_commands(shared_gcpt_commands, None, out_log, err_log)
        self.copy(archive_buffer_layout['gcpt'], spec, gcpt_bin_suffix, [
            ("build/gcpt.bin", "", archive_buffer_layout["gcpt_bins"]),
            ("build/gcpt.txt", ".gcpt.s", archive_buffer_layout["assembly"])
        ])

        self.gcpt_bin_list.append((spec, f"{archive_buffer_layout['gcpt_bins']}/{spec}{gcpt_bin_suffix}"))

    def boot_test(self, copies, emu):
        QEMU_HOME = self.path_env_vars.get("QEMU_HOME")
        NEMU_HOME = self.path_env_vars.get("NEMU_HOME")
        if not QEMU_HOME:
            raise EnvironmentError("Environment variable QEMU_HOME is not set or not initialized.")
        if not NEMU_HOME:
            raise EnvironmentError("Environment variable NEMU_HOME is not set or not initialized.")

        while self.gcpt_bin_list:
            _, gcpt_bin = self.gcpt_bin_list.pop()

            nemu_command = [f"{NEMU_HOME}/build/riscv64-nemu-interpreter", "-b", gcpt_bin]
            qemu_command = [f"{QEMU_HOME}/build/qemu-system-riscv64", "-bios", gcpt_bin, "-nographic", "-m", "8G", f"-smp", f"{copies}", "-cpu", "rv64,v=true,vlen=128,sv39=true,sv48=false,sv57=false,sv64=false", "-M", "nemu"]

            if emu == "NEMU":
                command = nemu_command
            else:
                command = qemu_command

            try:
                subprocess.run(command, timeout=60)
            except subprocess.TimeoutExpired:
                pass

    def build_opensbi_payload(self, spec, copies, enable_h_ext, bin_suffix = "", gcpt_bin_suffix = "", withGCPT = False):

        print(f"build {spec}-opensbi-linux-spec...{' with GCPT' if withGCPT else ''}")

        self.build_linux_kernel(spec, bin_suffix)
        if enable_h_ext:
            self.prepare_rcS("4G", "1", spec, self.config["archive_buffer_layout"]["scripts"])
            self.__generate_host_initramfs(self.config["archive_buffer_layout"]["scripts"], spec)
            self.build_host_linux_kernel(spec, bin_suffix)
        self.build_opensbi(spec=spec, copies=copies, bin_suffix=bin_suffix)

        if withGCPT:
            self.build_gcpt(spec=spec, copies=copies, gcpt_bin_suffix=gcpt_bin_suffix)

    @staticmethod
    def copy(src_base_path, spec, suffix, files: List[Tuple[str, str, str]]):
        """Copy files from base path to their respective destinations with appropriate suffixes."""
        for src_file, dst_suffix, dst_base_path in files:
            src_path = os.path.join(src_base_path, src_file)
            dst_path = os.path.join(dst_base_path, f"{spec}{suffix}{dst_suffix}")
            shutil.copy(src_path, dst_path)

# Example usage
#builder = Builder(env_vars_to_check=["LINUX_HOME", "OPENSBI_HOME", "XIANGSHAN_FDT", "NEMU_HOME", "RISCV_PK_HOME"])
#builder.build_spec_bbl("example_spec", "/path/to/logs", "/path/to/bin", "_suffix", "/path/to/assembly")
#builder.build_opensbi_payload("example_spec", "/path/to/logs", "/path/to/bin", "_suffix", "/path/to/gcpt_bin", "_gcpt_suffix", "/path/to/assembly", withGCPT=True)
#
