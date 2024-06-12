import os
import shutil
import subprocess
import os
import subprocess
import shutil

class Builder:
    def __init__(self, env_vars_to_check=None):
        """Initialize Builder with optional environment variables to check."""
        self.env_vars = {}
        if env_vars_to_check:
            for env_var in env_vars_to_check:
                self.env_vars[env_var] = self.check_directory(env_var)

    @staticmethod
    def check_directory(env_var):
        """Check if the environment variable is set and points to an existing directory."""
        path = os.environ.get(env_var)
        if not path:
            raise EnvironmentError(f"Environment variable {env_var} is not set.")
        if not os.path.exists(path):
            raise EnvironmentError(f"Path {path} for environment variable {env_var} does not exist.")
        return path

    @staticmethod
    def run_commands(commands, cwd, out_log, err_log):
        """Run a series of commands in a specified directory, logging output and errors."""
        with open(out_log, "a", encoding="utf-8") as out, open(err_log, "a", encoding="utf-8") as err:
            for command in commands:
                res = subprocess.run(command, cwd=cwd, stdout=out, stderr=err, check=True)
                res.check_returncode()

    def build_spec_bbl(self, spec, build_log_folder, spec_bin_folder, bin_suffix, assembly_folder):
        print("build_spec_bbl")
        PK_HOME = self.env_vars.get("RISCV_PK_HOME")
        if not PK_HOME:
            raise EnvironmentError("Environment variable RISCV_PK_HOME is not set or not initialized.")

        print(f"build {spec}-bbl-linux-spec...")

        out_log = os.path.join(build_log_folder, f"build-{spec}-out.log")
        err_log = os.path.join(build_log_folder, f"build-{spec}-err.log")

        pk_commands = [["make", "clean"], ["make", "-j70"]]
        self.run_commands(pk_commands, PK_HOME, out_log, err_log)

        self.copy_files(PK_HOME, spec, bin_suffix, assembly_folder, spec_bin_folder, {
            "build/bbl.bin": "",
            "build/bbl.txt": ".pk.s",
            "build/vmlinux.txt": ".vmlinux.s"
        })

    def build_opensbi_payload(self, spec, build_log_folder, spec_bin_folder, bin_suffix, gcpt_bin_folder, gcpt_bin_suffix, assembly_folder, withGCPT=False):
        required_vars = ["LINUX_HOME", "OPENSBI_HOME", "XIANGSHAN_FDT", "NEMU_HOME"]
        if not all([self.env_vars.get(var) for var in required_vars]):
            raise EnvironmentError("One or more required environment variables are not set or not initialized.")

        print(f"build {spec}-opensbi-linux-spec...{' with GCPT' if withGCPT else ''}")

        out_log = os.path.join(build_log_folder, f"build-binary-with-{spec}-out.log")
        err_log = os.path.join(build_log_folder, f"build-binary-with-{spec}-err.log")

        linux_commands = [["make", "clean"], ["make", "-j10"]]
        opensbi_commands = [
            ["rm", "-rf", "build"],
            ["make", "PLATFORM=generic", f"FW_PAYLOAD_PATH={self.env_vars['LINUX_HOME']}/arch/riscv/boot/Image", f"FW_FDT_PATH={self.env_vars['XIANGSHAN_FDT']}", "FW_PAYLOAD_OFFSET=0x160000", "-j10"]
        ]

        self.run_commands(linux_commands, self.env_vars["LINUX_HOME"], out_log, err_log)
        self.run_commands(opensbi_commands, self.env_vars["OPENSBI_HOME"], out_log, err_log)

        fw_payload_bin_dst_path = os.path.join(spec_bin_folder, f"{spec}{bin_suffix}")
        self.copy_files(self.env_vars["OPENSBI_HOME"], spec, bin_suffix, assembly_folder, spec_bin_folder, {
            "build/platform/generic/firmware/fw_payload.bin": ""
        })

        if withGCPT:
            gcpt_commands = [["make", "clean"], ["make", f"GCPT_PAYLOAD_PATH={fw_payload_bin_dst_path}"]]
            self.run_commands(gcpt_commands, os.path.join(self.env_vars["NEMU_HOME"], "resource", "gcpt_restore"), out_log, err_log)
            self.copy_files(os.path.join(self.env_vars["NEMU_HOME"], "resource", "gcpt_restore"), spec, gcpt_bin_suffix, assembly_folder, gcpt_bin_folder, {
                "build/gcpt.bin": "",
                "build/gcpt.txt": ".gcpt.s"
            })

    @staticmethod
    def copy_files(base_path, spec, suffix, assembly_folder, bin_folder, files):
        """Copy files from base path to their respective destinations with appropriate suffixes."""
        for src, dest_suffix in files.items():
            src_path = os.path.join(base_path, src)
            bin_dest_path = os.path.join(bin_folder, f"{spec}{suffix}")
            shutil.copy(src_path, bin_dest_path)

            if dest_suffix:
                assembly_dest_path = os.path.join(assembly_folder, f"{spec}{suffix}{dest_suffix}")
                shutil.copy(src_path, assembly_dest_path)

# Example usage
#builder = Builder(env_vars_to_check=["LINUX_HOME", "OPENSBI_HOME", "XIANGSHAN_FDT", "NEMU_HOME", "RISCV_PK_HOME"])
#builder.build_spec_bbl("example_spec", "/path/to/logs", "/path/to/bin", "_suffix", "/path/to/assembly")
#builder.build_opensbi_payload("example_spec", "/path/to/logs", "/path/to/bin", "_suffix", "/path/to/gcpt_bin", "_gcpt_suffix", "/path/to/assembly", withGCPT=True)
#