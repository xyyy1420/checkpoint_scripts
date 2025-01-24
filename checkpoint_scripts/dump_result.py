import os
import re
import json
from pathlib import Path
from itertools import product

app_list = [
    "bwaves", "gamess_cytosine", "gamess_gradient", "gamess_triazolium",
    "milc", "zeusmp", "gromacs", "cactusADM", "leslie3d", "namd", "dealII",
    "soplex_pds-50", "soplex_ref", "povray", "calculix", "GemsFDTD", "tonto",
    "lbm", "wrf", "sphinx3"
]

spec_2017_list = [
    "bwaves_1", "bwaves_2", "bwaves_3", "bwaves_4", "cactuBSSN", "namd",
    "parest", "povray", "lbm", "wrf", "blender", "cam4", "imagick", "nab",
    "fotonik3d", "roms", "perlbench_diff", "perlbench_spam", "perlbench_split",
    "gcc_pp_O2", "gcc_pp_O3", "gcc_ref32_O3", "gcc_ref32_O5", "gcc_small_O3",
    "mcf", "omnetpp", "xalancbmk", "x264_pass1", "x264_pass2", "x264_seek",
    "deepsjeng", "leela", "exchange2", "xz_cld", "xz_combined", "xz_cpu2006"
]

spec2017_int_list = [
    "perlbench_diff", "perlbench_spam", "perlbench_split", "gcc_pp_O2",
    "gcc_pp_O3", "gcc_ref32_O3", "gcc_ref32_O5", "gcc_small_O3", "mcf",
    "omnetpp", "xalancbmk", "x264_pass1", "x264_pass2", "x264_seek",
    "deepsjeng", "leela", "exchange2", "xz_cld", "xz_combined", "xz_cpu2006"
]

spec2017_fp_list = list(set(spec_2017_list) - set(spec2017_int_list))


def profiling_instrs(profiling_log, spec_app, using_new_script=False):
    regex = r".*total guest instructions = (.*)\x1b.*"
    new_path = os.path.join(profiling_log, spec_app, "profiling.out.log")
    old_path = os.path.join(profiling_log, "{}-out.log".format(spec_app))

    if using_new_script:
        path = new_path
        assert os.path.exists(new_path)
    elif os.path.exists(old_path):
        path = old_path
    elif os.path.exists(new_path):
        path = new_path
    else:
        print("Either {} or {} does not exist".format(old_path, new_path))
        raise

    with open(path, "r", encoding="utf-8") as f:
        for i in f.readlines():
            if "total guest instructions" in i:
                match = re.findall(regex, i)
                match = match[0].replace(',', '')
                return match
        return 0


def cluster_weight(cluster_path, spec_app):
    points = {}
    weights = {}

    weights_path = f"{cluster_path}/{spec_app}/weights0"
    simpoints_path = f"{cluster_path}/{spec_app}/simpoints0"

    with open(weights_path, "r") as f:
        for line in f.readlines():
            a, b = line.split()
            weights.update({"{}".format(b): "{}".format(a)})

    with open(simpoints_path, "r") as f:
        for line in f.readlines():
            a, b = line.split()
            if float(weights[b]) > 1e-4:  # ignore small simpoints
                points.update({a: weights.get(b)})

    return points


def per_checkpoint_generate_json(profiling_log, cluster_path, app_list,
                                 target_path):
    result = {}
    for spec in app_list:
        result.update({
            spec: {
                "insts": profiling_instrs(profiling_log, spec),
                'points': cluster_weight(cluster_path, spec)
            }
        })
    with open(os.path.join(target_path), "w") as f:
        f.write(json.dumps(result, indent=4))
    return result


def per_checkpoint_generate_worklist(cpt_path, target_path, json_result):
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
            workload, point = path.split("/")
            if point not in json_result[workload]["points"]:
                print(f"point {point} not in {workload} because of small weight or not in simpoint list")
                continue
            name = path.replace('/', "_", 1)
            print("{} {} 0 0 20 20".format(name, path), file=f)


def generate_result_list(base_path, times, ids):
    result_list = []

    for i, j, k in product(range(ids[0], times[0]), range(ids[1], times[1]),
                           range(ids[2], times[2])):
        cluster = f"cluster-{i}-{j}"
        profiling = f"profiling-{k}"
        checkpoint = f"checkpoint-{i}-{j}-{k}"
        result_list.append({
            "cl_res":
            os.path.join(base_path, cluster),
            "profiling_log":
            os.path.join(base_path, "logs", profiling),
            "checkpoint_path":
            os.path.join(base_path, checkpoint),
            "json_path":
            os.path.join(base_path, checkpoint, f"{cluster}.json"),
            "list_path":
            os.path.join(base_path, checkpoint, "checkpoint.lst"),
        })

    print(result_list)
    return result_list


#base_path="/nfs/home/jiaxiaoyu/profiling_env/auto_generate_env/archive/gcc12.2.0_rv64gc_base_nospecial_NEMU_archgroup_2024-05-31-19-01"
#base_path="/nfs/home/share/jiaxiaoyu/simpoint_checkpoint_archive/spec06_rv64gcbv_20m_gcc14.1.0_libquantum_hmmer_h264_without_segment"

#result = {
#    "cl_res":
#        os.path.join(
#            base_path, "cluster-0-0"
#        ),
#    "profiling_log":
#        os.path.join(
#            base_path, "logs","profiling-0"
#        ),
#    "checkpoint_path":
#        os.path.join(
#            base_path, "checkpoint-0-0-0"
#        ),
#    "json_path":
#        os.path.join(
#            base_path, "checkpoint-0-0-0","cluster-0-0.json"
#        ),
#    "list_path":
#        os.path.join(
#            base_path, "checkpoint-0-0-0","checkpoint.lst"
#        )
#}


def dump_result(base_path, spec_app_list, times, ids):
    result_list = generate_result_list(base_path, times, ids)

    for result in result_list:
        json_result = per_checkpoint_generate_json(result["profiling_log"], result["cl_res"],
                                     spec_app_list, result["json_path"])
        per_checkpoint_generate_worklist(result["checkpoint_path"],
                                         result["list_path"], json_result)


#/nfs/home/share/jiaxiaoyu/simpoint_checkpoint_archive/spec06_rv64gcbv_20m_gcc14.1.0_libquantum_hmmer_h264_without_segment/checkpoint-0-0-0/h264ref_sss
spec_list=["hmmer_nph3", "hmmer_retro", "libquantum", "h264ref_foreman.baseline", "h264ref_foreman.main", "h264ref_sss"]
#base_path = "/nfs/home/share/jiaxiaoyu/simpoint_checkpoint_archive/spec17-rv64gcb-O3-20m-gcc12.2.0-mix-with-special_wrf"
base_path = "/nfs/home/share/jiaxiaoyu/simpoint_checkpoint_archive/spec06_rv64gcbv_20m_gcc14.1.0_libquantum_hmmer_h264_without_segment"
times = [1, 1, 1]
ids = [0, 0, 0]

dump_result(base_path, spec_list, times, ids)