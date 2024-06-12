import os
import yaml
import pathlib
from datetime import datetime
import argparse
import shutil
import subprocess
import concurrent.futures
from spec_gen import prepare_rootfs
from spec_gen import get_cpu2017_info
from spec_gen import get_cpu2006_info
from generate_bbl import Builder
from take_checkpoint import set_startid_times
from take_checkpoint import generate_command
from take_checkpoint import level_first_exec

default_config = {
    "logs": "logs",
    "buffer": "",
    "archive_folder": "archive",
    "archive_id": "",
    "elf_suffix": "_base.riscv64-linux-gnu-gcc12.2.0",
}


def def_config():
    return default_config


def prepare_config():
    return {
        "prepare_log":
        os.path.join(def_config()["buffer"],
                     def_config()["logs"], "prepare"),
        "elf_folder":
        os.path.join(def_config()["buffer"], "elf"),
    }


def build_config():
    return {
        "build_log":
        os.path.join(def_config()["buffer"],
                     def_config()["logs"], "build"),
        "bin_folder":
        os.path.join(def_config()["buffer"], "bin"),
        "scripts_folder":
        os.path.join(def_config()["buffer"], "scripts"),
        "gcpt_bin_folder":
        os.path.join(def_config()["buffer"], "gcpt_bins"),
        "assembly_folder":
        os.path.join(def_config()["buffer"], "assembly"),
    }


def mkdir(path):
    if not pathlib.Path(path).exists():
        os.makedirs(path)


def create_folders():
    for value in build_config().values():
        mkdir(value)
    for value in prepare_config().values():
        mkdir(value)


def generate_archive_info(message):
    with open(os.path.join(def_config()["archive_folder"], "archive_info"),
              "a", encoding="utf-8") as f:
        f.write("{}: {}\n".format(def_config()["archive_id"], message))


folder_name_config = {
    "gcc_version": "gcc14.0.0",
    "riscv_ext": "rv64gcv",
    "base_or_fixed": "base",
    "special_flag": "nospecial",
    "emulator": "NEMU",
    "group": "archgroup",
    "time": ""
}


def generate_buffer_folder_name():
    folder_name_config["time"] = datetime.now().strftime("%Y-%m-%d-%H-%M")
    folder_name = "{}_{}_{}_{}_{}_{}_{}".format(
        folder_name_config["gcc_version"], folder_name_config["riscv_ext"],
        folder_name_config["base_or_fixed"],
        folder_name_config["special_flag"], folder_name_config["emulator"],
        folder_name_config["group"], folder_name_config["time"])
    return folder_name


def entrys(path):
    entrys_list = []
    with os.scandir(path) as el:
        for entry in el:
            entrys_list.append(entry)
    return entrys_list


def generate_folders(config):
    # set archive id from arg
    if config["archive_id"] is None:
        default_config["archive_id"] = generate_buffer_folder_name()
    else:
        default_config["archive_id"] = config["archive_id"]

    default_config["buffer"] = os.path.join(def_config()["archive_folder"],
                                            def_config()["archive_id"])
    if config["archive_id"] is None:
        create_folders()

    assert (os.path.exists(def_config()["buffer"]))

    if config["message"] is not None:
        generate_archive_info(config["message"])


def dump_assembly(file_path, assembly_file):
    if file_path is not None:
        with open(assembly_file, "w", encoding="utf-8") as out:
            res = subprocess.run(
                ["riscv64-unknown-linux-gnu-objdump", "-d", file_path],
                stdout=out, check=False)
            res.check_returncode()


def copy_to_dst(file, src_dir, dst_dir):
    if os.path.exists(os.path.join(src_dir, file)):
        shutil.copy(os.path.join(src_dir, file), os.path.join(dst_dir, file))
        return os.path.join(dst_dir, file)
    else:
        print(file, "Not found")
        return None

spec_2006_list=[]
spec_2017_list=[]

