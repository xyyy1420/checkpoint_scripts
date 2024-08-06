from collections import deque
import os
import sys
import pathlib
from datetime import datetime
import argparse
import shutil
import subprocess
import concurrent.futures
from concurrent.futures import Future
import signal
from generate_bbl import RootfsBuilder
from take_checkpoint import TakeCheckpointConfig
from take_checkpoint import generate_command
from take_checkpoint import level_first_exec
from config import BaseConfig
from typing import List, Tuple


def entrys(path):
    """seems useless"""
    entrys_list = []
    with os.scandir(path) as el:
        for entry in el:
            entrys_list.append(entry)
    return entrys_list


def dump_assembly(file_path, assembly_file):
    """generate assembly file"""
    if file_path is not None:
        with open(assembly_file, "w", encoding="utf-8") as out:
            res = subprocess.run(
                ["riscv64-unknown-linux-gnu-objdump", "-d", file_path],
                stdout=out,
                check=False)
            res.check_returncode()
    return (assembly_file, 1)


def copy_and_get_assembly(cp_src, elf, cp_dst) -> Tuple[str, str]:
    # copy
    if os.path.exists(os.path.join(cp_src, elf)):
        shutil.copy(os.path.join(cp_src, elf), os.path.join(cp_dst, elf))
        cp_dst_file_path = os.path.join(cp_dst, elf)
        return (elf, cp_dst_file_path)
    else:
        print(os.path.join(cp_dst, elf), "Not found")
        exit(1)


