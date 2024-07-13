import os
import pathlib
import itertools
import functools
import copy
import random
import concurrent.futures
import subprocess
from collections import deque


default_config = {
    "NEMU": {
        "NEMU_HOME":
        os.environ.get("NEMU_HOME"),
        "NEMU":
        os.path.join(os.environ.get("NEMU_HOME"), "build",
                     "riscv64-nemu-interpreter"),
        "gcpt_restore_home":
        os.path.join(os.environ.get("NEMU_HOME"), "resource", "gcpt_restore"),
        "gcpt_restore":
        os.path.join(os.environ.get("NEMU_HOME"), "resource", "gcpt_restore",
                     "build", "gcpt.bin"),
        "simpoint":
        os.path.join(os.environ.get("NEMU_HOME"), "resource", "simpoint",
                     "simpoint_repo", "bin", "simpoint"),
    },
    "QEMU": {
        "QEMU_HOME":
        os.environ.get("QEMU_HOME"),
        "QEMU":
        os.path.join(os.environ.get("QEMU_HOME"), "build",
                     "qemu-system-riscv64"),
        "memory":
        "8G",
        "smp":
        "1",
        "profiling_plugin":
        os.path.join(os.environ.get("QEMU_HOME"), "build", "contrib", "plugins",
                     "libprofiling.so"),
    },
    "utils": {
        "workload_folder": "",
        "compile_format": "zstd",
        "interval": "20000000",
        "workload": "",
        "buffer": "",
        "bin_suffix": "",
        "log_folder": ""
    },
    "profiling": {
        "basename": "profiling",
        "id": "0",
        "times": "1",
        "config": ""
    },
    "cluster": {
        "basename": "cluster",
        "id": "0",
        "times": "1",
        "config": ""
    },
    "checkpoint": {
        "basename": "checkpoint",
        "id": "0",
        "times": "1",
        "config": "",
    },
    "command": [],
    "emu": "",
    "out-log:": "",
    "err-log": "",
    "execute_mode": "",
    "cpu_bind": "",
    "mem_bind": ""
}


def get_config():
    return default_config


def mkdir(path):
    if not pathlib.Path(path).exists():
        os.makedirs(path)


class CheckpointTree:

    def __init__(self, value):
        self.value = value
        self.children = []

    def add_child(self, child_node):
        self.children.append(child_node)

    def execute(self):
        out_file = self.value["out-log"]
        err_file = self.value["err-log"]

        mkdir(os.path.split(out_file)[0])

        try:
            if "backup_commands" in self.value:
                for command in self.value["backup_commands"]:
                    res = subprocess.run(command, check=True)
                    print("Backup:", command, res.returncode, res.stdout, res.stderr)

            with open(out_file, "w", encoding="utf-8") as out, open(err_file, "w", encoding="utf-8") as err:
                command = self.value["command"]
                print((command))
                print(self.value["utils"]["workload"], self.value["execute_mode"])
                res = subprocess.run(command, stdout=out, stderr=err, check=False)
                print(command + "Execute finish")
                return res
        except subprocess.CalledProcessError as e:
            print(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}")
            with open(err_file, "a", encoding="utf-8") as err:
                err.write(f"\nCommand '{e.cmd}' returned non-zero exit status {e.returncode}\n")
        except FileNotFoundError as e:
            print(f"File not found error: {e}")
            with open(err_file, "a", encoding="utf-8") as err:
                err.write(f"\nFile not found error: {e}\n")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            with open(err_file, "a", encoding="utf-8") as err:
                err.write(f"\nAn unexpected error occurred: {e}\n")
            raise  # Rethrow the exception after logging it

    def __repr__(self):
        return "TreeNode({}, {}, {}, {})".format(
            self.value["profiling"]["config"], self.value["cluster"]["config"],
            self.value["checkpoint"]["config"], self.value["command"])


def print_tree(node, level=0):
    print("  " * level + str(node))
    for child in node.children:
        print_tree(child, level + 1)


def deep_first_exec(node, level=0):
    print("  " * level + str(node))
    res = node.execute()
    res.check_returncode()
    for child in node.children:
        deep_first_exec(child, level + 1)


def level_first_exec(root):
    if root is None:
        print("root is none")
        return

    queue = deque([root])

    while queue:
        level_size = len(queue)
        execute_list = []
        for _ in range(level_size):
            node = queue.popleft()
            execute_list.append(node)
            for child in node.children:
                queue.append(child)
        with concurrent.futures.ProcessPoolExecutor() as e:
            futures = []
            try:
                futures = {e.submit(task.execute):task for task in execute_list}
