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

    def build_spec_bbl(self, spec, build_log_folder, spec_bin_folder, bin_suffix, assembly_folder, qemu_payload):
        PK_HOME = self.env_vars.get("RISCV_PK_HOME")
        if not PK_HOME:
            raise EnvironmentError("Environment variable RISCV_PK_HOME is not set or not initialized.")
        GCPT_HOME = self.env_vars.get("GCPT_HOME")
        if not GCPT_HOME:
            raise EnvironmentError("Environment variable RISCV_PK_HOME is not set or not initialized.")

        if qemu_payload:
            print(f"build qemu payload: {spec}-gcpt-bbl-linux-spec...")
        else:
            print(f"build nemu payload: {spec}-bbl-linux-spec...")

        out_log = os.path.join(build_log_folder, f"build-{spec}-out.log")
        err_log = os.path.join(build_log_folder, f"build-{spec}-err.log")

        pk_commands = [["make", "clean"], ["make", "-j70"]]
        self.run_commands(pk_commands, PK_HOME, out_log, err_log)
        self.copy_files(PK_HOME, spec, bin_suffix, assembly_folder, spec_bin_folder, {
            "build/bbl.bin": "",
            "build/bbl.txt": ".pk.s",
            "build/vmlinux.txt": ".vmlinux.s"
        })

        if qemu_payload:
            gcpt_commands = [["make", "clean"], ["make", "USING_QEMU_DUAL_CORE_SYSTEM=1", f"GCPT_PAYLOAD_PATH={os.path.join(PK_HOME, 'build', 'bbl.bin')}", "-j10"]]

            self.run_commands(gcpt_commands, GCPT_HOME, out_log, err_log)
            self.copy_files(GCPT_HOME, spec, bin_suffix, assembly_folder, spec_bin_folder, {
                "build/gcpt.bin": ""
            })

    def build_opensbi_payload(self, spec, build_log_folder, spec_bin_folder, bin_suffix, gcpt_bin_folder, gcpt_bin_suffix, assembly_folder, withGCPT=False):
        required_vars = ["LINUX_HOME", "OPENSBI_HOME", "XIANGSHAN_FDT", "GCPT_HOME"]
        if not all([self.env_vars.get(var) for var in required_vars]):
            raise EnvironmentError("One or more required environment variables are not set or not initialized.")

        print(f"build {spec}-opensbi-linux-spec...{' with GCPT' if withGCPT else ''}")

        out_log = os.path.join(build_log_folder, f"build-binary-with-{spec}-out.log")
        err_log = os.path.join(build_log_folder, f"build-binary-with-{spec}-err.log")
#["make", "clean"], 
        linux_commands = [["make", "-j70"]]
        fw_payload_bin_size = os.path.getsize(f"{self.env_vars['LINUX_HOME']}/arch/riscv/boot/Image")
        fw_payload_fdt_addr = (((fw_payload_bin_size + 0x800000) + 0xfffff) // 0x100000) * 0x100000
        fw_payload_fdt_addr = fw_payload_fdt_addr + 0x80000000
        print(f"SPEC: {spec}, file size: {fw_payload_bin_size}, fw_payload_fdt_addr: {fw_payload_fdt_addr}")
        opensbi_commands = [
            ["rm", "-rf", "build"],
            ["make", "PLATFORM=generic", f"FW_PAYLOAD_PATH={self.env_vars['LINUX_HOME']}/arch/riscv/boot/Image", f"FW_FDT_PATH={self.env_vars['XIANGSHAN_FDT']}", "FW_PAYLOAD_OFFSET=0x700000", f"FW_PAYLOAD_FDT_ADDR={fw_payload_fdt_addr}", "-j10"]
        ]

        self.run_commands(linux_commands, self.env_vars["LINUX_HOME"], out_log, err_log)
        self.run_commands(opensbi_commands, self.env_vars["OPENSBI_HOME"], out_log, err_log)

#        fw_payload_bin_dst_path = os.path.join(spec_bin_folder, f"{spec}{bin_suffix}")
        self.copy_files(self.env_vars["OPENSBI_HOME"], spec, bin_suffix, assembly_folder, spec_bin_folder, {
            "build/platform/generic/firmware/fw_payload.bin": ""
        })

        if withGCPT:
            gcpt_commands = [["make", "clean"], ["make", f'GCPT_PAYLOAD_PATH={os.path.join(self.env_vars["OPENSBI_HOME"],"build","platform","generic","firmware","fw_payload.bin")}', "USING_QEMU_DUAL_CORE_SYSTEM=1"]]
            self.run_commands(gcpt_commands, self.env_vars["GCPT_HOME"], out_log, err_log)
            self.copy_files(self.env_vars["GCPT_HOME"], spec, gcpt_bin_suffix, assembly_folder, gcpt_bin_folder, {
                "build/gcpt.bin": "",
                "build/gcpt.txt": ".gcpt.s"
            })

    @staticmethod
    def copy_files(base_path, spec, suffix, assembly_folder, bin_folder, files):
        """Copy files from base path to their respective destinations with appropriate suffixes."""
        for src, dest_suffix in files.items():
            if dest_suffix:
                assembly_dest_path = os.path.join(assembly_folder, f"{spec}{suffix}{dest_suffix}")
                shutil.copy(src_path, assembly_dest_path)
                continue

            src_path = os.path.join(base_path, src)
            bin_dest_path = os.path.join(bin_folder, f"{spec}{suffix}")
            shutil.copy(src_path, bin_dest_path)

# Example usage
#builder = Builder(env_vars_to_check=["LINUX_HOME", "OPENSBI_HOME", "XIANGSHAN_FDT", "NEMU_HOME", "RISCV_PK_HOME"])
#builder.build_spec_bbl("example_spec", "/path/to/logs", "/path/to/bin", "_suffix", "/path/to/assembly")
#builder.build_opensbi_payload("example_spec", "/path/to/logs", "/path/to/bin", "_suffix", "/path/to/gcpt_bin", "_gcpt_suffix", "/path/to/assembly", withGCPT=True)
#