def generate_specapp_assembly(spec_base_app_list, elf_src_path, elf_dst_path,
                              assembly_path, max_threads):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as e:
        submit_result: List[Future[Tuple[str, str]]] = [
            e.submit(copy_and_get_assembly, elf_src_path, spec_app,
                     elf_dst_path) for spec_app in spec_base_app_list
        ]
        cp_dst_file_path_list: List[Tuple[str, str]] = [
            future.result() for future in submit_result
        ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as e:
        list(
            map(
                lambda item: e.submit(
                    dump_assembly, item[1],
                    os.path.join(assembly_path, item[0] + ".txt")),
                cp_dst_file_path_list))


def handle_keyboard_interrupt(signum, frame):
    print("Caught KeyboardInterrupt, shutting down...")
    raise KeyboardInterrupt


class globalConfigCtx(BaseConfig):

    def __init__(self, config_path) -> None:
        # load user config
        self.__user_config = super().load_yaml(config_path)
        self.__base_config = self.__user_config["base_config"]
        self.__archive_id_config = self.__user_config["archive_id_config"]

        # load spec app info
        if self.__base_config["CPU2017"]:
            self.__spec_app_info = super().load_yaml("spec_info/spec17.json")
        else:
            self.__spec_app_info = super().load_yaml("spec_info/spec06.json")

        # parse app info in user config, list file has a higher priority
        if self.__base_config["spec_app_list"] is None and self.__base_config[
                "spec_apps"] is None:
            self.__app_list = [key for key in self.__spec_app_info.keys()]

        elif self.__base_config["spec_app_list"] is None and self.__base_config[
                "spec_apps"] is not None:
            apps = self.__base_config["spec_apps"].split(",")
            self.__app_list = list(set(apps))
        else:
            app_list = []
            with open(self.__base_config["spec_app_list"],
                      encoding="utf-8") as f:
                app_list = f.read().splitlines()
            self.__app_list = list(set(app_list))

        # parse base app
        self.__base_app_list = list(
            set([
                self.__spec_app_info[app_name]["base_name"]
                for app_name in self.__app_list
            ]))

        # generate buffer_path
        # if not set already exists archive id, script will create new archive id, and generate folder tree
        self.__buffer_path = os.path.join(
            "archive", self.__base_config["archive_id"]
            if self.__base_config["archive_id"] is not None else
            self.__generate_buffer_folder_name())
        self.__buffer_path = os.path.realpath(self.__buffer_path)

        # set global config
        self.global_config = {
            "user_config": self.__user_config,
            "base_config": self.__base_config,
            "archive_id_config": self.__archive_id_config,
            "spec_app_info": self.__spec_app_info,
            "app_list": self.__app_list,
            "base_app_list": self.__base_app_list,
            "archive_buffer_layout": {
                "buffer_path": self.__buffer_path,
                "elf": os.path.join(self.__buffer_path, "elf"),
                "logs": os.path.join(self.__buffer_path, "logs"),
                "logs_build": os.path.join(self.__buffer_path, "logs", "build"),
                "logs_prepare": os.path.join(self.__buffer_path, "logs", "prepare"),
                "bin": os.path.join(self.__buffer_path, "bin"),
                "scripts": os.path.join(self.__buffer_path, "scripts"),
                "gcpt_bins": os.path.join(self.__buffer_path, "gcpt_bins"),
                "assembly": os.path.join(self.__buffer_path, "assembly"),
                "binary_archive": os.path.join(self.__buffer_path, "binary_archive")
            }
        }

        if self.__base_config["using_share_folder"]:
            self.global_config["archive_buffer_layout"].update({
                "linux": os.path.join(self.__buffer_path, "build", "linux"),
                "opensbi": os.path.join(self.__buffer_path, "build", "opensbi"),
                "rootfs": os.path.join(self.__buffer_path, "build", "rootfs"),
                "gcpt": os.path.join(self.__buffer_path, "build", "gcpt")
            })

    def __generate_buffer_folder_name(self):
        """using compile and env info generate archive id"""
        base_config = self.__base_config
        archive_id_config = self.__archive_id_config
        time = datetime.now().strftime("%Y-%m-%d-%H-%M")

        if base_config["CPU2017"]:
            spec_20xx = "spec17"
        else:
            spec_20xx = "spec06"

        folder_name = f'{spec_20xx}_{archive_id_config["gcc_version"]}_{archive_id_config["riscv_ext"]}_{archive_id_config["base_or_fixed"]}_{archive_id_config["special_flag"]}_{base_config["emulator"]}_{archive_id_config["group"]}_{time}'
        return folder_name

    def get_global_config(self):
        return self.global_config


def generate_buffer_folder(archive_buffer_layout):
    """create prepare and build folder"""
    for value in archive_buffer_layout.values():
        if not pathlib.Path(value).exists():
            os.makedirs(value)


def main(config_ctx: globalConfigCtx):
    global_config = config_ctx.get_global_config()
    base_config = global_config["base_config"]
    spec_app_list = global_config["app_list"]
    spec_base_app_list = global_config["base_app_list"]
    archive_buffer_layout = global_config["archive_buffer_layout"]

    # generate buffer folder
    if base_config["archive_id"] is None:
        generate_buffer_folder(archive_buffer_layout)
    assert (os.path.exists(archive_buffer_layout["buffer_path"]))

    print(spec_base_app_list)

    take_checkpoint_config_obj = TakeCheckpointConfig(
        path_env_vars_to_check=["NEMU_HOME", "QEMU_HOME"])

    # start id: start id is 0,0,0 means profiling-0 cluster-0-0 checkpoint-0-0-0
    # times 1,2,3 means once profiling, per profiling twice cluster, per cluster third times checkpoint
    take_checkpoint_config_obj.set_startid_times(base_config["start_id"],
                                                 base_config["times"])

    # get take checkpoint config
    take_checkpoint_config = take_checkpoint_config_obj.get_config()

    # get workload folder
    workload_folder = archive_buffer_layout["gcpt_bins"] if base_config[
        "emulator"] == "QEMU" else archive_buffer_layout["bin"]

    # create rootfs builder
    if base_config["bootloader"] == "opensbi":
        builder = RootfsBuilder(archive_buffer_layout,
                                global_config["spec_app_info"],
                                path_env_vars_to_check=[
                                    "LINUX_HOME", "OPENSBI_HOME",
                                    "XIANGSHAN_FDT", "GCPT_HOME",
                                    "RISCV_ROOTFS_HOME", "CPU2006_RUN_DIR",
                                    "CPU2017_RUN_DIR", "QEMU_HOME", "NEMU_HOME"
                                ],
                                env_vars_to_check=["ARCH"])
    else:
        builder = RootfsBuilder(archive_buffer_layout,
                                global_config["spec_app_info"],
                                path_env_vars_to_check=[
                                    "RISCV_PK_HOME", "GCPT_HOME",
                                    "RISCV_ROOTFS_HOME", "CPU2006_RUN_DIR",
                                    "CPU2017_RUN_DIR"
                                ])

    # if not set already exists archive id, script will generate benchmark assembly, generate rootfs, build bbl, and start checkpoint
    if base_config["archive_id"] is None:
        # copy elf to buffer and generate assembly
        generate_specapp_assembly(spec_base_app_list,
                                  base_config["elf_folder"],
                                  archive_buffer_layout["elf"],
                                  archive_buffer_layout["assembly"],
                                  base_config["max_threads"])

        spec_app_execute_list = []
        for spec_app in spec_app_list:
            builder.prepare_rootfs(
                spec_app,
                using_cpu2017=base_config["CPU2017"],
                copies=base_config["copies"],
                with_nemu_trap=True,
                redirect_output=base_config["redirect_output"],
                emu=base_config["emulator"])

            if base_config["generate_rootfs_script_only"]:
                continue

            if base_config["emulator"] == "QEMU":
                assert base_config["all_in_one_workload"]

            if base_config["bootloader"] == "opensbi":
                builder.build_opensbi_payload(
                    spec_app,
                    withGCPT=True)
            else:
                builder.build_spec_bbl(spec_app,
                                       archive_buffer_layout["logs_build"],
                                       archive_buffer_layout["bin"], "",
                                       archive_buffer_layout["assembly"],
                                       False)

            if base_config["boot_for_test"]:
                builder.boot_test(base_config["copies"])

            if base_config["build_bbl_only"]:
                continue

            root_noods = generate_command(
                workload_folder=workload_folder,
                workload=spec_app,
                buffer=archive_buffer_layout["buffer_path"],
                bin_suffix="",
                config=take_checkpoint_config,
                emu=base_config["emulator"],
                log_folder=archive_buffer_layout["logs"],
                cpu_bind=base_config["cpu_bind"],
                mem_bind=base_config["mem_bind"],
                copies=str(base_config["copies"]),
                all_in_one_workload=base_config["all_in_one_workload"],
            )

            spec_app_execute_list.append(root_noods)

        if spec_app_execute_list is not []:
            with concurrent.futures.ProcessPoolExecutor(
                    max_workers=base_config["max_threads"]) as e:
                futures = []
                try:
                    futures = {
                        e.submit(level_first_exec, task): task
                        for task in spec_app_execute_list
                    }
#                    e.map(level_first_exec, spec_app_execute_list)
                except KeyboardInterrupt:
                    for future in futures:
                        future.cancel()
                    e.shutdown(wait=False)
            #        generate_result(def_config()["buffer"], os.path.join(def_config()["buffer"], "logs"))

    # if set already exists archive id, will start checkpoint immidiatly, but archive must have valid binary file
    else:
        spec_app_execute_list = []
        resume_after = base_config.get("resume_after", None)
        for spec_app in spec_app_list:
            root_noods = generate_command(
                workload_folder=workload_folder,
                workload=spec_app,
                buffer=archive_buffer_layout["buffer_path"],
                bin_suffix="",
                config=take_checkpoint_config,
                emu=base_config["emulator"],
                log_folder=archive_buffer_layout["logs"],
                cpu_bind=base_config["cpu_bind"],
                mem_bind=base_config["mem_bind"],
                copies=str(base_config["copies"]),
                resume_after=resume_after,
                all_in_one_workload=base_config["all_in_one_workload"],
            )

            #            list(map(print_tree, root_noods))
            spec_app_execute_list.append(root_noods)

        with concurrent.futures.ProcessPoolExecutor(
                max_workers=base_config["max_threads"]) as e:
            futures = []
            try:
                futures = {
                    e.submit(level_first_exec, task): task
                    for task in spec_app_execute_list
                }


#                e.map(level_first_exec, spec_app_execute_list)
            except KeyboardInterrupt:
                for future in futures:
                    future.cancel()
                e.shutdown(wait=False)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_keyboard_interrupt)
    parser = argparse.ArgumentParser(
        description="Auto profiling and checkpointing")
    parser.add_argument(
        '--config',
        default='config.yaml',
        help="Path to the configuration file (default: config.yaml)")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_usage()
        sys.exit(1)

    config_ctx = globalConfigCtx(args.config)

    main(config_ctx)
