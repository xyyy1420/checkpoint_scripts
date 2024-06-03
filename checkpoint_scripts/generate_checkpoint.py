import os
import pathlib
from datetime import datetime
import argparse
import shutil
import subprocess
import concurrent.futures
from spec_gen import prepare_rootfs
from spec_gen import get_cpu2017_info
from spec_gen import get_cpu2006_info
from generate_bbl import build_spec_bbl
from generate_bbl import build_bbl_as_gcpt_payload
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


parser = argparse.ArgumentParser(
    description="Auto profiling and checkpointing")


def entrys(path):
    entrys_list = []
    with os.scandir(path) as el:
        for entry in el:
            entrys_list.append(entry)
    return entrys_list


def generate_folders():
    args = parser.parse_args()

    # set archive id from arg
    if args.archive_id is None:
        default_config["archive_id"] = generate_buffer_folder_name()
    else:
        default_config["archive_id"] = args.archive_id

    default_config["buffer"] = os.path.join(def_config()["archive_folder"],
                                            def_config()["archive_id"])
    if args.archive_id is None:
        create_folders()

    assert (os.path.exists(def_config()["buffer"]))

    if args.message is not None:
        generate_archive_info(args.message)


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


# copy from https://github.com/OpenXiangShan/riscv-rootfs/blob/da983ec95858dfd6f30e9feadd534b79db37e618/rootfsimg/spec_gen.py#L9
def get_default_spec_list():
    return {
        "astar_biglakes": {
            "base":
            "astar",
            "args": ["BigLakes2048.cfg"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/astar/BigLakes2048.bin",
                "${CPU2006_RUN_DIR}/astar/BigLakes2048.cfg"
            ],
        },
        "astar_rivers": {
            "base":
            "astar",
            "args": ["rivers.cfg"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/astar/rivers.bin",
                "${CPU2006_RUN_DIR}/astar/rivers.cfg"
            ],
        },
        "bwaves": {
            "base": "bwaves",
            "args": [],
            "ref_files": ["${CPU2006_RUN_DIR}/bwaves/bwaves.in"],
        },
        "bzip2_chicken": {
            "base": "bzip2",
            "args": ["chicken.jpg", "30"],
            "ref_files": ["${CPU2006_RUN_DIR}/bzip2/chicken.jpg"],
        },
        "bzip2_combined": {
            "base": "bzip2",
            "args": ["input.combined", "200"],
            "ref_files": ["${CPU2006_RUN_DIR}/bzip2/input.combined"],
        },
        "bzip2_html": {
            "base": "bzip2",
            "args": ["text.html", "280"],
            "ref_files": ["${CPU2006_RUN_DIR}/bzip2/text.html"],
        },
        "bzip2_liberty": {
            "base": "bzip2",
            "args": ["liberty.jpg", "30"],
            "ref_files": ["${CPU2006_RUN_DIR}/bzip2/liberty.jpg"],
        },
        "bzip2_program": {
            "base": "bzip2",
            "args": ["input.program", "280"],
            "ref_files": ["${CPU2006_RUN_DIR}/bzip2/input.program"],
        },
        "bzip2_source": {
            "base": "bzip2",
            "args": ["input.source", "280"],
            "ref_files": ["${CPU2006_RUN_DIR}/bzip2/input.source"],
        },
        "cactusADM": {
            "base": "cactusADM",
            "args": ["benchADM.par"],
            "ref_files": ["${CPU2006_RUN_DIR}/cactusADM/benchADM.par"],
        },
        "calculix": {
            "base":
            "calculix",
            "args": ["-i", "hyperviscoplastic"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/calculix/hyperviscoplastic.dat",
                "${CPU2006_RUN_DIR}/calculix/hyperviscoplastic.frd",
                "${CPU2006_RUN_DIR}/calculix/hyperviscoplastic.inp",
                "${CPU2006_RUN_DIR}/calculix/hyperviscoplastic.sta"
            ],
        },
        "dealII": {
            "base": "dealII",
            "args": ["23"],
            "ref_files": ["${CPU2006_RUN_DIR}/dealII/DummyData"],
        },
        "gamess_cytosine": {
            "base":
            "gamess",
            "args": ["<", "cytosine.2.config"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/gamess/cytosine.2.config",
                "${CPU2006_RUN_DIR}/gamess/cytosine.2.inp"
            ],
        },
        "gamess_gradient": {
            "base":
            "gamess",
            "args": ["<", "h2ocu2+.gradient.config"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/gamess/h2ocu2+.gradient.config",
                "${CPU2006_RUN_DIR}/gamess/h2ocu2+.gradient.inp"
            ],
        },
        "gamess_triazolium": {
            "base":
            "gamess",
            "args": ["<", "triazolium.config"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/gamess/triazolium.config",
                "${CPU2006_RUN_DIR}/gamess/triazolium.inp"
            ],
        },
        "gcc_166": {
            "base": "gcc",
            "args": ["166.i", "-o", "166.s"],
            "ref_files": ["${CPU2006_RUN_DIR}/gcc/166.i"],
        },
        "gcc_200": {
            "base": "gcc",
            "args": ["200.i", "-o", "200.s"],
            "ref_files": ["${CPU2006_RUN_DIR}/gcc/200.i"],
        },
        "gcc_cpdecl": {
            "base": "gcc",
            "args": ["cp-decl.i", "-o", "cp-decl.s"],
            "ref_files": ["${CPU2006_RUN_DIR}/gcc/cp-decl.i"],
        },
        "gcc_expr2": {
            "base": "gcc",
            "args": ["expr2.i", "-o", "expr2.s"],
            "ref_files": ["${CPU2006_RUN_DIR}/gcc/expr2.i"],
        },
        "gcc_expr": {
            "base": "gcc",
            "args": ["expr.i", "-o", "expr.s"],
            "ref_files": ["${CPU2006_RUN_DIR}/gcc/expr.i"],
        },
        "gcc_g23": {
            "base": "gcc",
            "args": ["g23.i", "-o", "g23.s"],
            "ref_files": ["${CPU2006_RUN_DIR}/gcc/g23.i"],
        },
        "gcc_s04": {
            "base": "gcc",
            "args": ["s04.i", "-o", "s04.s"],
            "ref_files": ["${CPU2006_RUN_DIR}/gcc/s04.i"],
        },
        "gcc_scilab": {
            "base": "gcc",
            "args": ["scilab.i", "-o", "scilab.s"],
            "ref_files": ["${CPU2006_RUN_DIR}/gcc/scilab.i"],
        },
        "gcc_typeck": {
            "base": "gcc",
            "args": ["c-typeck.i", "-o", "c-typeck.s"],
            "ref_files": ["${CPU2006_RUN_DIR}/gcc/c-typeck.i"],
        },
        "GemsFDTD": {
            "base":
            "GemsFDTD",
            "args": [],
            "ref_files": [
                "${CPU2006_RUN_DIR}/GemsFDTD/ref.in",
                "${CPU2006_RUN_DIR}/GemsFDTD/sphere.pec",
                "${CPU2006_RUN_DIR}/GemsFDTD/yee.dat"
            ],
        },
        "gobmk_13x13": {
            "base":
            "gobmk",
            "args": ["--quiet", "--mode", "gtp", "<", "13x13.tst"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/gobmk/13x13.tst",
                "$dir games {CPU2006_RUN_DIR}/gobmk/games",
                "$dir golois {CPU2006_RUN_DIR}/gobmk/golois"
            ],
        },
        "gobmk_nngs": {
            "base":
            "gobmk",
            "args": ["--quiet", "--mode", "gtp", "<", "nngs.tst"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/gobmk/nngs.tst",
                "$dir games {CPU2006_RUN_DIR}/gobmk/games",
                "$dir golois {CPU2006_RUN_DIR}/gobmk/golois"
            ],
        },
        "gobmk_score2": {
            "base":
            "gobmk",
            "args": ["--quiet", "--mode", "gtp", "<", "score2.tst"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/gobmk/score2.tst",
                "$dir games {CPU2006_RUN_DIR}/gobmk/games",
                "$dir golois {CPU2006_RUN_DIR}/gobmk/golois"
            ],
        },
        "gobmk_trevorc": {
            "base":
            "gobmk",
            "args": ["--quiet", "--mode", "gtp", "<", "trevorc.tst"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/gobmk/trevorc.tst",
                "$dir games {CPU2006_RUN_DIR}/gobmk/games",
                "$dir golois {CPU2006_RUN_DIR}/gobmk/golois"
            ],
        },
        "gobmk_trevord": {
            "base":
            "gobmk",
            "args": ["--quiet", "--mode", "gtp", "<", "trevord.tst"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/gobmk/trevord.tst",
                "$dir games {CPU2006_RUN_DIR}/gobmk/games",
                "$dir golois {CPU2006_RUN_DIR}/gobmk/golois"
            ],
        },
        "gromacs": {
            "base": "gromacs",
            "args": ["-silent", "-deffnm", "gromacs.tpr", "-nice", "0"],
            "ref_files": ["${CPU2006_RUN_DIR}/gromacs/gromacs.tpr"],
        },
        "h264ref_foreman.baseline": {
            "base":
            "h264ref",
            "args": ["-d", "foreman_ref_encoder_baseline.cfg"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/h264ref/foreman_ref_encoder_baseline.cfg",
                "${CPU2006_RUN_DIR}/h264ref/foreman_qcif.yuv"
            ],
        },
        "h264ref_foreman.main": {
            "base":
            "h264ref",
            "args": ["-d", "foreman_ref_encoder_main.cfg"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/h264ref/foreman_ref_encoder_main.cfg",
                "${CPU2006_RUN_DIR}/h264ref/foreman_qcif.yuv"
            ],
        },
        "h264ref_sss": {
            "base":
            "h264ref",
            "args": ["-d", "sss_encoder_main.cfg"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/h264ref/sss_encoder_main.cfg",
                "${CPU2006_RUN_DIR}/h264ref/sss.yuv"
            ],
        },
        "hmmer_nph3": {
            "base":
            "hmmer",
            "args": ["nph3.hmm", "swiss41"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/hmmer/nph3.hmm",
                "${CPU2006_RUN_DIR}/hmmer/swiss41"
            ],
        },
        "hmmer_retro": {
            "base":
            "hmmer",
            "args": [
                "--fixed", "0", "--mean", "500", "--num", "500000", "--sd",
                "350", "--seed", "0", "retro.hmm"
            ],
            "ref_files": ["${CPU2006_RUN_DIR}/hmmer/retro.hmm"],
        },
        "lbm": {
            "base":
            "lbm",
            "args": ["3000", "reference.dat", "0", "0", "100_100_130_ldc.of"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/lbm/100_100_130_ldc.of",
                "${CPU2006_RUN_DIR}/lbm/lbm.in"
            ],
        },
        "leslie3d": {
            "base": "leslie3d",
            "args": ["<", "leslie3d.in"],
            "ref_files": ["${CPU2006_RUN_DIR}/leslie3d/leslie3d.in"],
        },
        "libquantum": {
            "base": "libquantum",
            "args": ["1397", "8"],
            "ref_files": [],
        },
        "mcf": {
            "base": "mcf",
            "args": ["inp.in"],
            "ref_files": ["${CPU2006_RUN_DIR}/mcf/inp.in"],
        },
        "milc": {
            "base": "milc",
            "args": ["<", "su3imp.in"],
            "ref_files": ["${CPU2006_RUN_DIR}/milc/su3imp.in"],
        },
        "namd": {
            "base":
            "namd",
            "args": [
                "--input", "namd.input", "--iterations", "38", "--output",
                "namd.out"
            ],
            "ref_files": ["${CPU2006_RUN_DIR}/namd/namd.input"],
        },
        "omnetpp": {
            "base": "omnetpp",
            "args": ["omnetpp.ini"],
            "ref_files": ["${CPU2006_RUN_DIR}/omnetpp/omnetpp.ini"],
        },
        "perlbench_checkspam": {
            "base":
            "perlbench",
            "args": [
                "-I./lib", "checkspam.pl", "2500", "5", "25", "11", "150", "1",
                "1", "1", "1"
            ],
            "ref_files": [
                "${CPU2006_RUN_DIR}/perlbench/cpu2006_mhonarc.rc",
                "${CPU2006_RUN_DIR}/perlbench/checkspam.pl",
                "${CPU2006_RUN_DIR}/perlbench/checkspam.in",
                "$dir lib {CPU2006_RUN_DIR}/perlbench/lib",
                "$dir rules {CPU2006_RUN_DIR}/perlbench/rules"
            ],
        },
        "perlbench_diffmail": {
            "base":
            "perlbench",
            "args":
            ["-I./lib", "diffmail.pl", "4", "800", "10", "17", "19", "300"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/perlbench/cpu2006_mhonarc.rc",
                "${CPU2006_RUN_DIR}/perlbench/diffmail.pl",
                "${CPU2006_RUN_DIR}/perlbench/diffmail.in",
                "$dir lib {CPU2006_RUN_DIR}/perlbench/lib",
                "$dir rules {CPU2006_RUN_DIR}/perlbench/rules"
            ],
        },
        "perlbench_splitmail": {
            "base":
            "perlbench",
            "args":
            ["-I./lib", "splitmail.pl", "1600", "12", "26", "16", "4500"],
            "ref_files": [
                "${CPU2006_RUN_DIR}/perlbench/cpu2006_mhonarc.rc",
                "${CPU2006_RUN_DIR}/perlbench/splitmail.pl",
                "${CPU2006_RUN_DIR}/perlbench/splitmail.in",
                "$dir lib {CPU2006_RUN_DIR}/perlbench/lib",
                "$dir rules {CPU2006_RUN_DIR}/perlbench/rules"
            ],
        },
        "povray": {
            "base": "povray",
            "args": ["SPEC-benchmark-ref.ini"],
            "ref_files": ["$dir . {CPU2006_RUN_DIR}/povray"],
        },
        "sjeng": {
            "base": "sjeng",
            "args": ["ref.txt"],
            "ref_files": ["${CPU2006_RUN_DIR}/sjeng/ref.txt"],
        },
        "soplex_pds-50": {
            "base": "soplex",
            "args": ["-s1", "-e", "-m45000", "pds-50.mps"],
            "ref_files": ["${CPU2006_RUN_DIR}/soplex/pds-50.mps"],
        },
        "soplex_ref": {
            "base": "soplex",
            "args": ["-m3500", "ref.mps"],
            "ref_files": ["${CPU2006_RUN_DIR}/soplex/ref.mps"],
        },
        "sphinx3": {
            "base": "sphinx3",
            "args": ["ctlfile", ".", "args.an4"],
            "ref_files": ["$dir . {CPU2006_RUN_DIR}/sphinx3"],
        },
        "tonto": {
            "base": "tonto",
            "args": [],
            "ref_files": ["${CPU2006_RUN_DIR}/tonto/stdin"],
        },
        "wrf": {
            "base": "wrf",
            "args": [],
            "ref_files": ["$dir . {CPU2006_RUN_DIR}/wrf"],
        },
        "xalancbmk": {
            "base": "xalancbmk",
            "args": ["-v", "t5.xml", "xalanc.xsl"],
            "ref_files": ["$dir . {CPU2006_RUN_DIR}/xalancbmk"],
        },
        "zeusmp": {
            "base": "zeusmp",
            "args": [],
            "ref_files": ["${CPU2006_RUN_DIR}/zeusmp/zmp_inp"],
        }
    }

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
#    for spec in spec_base_app_list:
#        dst_file_path = copy_to_dst(spec, elfs,
#                                    prepare_config()["elf_folder"])
#        dump_assembly(
#            dst_file_path,
#            os.path.join(build_config()["assembly_folder"], spec + ".txt"))