#                list(map(lambda x: e.submit(x.execute), execute_list))
            except KeyboardInterrupt:
                for future in futures:
                    future.cancel()
                e.shutdown(wait=False)
        print("---- Level Execute finish ----")


profiling_configs = list(
    itertools.product(
        range(int(get_config()["profiling"]["id"]),
              int(get_config()["profiling"]["times"]))))
cluster_configs = list(
    itertools.product(
        range(int(get_config()["profiling"]["id"]),
              int(get_config()["profiling"]["times"])),
        range(int(get_config()["cluster"]["id"]),
              int(get_config()["cluster"]["times"]))))
checkpoint_configs = list(
    itertools.product(
        range(int(get_config()["profiling"]["id"]),
              int(get_config()["profiling"]["times"])),
        range(int(get_config()["cluster"]["id"]),
              int(get_config()["cluster"]["times"])),
        range(int(get_config()["checkpoint"]["id"]),
              int(get_config()["checkpoint"]["times"]))))

profiling_roots = CheckpointTree(None)

def nemu_profiling_command(config):
    command = [
        "numactl","--cpunodebind={}".format(config["cpu_bind"]),"--membind={}".format(config["mem_bind"]),
        config["NEMU"]["NEMU"],
        "{}/{}{}".format(config["utils"]["workload_folder"], config["utils"]["workload"], config["utils"]["bin_suffix"]),
        "-D", config["utils"]["buffer"],
        "-C", config["profiling"]["config"],
        "-w", config["utils"]["workload"],
        "-b",
        "--simpoint-profile",
        "--cpt-interval", config["utils"]["interval"],
        "-r", config["NEMU"]["gcpt_restore"],
        "--checkpoint-format", config["utils"]["compile_format"]
    ]
    return command

def qemu_profiling_command(config):
    command = [
        "numactl","--cpunodebind={}".format(config["cpu_bind"]),"--membind={}".format(config["mem_bind"]),
        config["QEMU"]["QEMU"],
        "-bios", f'{config["utils"]["workload_folder"]}/{config["utils"]["workload"]}{config["utils"]["bin_suffix"]}',
        "-M", "nemu",
        "-nographic",
        "-m", config["QEMU"]["memory"],
        "-smp", config["QEMU"]["smp"],
        "-cpu", "rv64,v=true,vlen=128,h=false,sv39=true,sv48=false,sv57=false,sv64=false",
        "-plugin", "{},workload={},intervals={},target={}".format(
            config["QEMU"]["profiling_plugin"],
            config["utils"]["workload"],
            config["utils"]["interval"],
            os.path.join(config["utils"]["buffer"], config["profiling"]["config"], config["utils"]["workload"]))
    ]
    return command


def cluster_command(config, is_resume_from):
    seedkm = random.randint(100000, 999999)
    seedproj = random.randint(100000, 999999)
    mkdir(os.path.split(os.path.join(config["utils"]["buffer"], config["cluster"]["config"], config["utils"]["workload"], "simpoints0"))[0])
    bbv_path = os.path.join(config["utils"]["buffer"], config["profiling"]["config"], config["utils"]["workload"], "simpoint_bbv.gz")
    if is_resume_from:
        # make sure bbv.gz has been generated
        assert os.path.exists(bbv_path)
    command = [
        "numactl","--cpunodebind={}".format(config["cpu_bind"]),"--membind={}".format(config["mem_bind"]),
        config["NEMU"]["simpoint"],
        "-loadFVFile", bbv_path,
        "-saveSimpoints", os.path.join(config["utils"]["buffer"], config["cluster"]["config"], config["utils"]["workload"], "simpoints0"),
        "-saveSimpointWeights", os.path.join(config["utils"]["buffer"], config["cluster"]["config"], config["utils"]["workload"], "weights0"),
        "-inputVectorsGzipped",
        "-maxK", "30",
        "-numInitSeeds", "2",
        "-iters", "1000",
        "-seedkm", f"{seedkm}", "-seedproj", f"{seedproj}"
    ]
    return command

def nemu_checkpoint_command(config, is_resume_from):
    simpoint_path = os.path.join(config["utils"]["buffer"], config["cluster"]["config"])
    if is_resume_from:
        assert os.path.exists(simpoint_path)
    command = [
        # "numactl","--cpunodebind={}".format(config["cpu_bind"]),"--membind={}".format(config["mem_bind"]),
        config["NEMU"]["NEMU"],
        "{}/{}{}".format(config["utils"]["workload_folder"], config["utils"]["workload"], config["utils"]["bin_suffix"]),
        "-D", config["utils"]["buffer"],
        "-w", config["utils"]["workload"],
        "-C", config["checkpoint"]["config"],
        "-b",
        "-S", simpoint_path,
        "--cpt-interval", config["utils"]["interval"],
        "-r", config["NEMU"]["gcpt_restore"],
        "--checkpoint-format", config["utils"]["compile_format"]
    ]
    return command

