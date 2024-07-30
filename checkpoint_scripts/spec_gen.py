import os
from os.path import realpath
import yaml
import json

# original func is: https://github.com/OpenXiangShan/riscv-rootfs/blob/da983ec95858dfd6f30e9feadd534b79db37e618/rootfsimg/spec_gen.py#L499
def get_default_initramfs_file():
    return [
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
    ]

#, "dir /spec 755 0 0",
#        "file /spec/run.sh ${RISCV_ROOTFS_HOME}/rootfsimg/run.sh 755 0 0"


# original func is: https://github.com/OpenXiangShan/riscv-rootfs/blob/da983ec95858dfd6f30e9feadd534b79db37e618/rootfsimg/spec_gen.py#L544
def traverse_path(path, stack=""):
    all_dirs, all_files = [], []
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        item_stack = os.path.join(stack, item)
        if os.path.isfile(item_path):
            all_files.append(item_stack)
        else:
            all_dirs.append(item_stack)
            sub_dirs, sub_files = traverse_path(item_path, item_stack)
            all_dirs.extend(sub_dirs)
            all_files.extend(sub_files)
    return (all_dirs, all_files)



# original func is: https://github.com/OpenXiangShan/riscv-rootfs/blob/c61a659b454e5b038b5374a9091b29ad4995f13f/rootfsimg/spec_gen.py#L558
def generate_initramfs(scripts_folder, elf_folder, spec, elf_suffix, dest_path, spec_config, CPU2017=False, copy=1):
    lines = get_default_initramfs_file().copy()

    spec_files = spec_config["spec_info"][spec]["files"]

    if CPU2017:
        cpu20xx_run_dir = spec_config["env_vars"]["CPU2017_RUN_DIR"]
    else:
        cpu20xx_run_dir = spec_config["env_vars"]["CPU2006_RUN_DIR"]

    for i in range(0, copy):
        lines.append(f"dir /spec{i} 755 0 0")

    lines.append("file /spec0/run.sh ${RISCV_ROOTFS_HOME}/rootfsimg/run.sh 755 0 0")

    for i in range(0, copy):
        elf_file_abspath = os.path.realpath(f"{elf_folder}/{spec_config['spec_info'][spec]['base_name']}")
        lines.append(f"file /spec{i}/{spec_config['spec_info'][spec]['base_name']} {elf_file_abspath} 755 0 0")

    for i, filename in enumerate(spec_files):
        if len(filename.split()) == 1:
            for j in range(0, copy):
                target_filename = f"file /spec{j}/{filename.split('/')[-1]} {cpu20xx_run_dir}/{filename} 755 0 0"
                lines.append(target_filename)

        elif len(filename.split()) == 3:
            node_type, name, path = filename.split()

            if node_type != "dir":
                print(f"unknown filename: {filename}")
                continue

            all_dirs, all_files = traverse_path(f"{cpu20xx_run_dir}{path}")

            for i in range(0, copy):
                lines.append(f"dir /spec{i}/{name} 755 0 0")
            for sub_dir in all_dirs:
                for i in range(0, copy):
                    lines.append(f"dir /spec{i}/{name}/{sub_dir} 755 0 0")
            for file in all_files:
                for i in range(0, copy):
                    lines.append(f"file /spec{i}/{name}/{file} {cpu20xx_run_dir}{path}/{file} 755 0 0")
        else:
            print(f"unknown filename: {filename}")

    for i in range(0, int(copy)):
        lines.append(f"file /spec{i}/task{i}.sh "+ "${RISCV_ROOTFS_HOME}/rootfsimg/" + f"task{i}.sh 755 0 0")

    with open(os.path.join(dest_path, "initramfs-spec.txt"), "w", encoding="utf-8") as f:
        f.writelines(map(lambda x: x + "\n", lines))
    with open(
            os.path.join(scripts_folder,
                         "{}_initramfs-spec.txt".format(spec)), "w", encoding="utf-8") as f:
        f.writelines(map(lambda x: x + "\n", lines))