def app_list(list_path, app_list, CPU2017):
    if list_path is None and app_list is None:
        if CPU2017:
            return spec_2017_list
        else:
            return spec_2006_list
    elif list_path is None and app_list is not None:
        apps = app_list.split(",")
        return list(set(apps))
    else:
        app_list = []
        with open(list_path, encoding="utf-8") as f:
            app_list = f.read().splitlines()
        return list(set(app_list))


def copy_and_get_assembly(spec, elfs):
    dst_file_path = copy_to_dst(spec, elfs,
                                prepare_config()["elf_folder"])
    dump_assembly(
        dst_file_path,
        os.path.join(build_config()["assembly_folder"], spec + ".txt"))


def generate_specapp_assembly(spec_base_app_list, elfs, max_threads):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as e:
        list(map(lambda spec: e.submit(copy_and_get_assembly, spec, elfs), spec_base_app_list))

def main(config):
    spec_app_list = app_list(config["spec_app_list"], config["spec_apps"], config["CPU2017"])
    if config["CPU2017"]:
        spec_base_app_list = list(set(
            map(lambda item: os.path.split(get_cpu2017_info(os.environ.get("CPU2017_RUN_DIR"), "", "")[item][0][0])[1], spec_app_list)))
    else:
        spec_base_app_list = list(set(
            map(lambda item: os.path.split(get_cpu2006_info(os.environ.get("CPU2006_RUN_DIR"), "", "")[item][0][0])[1], spec_app_list)))

    print(spec_base_app_list)

    set_startid_times(config["start_id"], config["times"])

    generate_folders(config)

    if config["archive_id"] is None:
        generate_specapp_assembly(spec_base_app_list, config["elf_folder"], config["max_threads"])

        spec_app_execute_list = []
        for spec_app in spec_app_list:
            prepare_rootfs(scripts_folder=build_config()["scripts_folder"], elf_folder=prepare_config()["elf_folder"], spec=spec_app, withTrap=True, copy=config["copies"], CPU2017=config["CPU2017"])

            if config["generate_rootfs_script_only"]:
                continue

            builder = Builder(env_vars_to_check=["RISCV_PK_HOME"])
            if config["emulator"] == "QEMU":
                builder.build_opensbi_payload(spec_app, build_config()["build_log"], build_config()["bin_folder"], "", build_config()["gcpt_bin_folder"], "", build_config()["assembly_folder"])
            else:
                builder.build_spec_bbl(spec_app, build_config()["build_log"], build_config()["bin_folder"], "", build_config()["assembly_folder"])

            if config["build_bbl_only"]:
                continue

            root_noods = generate_command(build_config()["bin_folder"], spec_app, def_config()["buffer"], "", config["emulator"], os.path.join(def_config()["buffer"], "logs"))

            spec_app_execute_list.append(root_noods)

        if spec_app_execute_list is not []:
            with concurrent.futures.ProcessPoolExecutor(max_workers=config["max_threads"]) as e:
                e.map(level_first_exec, spec_app_execute_list)
#        generate_result(def_config()["buffer"], os.path.join(def_config()["buffer"], "logs"))
    else:
        spec_app_execute_list = []
        for spec_app in spec_app_list:
            root_noods = generate_command(build_config()["bin_folder"], spec_app, def_config()["buffer"], "", config["emulator"], os.path.join(def_config()["buffer"], "logs"))

#            list(map(print_tree, root_noods))
            spec_app_execute_list.append(root_noods)

        with concurrent.futures.ProcessPoolExecutor(max_workers=config["max_threads"]) as e:
            e.map(level_first_exec, spec_app_execute_list)
#


def load_config(config_file):
    with open(config_file, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto profiling and checkpointing")
    parser.add_argument('--config', default='config.yaml', help="Path to the configuration file (default: config.yaml)")
    args = parser.parse_args()

    config = load_config(args.config)
    main(config)