if __name__ == "__main__":
    parser.add_argument(
        '--archive-id',
        help=
        "Archive id (default: use {gcc_version}_{riscv_ext}_{base_or_fixed}_{special_flag}_{emulator}_{group}_{time})"
    )
    parser.add_argument('--message', help="Record info to the archive")
    parser.add_argument(
        '--spec-app-list',
        help="List of selected spec programs path (default: all spec program)")
    parser.add_argument(
        '--spec-apps',
        help=
        'List of selected spec programs (default: null; format: "astar_biglakes,astar_rivers" )'
    )
    parser.add_argument('--elfs',
                        help="Local spec programs folder (elf format)")
    parser.add_argument(
        '--times',
        help=
        "Profiing cluster checkpoint times (default: 1,1,1;(format 1,1,1) if set it manual, you must set archive id and ensure profiling id, cluster id, checkpoint id is ok)"
    )
    parser.add_argument(
        '--start-id',
        help=
        "Profiing cluster checkpoint start id (default: 0,0,0;(format 0,0,0) if set it manual, it will overwrite some result which is exists)"
    )
    parser.add_argument(
        '--emulator',
        default="NEMU",
        help="Specify the emulator (default: NEMU), options: NEMU, QEMU(unsupported)"
    )
    parser.add_argument(
        '--build-bbl-only', action='store_true', help="Generate spec bbl only"
    )
    parser.add_argument(
        '--max-threads',
        default=40,
        help="Max threads, must less then cpu nums (default: 10)"
    )
    parser.add_argument(
        '--CPU2017',
        default=True,
        action='store_true',
        help="Max threads, must less then cpu nums (default: 10)"
    )

    args = parser.parse_args()
    spec_app_list = app_list(args.spec_app_list, args.spec_apps, args.CPU2017)
    if args.CPU2017:
        spec_base_app_list = list(set(
            map(lambda item: os.path.split(get_cpu2017_info(os.environ.get("CPU2017_RUN_DIR"),"","")[item][0][0])[1], spec_app_list)))
    else:
        spec_base_app_list = list(set(
            map(lambda item: os.path.split(get_cpu2006_info(os.environ.get("CPU2006_RUN_DIR"),"","")[item][0][0])[1], spec_app_list)))