# original func is: https://github.com/OpenXiangShan/riscv-rootfs/blob/c61a659b454e5b038b5374a9091b29ad4995f13f/rootfsimg/spec_gen.py#L585
def generate_run_sh(scripts_folder, spec_config, elf_suffix ,spec, dest_path, copy=1, withTrap=False, CPU2017=False, redirect_output=False, emu="NEMU"):
    lines = []
    lines.append("#!/bin/sh")

    if CPU2017:
        SPEC_20XX = "SPEC2017"
        spec_bin = spec_config["spec_info"][spec]["base_name"]
        spec_cmd = " ".join(
            spec_config["spec_info"][spec]["args"])
    else:
        SPEC_20XX = "SPEC2006"
        spec_bin = spec_config["spec_info"][spec]["base_name"]
        spec_cmd = " ".join(
            spec_config["spec_info"][spec]["args"])

    lines.append(f"echo '===== Start running {SPEC_20XX} ====='")

    lines.append(f"echo '======== BEGIN {spec} ========'")
    lines.append("set -x")
    #lines.append("cat /dev/urandom | head -c 16 | busybox hexdump")
    for i in range(0, copy):
        lines.append(f"md5sum /spec{i}/{spec_bin}")

    output_redirect = (" ").join([">", "out.log", "2>", "err.log"]) if redirect_output else ""

    taskN = []
    for i in range(0, int(copy)):
        taskN.append("#!/bin/sh")
        taskN.append("set -x")
        taskN.append(f"echo '===== Start running TASK{i} ====='")
        taskN.append("date -R")
        if withTrap:
            taskN.append("/spec_common/before_workload")
           
        if spec_bin == "perlbench":
            taskN.append(f'cd /spec{i} && ./{spec_bin} {spec_cmd} {output_redirect} ')
        else:
            taskN.append(f'cd /spec{i} && ./{spec_bin} {spec_cmd} {output_redirect} ')

        taskN.append("date -R")
        if withTrap:
            if emu=="NEMU":
                taskN.append("/spec_common/trap")
            else:
                taskN.append("/spec_common/qemu_trap")

        backend_run = '&'

        lines.append(f"/bin/busybox taskset -c {i} /spec{i}/task{i}.sh {backend_run}")
        lines.append(f"PID{i}=$!")
        with open(os.path.join(dest_path, f"task{i}.sh"), "w", encoding="utf-8") as f:
            f.writelines(map(lambda x: x + "\n", taskN))
        with open(os.path.join(scripts_folder, f"{spec}_task{i}.sh"), "w", encoding="utf-8") as f:
            f.writelines(map(lambda x: x + "\n", taskN))
        taskN = []
    for i in range(0, int(copy)):
        lines.append(f"wait $PID{i}")

    lines.append("ls /spec")

    if withTrap:
        if emu=="NEMU":
            taskN.append("/spec_common/trap")
        else:
            taskN.append("/spec_common/qemu_trap")

    lines.append(f"echo '======== END   {spec} ========'")
    lines.append(f"echo '===== Finish running {SPEC_20XX} ====='")

    with open(os.path.join(dest_path, "run.sh"), "w", encoding="utf-8") as f:
        f.writelines(map(lambda x: x + "\n", lines))
    with open(
            os.path.join(scripts_folder,
                         "{}_run.sh".format(spec)), "w", encoding="utf-8") as f:
        f.writelines(map(lambda x: x + "\n", lines))


class SpecGenConfig():
    def __init__(self, spec_info, env_vars_to_check=None) -> None:
        self.env_vars = {}
        if env_vars_to_check:
            for env_var in env_vars_to_check:
                self.env_vars[env_var] = self.check_directory(env_var)

        self.spec_info = spec_info

    def check_directory(self, env_var):
        """Check if the environment variable is set and points to an existing directory."""
        path = os.environ.get(env_var)
        if not path:
            raise EnvironmentError(f"Environment variable {env_var} is not set.")
        if not os.path.exists(path):
            raise EnvironmentError(f"Path {path} for environment variable {env_var} does not exist.")
        return path

    def get_all_config(self):
        return {
            "spec_info": self.spec_info,
            "env_vars": self.env_vars
        }


def prepare_rootfs(spec_info, scripts_folder, elf_folder, spec, copy, withTrap=False, CPU2017=False, redirect_output=False, emu="NEMU"):

    spec_config_obj = SpecGenConfig(spec_info, env_vars_to_check=["RISCV_ROOTFS_HOME", "CPU2017_RUN_DIR", "CPU2006_RUN_DIR"])
    spec_config = spec_config_obj.get_all_config()

    generate_initramfs(scripts_folder=scripts_folder, elf_folder=elf_folder, spec=spec,
                       elf_suffix="",
                       dest_path=os.path.join(spec_config["env_vars"]["RISCV_ROOTFS_HOME"], "rootfsimg"), copy=copy, spec_config = spec_config, CPU2017=CPU2017)

    generate_run_sh(scripts_folder=scripts_folder, spec=spec, spec_config=spec_config,
                    elf_suffix="", copy=copy,
                    dest_path=os.path.join(spec_config["env_vars"]["RISCV_ROOTFS_HOME"], "rootfsimg"),
                    withTrap=withTrap, CPU2017=CPU2017, redirect_output=redirect_output, emu=emu)
