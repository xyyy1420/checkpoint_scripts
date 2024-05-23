import os
import shutil
import subprocess


def build_spec_bbl(spec, build_log_folder, spec_bin_folder, bin_suffix, assembly_folder):

    print(f"build {spec}-bbl-linux-spec...")

    with open(
        os.path.join(build_log_folder, f"build-{spec}-out.log"), "w"
    ) as out, open(
        os.path.join(build_log_folder, f"build-{spec}-err.log"), "w"
    ) as err:
        pk_folder=os.environ.get("RISCV_PK_HOME")
        if pk_folder is None or not os.path.exists(pk_folder):
            print("riscv-pk is not exists")
            exit(-1)

        res = subprocess.run(
            ["make", "clean"], cwd=pk_folder, stdout=out, stderr=err
        )
        res.check_returncode()
        res = subprocess.run(
            ["make", "-j70"], cwd=pk_folder, stdout=out, stderr=err
        )
        res.check_returncode()

    bbl_bin_src_path = os.path.join(pk_folder, "build", "bbl.bin")
    bbl_bin_dest_path = os.path.join(
        spec_bin_folder,
        "{}{}".format(spec, bin_suffix)
    )
    shutil.copy(bbl_bin_src_path, bbl_bin_dest_path)

    bbl_txt_src_path = os.path.join(pk_folder, "build", "bbl.txt")
    bbl_txt_dest_path = os.path.join(
        assembly_folder,
        "{}{}{}".format(spec,
                        bin_suffix, ".pk.s")
    )
    shutil.copy(bbl_txt_src_path, bbl_txt_dest_path)

    kernel_txt_src_path = os.path.join(
        pk_folder, "build", "vmlinux.txt"
    )
    kernel_txt_dest_path = os.path.join(
        assembly_folder,
        "{}{}{}".format(spec,
                        bin_suffix, ".vmlinux.s")
    )
    shutil.copy(kernel_txt_src_path, kernel_txt_dest_path)


def build_bbl_as_gcpt_payload(spec, build_log_folder, spec_bin_folder, bin_suffix, gcpt_bin_folder, gcpt_bin_suffix, assembly_folder):
    with open(
        os.path.join(
            build_log_folder, f"build-{spec}-aspayload-out.log"
        ), "w"
    ) as out, open(
        os.path.join(
            build_log_folder, f"build-{spec}-aspayload-err.log"
        ), "w"
    ) as err:

        res = subprocess.run(
            ["make", "clean"],
            cwd=os.path.join(
                os.environ.get("NEMU_HOME"), "resource", "gcpt_restore"
            ),
            stdout=out,
            stderr=err
        )
        res.check_returncode()

        res = subprocess.run(
            [
                "make", "GCPT_PAYLOAD_PATH={}".format(
                    os.path.abspath(
                        os.path.join(
                            spec_bin_folder,
                            "{}{}".format(spec,
                                          bin_suffix)
                        )
                    )
                )
            ],
            cwd=os.path.join(
                os.environ.get("NEMU_HOME"), "resource", "gcpt_restore"
            ),
            stdout=out,
            stderr=err
        )
        res.check_returncode()

    gcpt_bin_src_path = os.path.join(
        os.environ.get("NEMU_HOME"), "resource", "gcpt_restore", "build",
        "gcpt.bin"
    )
    gcpt_bin_dest_path = os.path.join(
        gcpt_bin_folder,
        "{}{}".format(spec,
                      gcpt_bin_suffix)
    )
    shutil.copy(gcpt_bin_src_path, gcpt_bin_dest_path)

    gcpt_txt_src_path = os.path.join(
        os.environ.get("NEMU_HOME"), "resource", "gcpt_restore", "build",
        "gcpt.txt"
    )
    gcpt_txt_dest_path = os.path.join(
        assembly_folder,
        "{}{}{}".format(spec,
                        gcpt_bin_suffix, ".gcpt.s")
    )
    shutil.copy(gcpt_txt_src_path, gcpt_txt_dest_path)