#    spec_base_app_list = list(
#        set(
#            map(lambda item: get_default_spec_list()[item]["base"],
#                spec_app_list)))
    print(spec_base_app_list)

    set_startid_times(args.start_id, args.times)

    generate_folders()

    if args.archive_id is None:
        generate_specapp_assembly(spec_base_app_list, args.elfs, args.max_threads)

        spec_app_execute_list = []
        for spec_app in spec_app_list:
            prepare_rootfs(build_config()["scripts_folder"], prepare_config()["elf_folder"], spec_app, True, args.CPU2017)
            if args.emulator == "QEMU":
                build_bbl_as_gcpt_payload(spec_app, build_config()["build_log"], build_config()["bin_folder"], "", build_config()["gcpt_bin_folder"], "", build_config()["assembly_folder"])
            else:
                build_spec_bbl(spec_app, build_config()["build_log"], build_config()["bin_folder"], "" ,build_config()["assembly_folder"])

            if args.build_bbl_only:
                exit(0)

            root_noods = generate_command(build_config()["bin_folder"], spec_app, def_config()["buffer"], "", args.emulator, os.path.join(def_config()["buffer"], "logs"))

#            list(map(print_tree, root_noods))
            spec_app_execute_list.append(root_noods)

        with concurrent.futures.ProcessPoolExecutor(max_workers=args.max_threads) as e:
            e.map(level_first_exec, spec_app_execute_list)
#        generate_result(def_config()["buffer"], os.path.join(def_config()["buffer"], "logs"))
    else:
        spec_app_execute_list = []
        for spec_app in spec_app_list:
            root_noods = generate_command(build_config()["bin_folder"], spec_app, def_config()["buffer"], "", args.emulator, os.path.join(def_config()["buffer"], "logs"))

#            list(map(print_tree, root_noods))
            spec_app_execute_list.append(root_noods)

        with concurrent.futures.ProcessPoolExecutor(max_workers=args.max_threads) as e:
            e.map(level_first_exec, spec_app_execute_list)
#