def qemu_checkpoint_command(config, is_resume_from):
    simpoint_path = os.path.join(config["utils"]["buffer"], config["cluster"]["config"])
    if is_resume_from:
        assert os.path.exists(simpoint_path)
    command = [
        # "numactl","--cpunodebind={}".format(config["cpu_bind"]),"--membind={}".format(config["mem_bind"]),
        config["QEMU"]["QEMU"],
        "-bios", "{}/{}{}".format(config["utils"]["workload_folder"], config["utils"]["workload"], config["utils"]["bin_suffix"]),
        "-M", f'nemu,simpoint-path={simpoint_path},workload={config["utils"]["workload"]},cpt-interval={config["utils"]["interval"]},output-base-dir={config["utils"]["buffer"]},config-name={config["checkpoint"]["config"]},checkpoint-mode={"SimpointCheckpoint"}',
        "-nographic",
        "-m", config["QEMU"]["memory"],
        "-smp", config["QEMU"]["smp"],
        "-cpu", "rv64,v=true,vlen=128,h=false,sv39=true,sv48=false,sv57=false,sv64=false",
#        "-simpoint-path", os.path.join(config["utils"]["buffer"], config["cluster"]["config"]),
#        "-workload", config["utils"]["workload"],
#        "-cpt-interval", config["utils"]["interval"],
#        "-output-base-dir", config["utils"]["buffer"],
#        "-config-name", config["checkpoint"]["config"],
#        "-checkpoint-mode", "SimpointCheckpoint"
    ]
    return command

def profiling_func(profiling_id, config, dry_run=False):
    profiling_config = copy.deepcopy(config)

    profiling_config["profiling"]["config"] = "{}-{}".format(
        profiling_config["profiling"]["basename"], profiling_id)

    profiling_config["out-log"] = os.path.join(config["utils"]["log_folder"], "profiling-{}".format(profiling_id), config["utils"]["workload"], "profiling.out.log")
    profiling_config["err-log"] = os.path.join(config["utils"]["log_folder"], "profiling-{}".format(profiling_id), config["utils"]["workload"], "profiling.err.log")
    profiling_config["execute_mode"] = "profiling"

    if not dry_run:
        if profiling_config["emu"] == "NEMU":
            profiling_config["command"] = nemu_profiling_command(profiling_config)
        else:
            profiling_config["command"] = qemu_profiling_command(profiling_config)
    else:
        bak_out_log_path = os.path.join(config["utils"]["log_folder"], "profiling-{}".format(profiling_id), config["utils"]["workload"], "old_profiling.out.log")
        bak_err_log_path = os.path.join(config["utils"]["log_folder"], "profiling-{}".format(profiling_id), config["utils"]["workload"], "old_profiling.err.log")
        profiling_config["backup_commands"] = [['cp', profiling_config["out-log"], bak_out_log_path], ['cp', profiling_config["err-log"], bak_err_log_path]]
        profiling_config["command"] = ["echo", '"dry_run_profiling_command"']

    print(profiling_config["command"])

    global profiling_roots
    profiling_roots = CheckpointTree(profiling_config)

    return profiling_config["profiling"]["config"]


def cluster_func(profiling_id, cluster_id, config, is_resume_from=False, dry_run=False):
    cluster_config = copy.deepcopy(config)

    cluster_config["profiling"]["config"] = "{}-{}".format(
        cluster_config["profiling"]["basename"], profiling_id)

    cluster_config["cluster"]["config"] = "{}-{}-{}".format(
        cluster_config["cluster"]["basename"], profiling_id, cluster_id)

    cluster_config["execute_mode"] = "cluster"

    cluster_config["out-log"] = os.path.join(config["utils"]["log_folder"], "cluster-{}-{}".format(profiling_id, cluster_id), config["utils"]["workload"],"cluster.out.log")
    cluster_config["err-log"] = os.path.join(config["utils"]["log_folder"], "cluster-{}-{}".format(profiling_id, cluster_id), config["utils"]["workload"],"cluster.err.log")

    if not dry_run:
        cluster_config["command"] = cluster_command(cluster_config, is_resume_from=is_resume_from)
    else:
        cluster_config["command"] = ['echo', 'dry_run_cluster_command']

    child = CheckpointTree(cluster_config)
    global profiling_roots
    profiling_roots.add_child(child)

    return cluster_config["cluster"]["config"]


