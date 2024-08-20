import os
import shutil
import subprocess
import os
import subprocess
import shutil
from config import BaseConfig
from typing import Tuple, List
import subprocess

class RootfsBuilder(BaseConfig):
    def __init__(self, archive_buffer_layout, spec_info, path_env_vars_to_check=None, env_vars_to_check=None):
        """Initialize Builder with optional environment variables to check."""
        super().__init__(path_env_vars_to_check=path_env_vars_to_check, env_vars_to_check=env_vars_to_check)
        self.kernel_list: List[Tuple[str, str]] = []
        self.opensbi_fw_payload: List[Tuple[str, str]] = []
        self.gcpt_bin_list: List[Tuple[str, str]] = []
        self.initramfs_list: List[Tuple[str, str]] = []
        self.config.update(
            **{
                "archive_buffer_layout": {
                    "scripts": archive_buffer_layout.get("scripts"),
                    "elf": archive_buffer_layout.get("elf"),
                    "logs_build": archive_buffer_layout.get("logs_build"),
                    "opensbi": archive_buffer_layout.get("opensbi"),
                    "linux": archive_buffer_layout.get("linux"),
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
                    "# libraries",
                    "file /lib/ld-linux-riscv64-lp64d.so.1 ${RISCV}/sysroot/lib/ld-linux-riscv64-lp64d.so.1 755 0 0",
                    "file /lib/libc.so.6 ${RISCV}/sysroot/lib/libc.so.6 755 0 0",
                    "file /lib/libresolv.so.2 ${RISCV}/sysroot/lib/libresolv.so.2 755 0 0",
                    "file /lib/libm.so.6 ${RISCV}/sysroot/lib/libm.so.6 755 0 0",
                    "file /lib/libdl.so.2 ${RISCV}/sysroot/lib/libdl.so.2 755 0 0",
                    "file /lib/libpthread.so.0 ${RISCV}/sysroot/lib/libpthread.so.0 755 0 0",
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
                ]
            }
        )

    def prepare_rootfs(self, spec, using_cpu2017, copies, with_nemu_trap, redirect_output, emu):
        archive_buffer_layout = self.config["archive_buffer_layout"]
        self.__generate_initramfs(archive_buffer_layout["scripts"], archive_buffer_layout["elf"], spec, os.path.join(self.config["path_env_vars"]["RISCV_ROOTFS_HOME"], "rootfsimg"), using_cpu2017, copies)
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


# original func is: https://github.com/OpenXiangShan/riscv-rootfs/blob/c61a659b454e5b038b5374a9091b29ad4995f13f/rootfsimg/spec_gen.py#L558
    def __generate_initramfs(self, scripts_archive_folder, elf_folder, spec, dest_path, using_cpu2017=False, copies=1):
        spec_config = self.config["spec_info"]

        lines = self.config["default_initramfs_file"].copy()
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
        lines.append("set -x")

        for i in range(0, copies):
            lines.append(f"md5sum /spec{i}/{spec_bin}")

        output_redirect = (" ").join([">", "out.log", "2>", "err.log"]) if redirect_output else ""
        force_output_redirect = (" ").join([">", "out.log", "2>", "err.log"])

        taskN = []
        for i in range(0, int(copies)):
            taskN.append("#!/bin/sh")
            taskN.append("set -x")
            taskN.append(f"echo '===== Start running TASK{i} ====='")
            taskN.append("date -R")
            if with_nemu_trap:
                taskN.append("/spec_common/before_workload")

            if spec_bin in ['xalancbmk']:
                taskN.append(f'cd /spec{i} && ./{spec_bin} {spec_cmd} {force_output_redirect} ')
            else:
                taskN.append(f'cd /spec{i} && ./{spec_bin} {spec_cmd} {output_redirect} ')

            taskN.append("date -R")
            if with_nemu_trap:
                if emu=="NEMU":
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

    def build_opensbi_payload(self, spec, copies, bin_suffix = "", gcpt_bin_suffix = "", withGCPT = False):

        print(f"build {spec}-opensbi-linux-spec...{' with GCPT' if withGCPT else ''}")

        self.build_linux_kernel(spec, bin_suffix)
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
