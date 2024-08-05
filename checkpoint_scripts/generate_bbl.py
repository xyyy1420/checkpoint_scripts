import os
import shutil
import subprocess
import os
import subprocess
import shutil
from config import BaseConfig

class Builder(BaseConfig):
    def __init__(self, archive_buffer_layout, spec_info, path_env_vars_to_check=None, env_vars_to_check=None):
        """Initialize Builder with optional environment variables to check."""
        super().__init__(path_env_vars_to_check=path_env_vars_to_check, env_vars_to_check=env_vars_to_check)
        self.config.update(
            **{
                "archive_buffer_layout": {
                    "scripts": archive_buffer_layout.get("scripts"),
                    "elf": archive_buffer_layout.get("elf"),
                    "logs_build": archive_buffer_layout.get("logs_build"),
                    "opensbi": archive_buffer_layout.get("opensbi"),
                    "linux": archive_buffer_layout.get("linux"),
                    "gcpt_bins": archive_buffer_layout.get("gcpt_bins"),
                    "assembly": archive_buffer_layout.get("assembly"),
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
    def __generate_initramfs(self, scripts_folder, elf_folder, spec, dest_path, using_cpu2017=False, copies=1):
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

        lines.append("file /spec0/run.sh ${RISCV_ROOTFS_HOME}/rootfsimg/run.sh 755 0 0")

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
            lines.append(f"file /spec{i}/task{i}.sh "+ "${RISCV_ROOTFS_HOME}/rootfsimg/" + f"task{i}.sh 755 0 0")

        with open(os.path.join(dest_path, "initramfs-spec.txt"), "w", encoding="utf-8") as f:
            f.writelines(map(lambda x: x + "\n", lines))
        with open(
                os.path.join(scripts_folder,
                             "{}_initramfs-spec.txt".format(spec)), "w", encoding="utf-8") as f:
            f.writelines(map(lambda x: x + "\n", lines))

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

        taskN = []
        for i in range(0, int(copies)):
            taskN.append("#!/bin/sh")
            taskN.append("set -x")
            taskN.append(f"echo '===== Start running TASK{i} ====='")
            taskN.append("date -R")
            if with_nemu_trap:
                taskN.append("/spec_common/before_workload")

            if spec_bin == "perlbench":
                taskN.append(f'cd /spec{i} && ./{spec_bin} {spec_cmd} {output_redirect} ')
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
            with open(os.path.join(run_scripts_dest_path, f"task{i}.sh"), "w", encoding="utf-8") as f:
                f.writelines(map(lambda x: x + "\n", taskN))
            with open(os.path.join(run_scripts_archive_path, f"{spec}_task{i}.sh"), "w", encoding="utf-8") as f:
                f.writelines(map(lambda x: x + "\n", taskN))
            taskN = []
        for i in range(0, int(copies)):
            lines.append(f"wait $PID{i}")

        lines.append("ls /spec")
        lines.append(f"echo '======== END   {spec} ========'")
        lines.append(f"echo '===== Finish running {SPEC_20XX} ====='")

        with open(os.path.join(run_scripts_dest_path, "run.sh"), "w", encoding="utf-8") as f:
            f.writelines(map(lambda x: x + "\n", lines))
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
        self.copy_files(self.path_env_vars.get("RISCV_PK_HOME"), spec, bin_suffix, assembly_folder, spec_bin_folder, {
            "build/bbl.bin": "",
            "build/bbl.txt": ".pk.s",
            "build/vmlinux.txt": ".vmlinux.s"
        })

        if qemu_payload:
            gcpt_commands = [["make", "clean"], ["make", "USING_QEMU_DUAL_CORE_SYSTEM=1", f"GCPT_PAYLOAD_PATH={os.path.join(PK_HOME, 'build', 'bbl.bin')}", "-j10"]]

            self.run_commands(gcpt_commands, GCPT_HOME, out_log, err_log)
            self.copy_files(GCPT_HOME, spec, bin_suffix, assembly_folder, spec_bin_folder, {
                "build/gcpt.bin": ""
            })

    def build_opensbi_payload(self, spec,  bin_suffix, gcpt_bin_suffix, withGCPT=False, using_share_folder=False):
        archive_buffer_layout = self.config["archive_buffer_layout"]
        required_path_vars = ["LINUX_HOME", "OPENSBI_HOME", "XIANGSHAN_FDT", "GCPT_HOME", "RISCV_ROOTFS_HOME"]
        if not all([self.path_env_vars.get(var) for var in required_path_vars]):
            raise EnvironmentError("One or more required environment variables are not set or not initialized.")
        required_vars = ["ARCH"]
        if not all([self.env_vars.get(var) for var in required_vars]):
            raise EnvironmentError("One or more required environment variables are not set or not initialized.")

        print(f"build {spec}-opensbi-linux-spec...{' with GCPT' if withGCPT else ''}")

        if not isinstance(archive_buffer_layout["logs_build"], str):
            raise ValueError(f"The 'logs_build' key in bbl generate config must be a string and must exist.")

        out_log = os.path.join(archive_buffer_layout["logs_build"], f"build-binary-with-{spec}-out.log")
        err_log = os.path.join(archive_buffer_layout["logs_build"], f"build-binary-with-{spec}-err.log")

        linux_commands = [["make", "-j70"]]

        shared_linux_command = [
            ["make", "-C", f"{self.path_env_vars['LINUX_HOME']}", f"O={archive_buffer_layout['linux']}", "xiangshan_defconfig"],
            ["make", "-C", f"{self.path_env_vars['LINUX_HOME']}", f"O={archive_buffer_layout['linux']}", "-j70"]
        ]

        if using_share_folder:
            self.run_commands(shared_linux_command, None, out_log, err_log)
        else:
            self.run_commands(linux_commands, self.path_env_vars["LINUX_HOME"], out_log, err_log)

        # reset fw_payload_fdt_addr
        if using_share_folder:
            fw_payload_bin = f"{archive_buffer_layout['linux']}/arch/riscv/boot/Image"
        else:
            fw_payload_bin = f"{self.path_env_vars['LINUX_HOME']}/arch/riscv/boot/Image"

        fw_payload_bin_size = os.path.getsize(fw_payload_bin)
        fw_payload_fdt_addr = (((fw_payload_bin_size + 0x800000) + 0xfffff) // 0x100000) * 0x100000
        fw_payload_fdt_addr = fw_payload_fdt_addr + 0x80000000
        print(f"SPEC: {spec}, file size: {fw_payload_bin_size:X}, fw_payload_fdt_addr: {fw_payload_fdt_addr:X}")

        opensbi_commands = [
            ["rm", "-rf", "build"],
            ["make", "PLATFORM=generic", f"FW_PAYLOAD_PATH={fw_payload_bin}", f"FW_FDT_PATH={self.path_env_vars['XIANGSHAN_FDT']}", "FW_PAYLOAD_OFFSET=0x700000", f"FW_PAYLOAD_FDT_ADDR={fw_payload_fdt_addr}", "-j10"]
        ]

        shared_opensbi_command = []
        if os.path.exists(f"{archive_buffer_layout['opensbi']}/build"):
            shared_opensbi_command.append(["rm", "-rf", f"{archive_buffer_layout['opensbi']}/build"])

        shared_opensbi_command.append(
            ["make", "-C", self.path_env_vars["OPENSBI_HOME"], f"O={archive_buffer_layout['opensbi']}/build", "PLATFORM=generic", f"FW_PAYLOAD_PATH={fw_payload_bin}", f"FW_FDT_PATH={self.path_env_vars['XIANGSHAN_FDT']}", "FW_PAYLOAD_OFFSET=0x700000", f"FW_PAYLOAD_FDT_ADDR={fw_payload_fdt_addr}", "-j10"]
        )

        if using_share_folder:
            self.run_commands(shared_opensbi_command, None, out_log, err_log)
        else:
            self.run_commands(opensbi_commands, self.path_env_vars["OPENSBI_HOME"], out_log, err_log)

#        fw_payload_bin_dst_path = os.path.join(spec_bin_folder, f"{spec}{bin_suffix}")
        # copy fw_payload.bin to another folder: FIX
        if using_share_folder:
            self.copy_files(archive_buffer_layout["opensbi"], spec, bin_suffix, archive_buffer_layout["assembly"], archive_buffer_layout["gcpt_bins"], {
                "build/platform/generic/firmware/fw_payload.bin": ""
            })
        else:
            self.copy_files(self.path_env_vars["OPENSBI_HOME"], spec, bin_suffix, archive_buffer_layout["assembly"], archive_buffer_layout["gcpt_bins"], {
                "build/platform/generic/firmware/fw_payload.bin": ""
            })
 

        if withGCPT:
            if using_share_folder:
                if not isinstance(archive_buffer_layout["opensbi"], str):
                    raise ValueError(f"The 'opensbi' key in bbl generate config must be a string and must exist.")

                gcpt_commands = [["make", "clean"], ["make", f'GCPT_PAYLOAD_PATH={os.path.join(archive_buffer_layout["opensbi"],"build","platform","generic","firmware","fw_payload.bin")}', "USING_QEMU_DUAL_CORE_SYSTEM=1"]]
            else:
                gcpt_commands = [["make", "clean"], ["make", f'GCPT_PAYLOAD_PATH={os.path.join(self.path_env_vars["OPENSBI_HOME"],"build","platform","generic","firmware","fw_payload.bin")}', "USING_QEMU_DUAL_CORE_SYSTEM=1"]]

            self.run_commands(gcpt_commands, self.path_env_vars["GCPT_HOME"], out_log, err_log)
            self.copy_files(self.path_env_vars["GCPT_HOME"], spec, gcpt_bin_suffix, archive_buffer_layout["assembly"], archive_buffer_layout["gcpt_bins"], {
                "build/gcpt.bin": "",
                "build/gcpt.txt": ".gcpt.s"
            })

    @staticmethod
    def copy_files(base_path, spec, suffix, assembly_folder, bin_folder, files):
        """Copy files from base path to their respective destinations with appropriate suffixes."""
        for src, dest_suffix in files.items():
            src_path = os.path.join(base_path, src)

            if dest_suffix:
                assembly_dest_path = os.path.join(assembly_folder, f"{spec}{suffix}{dest_suffix}")
                shutil.copy(src_path, assembly_dest_path)
                continue

            bin_dest_path = os.path.join(bin_folder, f"{spec}{suffix}")
            shutil.copy(src_path, bin_dest_path)

# Example usage
#builder = Builder(env_vars_to_check=["LINUX_HOME", "OPENSBI_HOME", "XIANGSHAN_FDT", "NEMU_HOME", "RISCV_PK_HOME"])
#builder.build_spec_bbl("example_spec", "/path/to/logs", "/path/to/bin", "_suffix", "/path/to/assembly")
#builder.build_opensbi_payload("example_spec", "/path/to/logs", "/path/to/bin", "_suffix", "/path/to/gcpt_bin", "_gcpt_suffix", "/path/to/assembly", withGCPT=True)
#
