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
                     "qemu-riscv64-system"),
        "memory":
        "8G",
        "smp":
        "1",
        "profiling_plugin":
        os.path.join(os.environ.get("QEMU_HOME"), "build", "contrib", "plugin",
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

        with open(out_file, "w") as out, open(err_file, "w") as err:
            command = self.value["command"]
            print(self.value)
            print(self.value["utils"]["workload"], self.value["execute_mode"])
            res = subprocess.run(command, stdout=out, stderr=err)
            print(command + "Execute finish")
            return res

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
        "-bios", "{}/{}{}".format(config["utils"]["workload_folder"], config["utils"]["workload"], config["utils"]["bin_suffix"]),
        "-M", "nemu",
        "-nographic",
        "-m", config["QEMU"]["memory"],
        "-smp", config["QEMU"]["smp"],
        "-cpu", "rv64,v=true,vlen=128",
        "-plugin", "{},workload={},intervals={},target={}".format(
            config["QEMU"]["profiling_plugin"],
            config["utils"]["workload"],
            config["utils"]["interval"],
            os.path.join(config["utils"]["buffer"], config["profiling"]["config"], config["utils"]["workload"]))
    ]
    return command

def cluster_command(config):
    seedkm = random.randint(100000, 999999)
    seedproj = random.randint(100000, 999999)
    mkdir(os.path.split(os.path.join(config["utils"]["buffer"], config["cluster"]["config"], config["utils"]["workload"], "simpoints0"))[0])
    command = [
        "numactl","--cpunodebind={}".format(config["cpu_bind"]),"--membind={}".format(config["mem_bind"]),
        config["NEMU"]["simpoint"],
        "-loadFVFile", os.path.join(config["utils"]["buffer"], config["profiling"]["config"], config["utils"]["workload"], "simpoint_bbv.gz"),
        "-saveSimpoints", os.path.join(config["utils"]["buffer"], config["cluster"]["config"], config["utils"]["workload"], "simpoints0"),
        "-saveSimpointWeights", os.path.join(config["utils"]["buffer"], config["cluster"]["config"], config["utils"]["workload"], "weights0"),
        "-inputVectorsGzipped",
        "-maxK", "30",
        "-numInitSeeds", "2",
        "-iters", "1000",
        "-seedkm", f"{seedkm}", "-seedproj", f"{seedproj}"
    ]
    return command

def nemu_checkpoint_command(config):
    command = [
        "numactl","--cpunodebind={}".format(config["cpu_bind"]),"--membind={}".format(config["mem_bind"]),
        config["NEMU"]["NEMU"],
        "{}/{}{}".format(config["utils"]["workload_folder"], config["utils"]["workload"], config["utils"]["bin_suffix"]),
        "-D", config["utils"]["buffer"],
        "-w", config["utils"]["workload"],
        "-C", config["checkpoint"]["config"],
        "-b",
        "-S", os.path.join(config["utils"]["buffer"], config["cluster"]["config"]),
        "--cpt-interval", config["utils"]["interval"],
        "-r", config["NEMU"]["gcpt_restore"],
        "--checkpoint-format", config["utils"]["compile_format"]
    ]
    return command

def qemu_checkpoint_command(config):
    command = [
        "numactl","--cpunodebind={}".format(config["cpu_bind"]),"--membind={}".format(config["mem_bind"]),
        config["QEMU"]["QEMU"],
        "-bios", "{}/{}{}".format(config["utils"]["workload_folder"], config["utils"]["workload"], config["utils"]["bin_suffix"]),
        "-M", "nemu",
        "-nographic",
        "-m", config["QEMU"]["memory"],
        "-smp", config["QEMU"]["smp"],
        "-cpu", "rv64,v=true,vlen=128",
        "-simpoint-path", os.path.join(config["utils"]["buffer"], config["cluster"]["config"]),
        "-workload", config["utils"]["workload"],
        "-cpt-interval", config["utils"]["interval"],
        "-output-base-dir", config["utils"]["buffer"],
        "-config-name", config["checkpoint"]["config"],
        "-checkpoint-mode", "SimpointCheckpoint"
    ]
    return command

def profiling_func(profiling_id, config):
    profiling_config = copy.deepcopy(config)

    profiling_config["profiling"]["config"] = "{}-{}".format(
        profiling_config["profiling"]["basename"], profiling_id)

    profiling_config["out-log"] = os.path.join(config["utils"]["log_folder"], "profiling-{}".format(profiling_id), config["utils"]["workload"], "profiling.out.log")
    profiling_config["err-log"] = os.path.join(config["utils"]["log_folder"], "profiling-{}".format(profiling_id), config["utils"]["workload"], "profiling.err.log")
    profiling_config["execute_mode"] = "profiling"

    if profiling_config["emu"] == "NEMU":
        profiling_config["command"] = nemu_profiling_command(profiling_config)
    else:
        profiling_config["command"] = qemu_profiling_command(profiling_config)

    global profiling_roots
    profiling_roots = CheckpointTree(profiling_config)

    return profiling_config["profiling"]["config"]


def cluster_func(profiling_id, cluster_id, config):
    cluster_config = copy.deepcopy(config)

    cluster_config["profiling"]["config"] = "{}-{}".format(
        cluster_config["profiling"]["basename"], profiling_id)

    cluster_config["cluster"]["config"] = "{}-{}-{}".format(
        cluster_config["cluster"]["basename"], profiling_id, cluster_id)

    cluster_config["execute_mode"] = "cluster"

    cluster_config["out-log"] = os.path.join(config["utils"]["log_folder"], "cluster-{}-{}".format(profiling_id, cluster_id), config["utils"]["workload"],"cluster.out.log")
    cluster_config["err-log"] = os.path.join(config["utils"]["log_folder"], "cluster-{}-{}".format(profiling_id, cluster_id), config["utils"]["workload"],"cluster.err.log")

    cluster_config["command"] = cluster_command(cluster_config)

    child = CheckpointTree(cluster_config)
    global profiling_roots
    profiling_roots.add_child(child)

    return cluster_config["cluster"]["config"]


def checkpoint_func(profiling_id, cluster_id, checkpoint_id, config):
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
            checkpoint_config)
    else:
        checkpoint_config["command"] = qemu_checkpoint_command(
            checkpoint_config)

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
                     profiling_func=profiling_func,
                     cluster_func=cluster_func,
                     checkpoint_func=checkpoint_func,
                     config=default_config):

    config["utils"]["workload_folder"] = workload_folder
    config["utils"]["workload"] = workload
    config["utils"]["buffer"] = buffer
    config["utils"]["bin_suffix"] = bin_suffix
    config["emu"] = emu
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

    p_func = functools.partial(profiling_func, config=config)
    cl_func = functools.partial(cluster_func, config=config)
    c_func = functools.partial(checkpoint_func, config=config)

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