def checkpoint_func(profiling_id, cluster_id, checkpoint_id, config, is_resume_from=False):
    checkpoint_config = copy.deepcopy(config)

    checkpoint_config["profiling"]["config"] = "{}-{}".format(
        checkpoint_config["profiling"]["basename"], profiling_id)

    checkpoint_config["cluster"]["config"] = "{}-{}-{}".format(
        checkpoint_config["cluster"]["basename"], profiling_id, cluster_id)

    checkpoint_config["checkpoint"]["config"] = "{}-{}-{}-{}".format(
        checkpoint_config["checkpoint"]["basename"], profiling_id, cluster_id,
        checkpoint_id)

    checkpoint_config["execute_mode"] = "checkpoint"

    checkpoint_config["out-log"] = os.path.join(config["utils"]["log_folder"], "checkpoint-{}-{}-{}".format(profiling_id, cluster_id, checkpoint_id), config["utils"]["workload"], "checkpoint.out.log")
    checkpoint_config["err-log"] = os.path.join(config["utils"]["log_folder"], "checkpoint-{}-{}-{}".format(profiling_id, cluster_id, checkpoint_id), config["utils"]["workload"], "checkpoint.err.log")

    if checkpoint_config["emu"] == "NEMU":
        checkpoint_config["command"] = nemu_checkpoint_command(
            checkpoint_config, is_resume_from=is_resume_from)
    else:
        checkpoint_config["command"] = qemu_checkpoint_command(
            checkpoint_config, is_resume_from=is_resume_from)

    child = CheckpointTree(checkpoint_config)
    global profiling_roots
    profiling_roots.children[cluster_id].add_child(child)

    return checkpoint_config["checkpoint"]["config"]


def generate_command(workload_folder,
                     workload,
                     buffer,
                     bin_suffix,
                     emu,
                     log_folder,
                     cpu_bind,
                     mem_bind,
                     copies,
                     resume_after=None,
                     profiling_func=profiling_func,
                     cluster_func=cluster_func,
                     checkpoint_func=checkpoint_func,
                     config=default_config):

    config["utils"]["workload_folder"] = workload_folder
    config["utils"]["workload"] = workload
    config["utils"]["buffer"] = buffer
    config["utils"]["bin_suffix"] = bin_suffix
    config["emu"] = emu
    if config["emu"] == "QEMU":
        config["QEMU"]["smp"] = copies
    config["utils"]["log_folder"] = log_folder
    config["cpu_bind"] = cpu_bind
    config["mem_bind"] = mem_bind

    global profiling_roots
    if not os.path.exists("{}/{}{}".format(config["utils"]["workload_folder"],
                                           config["utils"]["workload"],
                                           config["utils"]["bin_suffix"])):
        print("Workload binary not exists: {}", config["utils"]["workload"])
        profiling_roots = None
        return profiling_roots


    if resume_after is None or len(resume_after) == 0:
        p_func = functools.partial(profiling_func, config=config)
        cl_func = functools.partial(cluster_func, config=config)
        c_func = functools.partial(checkpoint_func, config=config)
    elif resume_after == "profiling":
        p_func = functools.partial(profiling_func, config=config, dry_run=True)
        cl_func = functools.partial(cluster_func, config=config, is_resume_from=True)
        c_func = functools.partial(checkpoint_func, config=config)
    elif resume_after == "cluster":
        p_func = functools.partial(profiling_func, config=config, dry_run=True)
        cl_func = functools.partial(cluster_func, config=config, dry_run=True)
        c_func = functools.partial(checkpoint_func, config=config, is_resume_from=True)

    print(list(itertools.starmap(p_func, profiling_configs)))
    print(list(itertools.starmap(cl_func, cluster_configs)))
    print(list(itertools.starmap(c_func, checkpoint_configs)))

    return profiling_roots

def set_startid_times(start_id, times):
    if start_id is not None:
        default_config["profiling"]["id"] = start_id.split(",")[0]
        default_config["cluster"]["id"] = start_id.split(",")[1]
        default_config["checkpoint"]["id"] = start_id.split(",")[2]

    if times is not None:
        default_config["profiling"]["times"] = times.split(",")[0]
        default_config["cluster"]["times"] = times.split(",")[1]
        default_config["checkpoint"]["times"] = times.split(",")[2]


#generate_command("gcc_test", "astar_biglakes", "archive", "", "NEMU", "log_folder")
#print_tree(profiling_roots[0])
#level_first_exec(profiling_roots[0])
