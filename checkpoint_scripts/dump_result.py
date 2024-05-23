import os
import re
import json
from pathlib import Path

app_list = [
    "bwaves", "gamess_cytosine", "gamess_gradient", "gamess_triazolium", "milc",
    "zeusmp", "gromacs", "cactusADM", "leslie3d", "namd", "dealII",
    "soplex_pds-50", "soplex_ref", "povray", "calculix", "GemsFDTD", "tonto",
    "lbm", "wrf", "sphinx3"
]

def profiling_instrs(profiling_log, spec_app):
    regex = r".*total guest instructions = (.*)\x1b.*"
    with open(os.path.join(profiling_log, "{}-out.log".format(spec_app)),
              "r") as f:
        return 0
        for i in f.readlines():
            if "total guest instructions" in i:
                match = re.findall(regex, i)
                match = match[0].replace(',', '')
                return match
        else:
            return 0


def cluster_weight(cluster_path, spec_app):
    points = {}
    weights = {}

    weights_path = "{}/{}/weights0".format(cluster_path, spec_app)
    simpoints_path = "{}/{}/simpoints0".format(cluster_path, spec_app)

    with open(weights_path, "r") as f:
        for line in f.readlines():
            a, b = line.split()
            weights.update({"{}".format(b): "{}".format(a)})

    with open(simpoints_path, "r") as f:
        for line in f.readlines():
            a, b = line.split()
            points.update({a: weights.get(b)})

    return points



def per_checkpoint_generate_json(
    profiling_log, cluster_path, app_list, target_path
):
    result = {}
    for spec in app_list:
        result.update(
            {
                spec:
                    {
                        "insts": profiling_instrs(profiling_log, spec),
                        'points': cluster_weight(cluster_path, spec)
                    }
            }
        )
    with open(os.path.join(target_path), "w") as f:
        f.write(json.dumps(result))

def per_checkpoint_generate_worklist(cpt_path, target_path):
    cpt_path = cpt_path + "/"
    checkpoints = []
    for item in os.scandir(cpt_path):
        if item.is_dir():
            checkpoints.append(item.path)

    checkpoint_dirs = []
    for item in checkpoints:
        for entry in os.scandir(item):
            checkpoint_dirs.append(entry.path)

    with open(target_path, "w") as f:
        for i in checkpoint_dirs:
            path = i.replace(cpt_path, "")
            name = path.replace('/', "_", 1)
            print("{} {} 0 0 20 20".format(name, path), file=f)

result = {
    "cl_res":
        os.path.join(
            "/path/to/cluster-0-0"
        ),
    "profiling_log":
        os.path.join(
            "/path/to/logs/profiling-0"
        ),
    "checkpoint_path":
        os.path.join(
            "/path/to/checkpoint-0-0-0"
        ),
    "json_path":
        os.path.join(
            "/path/to/checkpoint-0-0-0/cluster-0-0.json"
        ),
    "list_path":
        os.path.join(
            "/path/to/checkpoint-0-0-0/checkpoint.lst"
        )
}
#
#def generate_result(buffer, log_folder):
#    buffer_path = Path(buffer)
#    log_path = Path(log_folder)
#    profiling_logs = list(log_path.glob("profiling-*"))
#

per_checkpoint_generate_json(result["profiling_log"], result["cl_res"], app_list, result["json_path"])
per_checkpoint_generate_worklist(result["checkpoint_path"], result["list_path"])
