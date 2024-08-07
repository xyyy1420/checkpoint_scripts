## 环境准备

### 可以访问公共服务器
- 请执行
```bash
source /nfs/home/share/workload_env/env.sh
```

### 无法访问公共服务器
- 预先准备好 riscv64 工具链，可能用到的 prefix 有`riscv64-linux-gnu-`，`riscv64-unknown-linux-gnu-`，`riscv64-unknown-elf-`，需要的 gcc 版本最低应该是 14.0.0

- 克隆或下载 OpenSBI，Linux，workload_build_env，NEMU，QEMU，LibCheckpoint，LibCheckpointAlpha，riscv-rootfs
    - https://github.com/riscv-software-src/opensbi.git
    - https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.10.3.tar.xz
    - https://github.com/xyyy1420/workload_build_env.git
    - https://github.com/OpenXiangShan/NEMU.git
    - https://github.com/OpenXiangShan/qemu.git checkpoint分支
    - https://github.com/OpenXiangShan/LibCheckpoint.git
    - https://github.com/OpenXiangShan/LibCheckpointAlpha.git
    - https://github.com/OpenXiangShan/riscv-rootfs.git

- 准备 Linux kernel
    - 解压缩内核 `tar -xf linux-6.10.3.tar.xz`
    - 复制配置文件 `cp /path/to/workload_build_env/config/xiangshan_defconfig /path/to/linux/arch/riscv/config/`
    - 在 Linux kernel 目录下调整配置文件并保存为默认配置文件 `make menuconfig; make savedefconfig; mv defconfig arch/riscv/config/xiangshan_defconfig`
- 准备设备树
    - 构建单核多核设备树 `cd /path/to/workload_build_env/dts && ./build_dual_core_for_qemu.sh && ./build_single_core_for_nemu.sh`

- 构建 NEMU
    - 进入 NEMU 目录
    - 拉取 submodule `git submodule update --init`
    - 使用 `riscv64-xs-cpt_defconfig` 配置 NEMU `make riscv64-xs-cpt_defconfig`
    - 构建 NEMU `make -j`
    - 构建 simpoint `cd /path/to/NEMU/resource/simpoint/simpoint_repo && make -j`

- 构建 QEMU
    - 进入 QEMU 目录
    - 配置 QEMU `mkdir build && cd build && ../configure --target-list=riscv64-softmmu --enable-debug --enable-zstd --enable-plugins`
    - 构建 QEMU `make -j`

- 准备 riscv-rootfs
    - 进入 riscv-rootfs 目录
    - 构建 riscv-rootfs app `make install`

- 准备运行时所需文件的目录
    - 提前运行一遍 SPEC2006 和 SPEC2017 （根据自己需要可以仅运行其中一个）
    - 创建目录 `mkdir cpu2006_run_dir` 和 `mkdir cpu2017_run_dir`
    - 将运行结果所在的目录拷贝到`cpu2006_run_dir`中，例如 `cp cpu2006v99/benchspec/CPU2006/410.perlbench/run/run_base_ref_amd64-m64-gcc42-05.0001 cpu2006_run_dir/perlbench -r`
    - 对所有子项都这样操作，然后设置环境变量 `export CPU2006_RUN_DIR=/path/to/cpu2006_run_dir` 和 `export CPU2017_RUN_DIR=/path/to/cpu2017_run_dir`

- 导出环境变量
```bash
export ARCH=riscv
export LINUX_HOME=/path/to/linux
export OPENSBI_HOME=/path/to/opensbi
export XIANGSHAN_FDT=/path/to/workload_build_env/dts/build/xiangshan_dualcore.dtb
export RISCV=/path/to/riscv-toolchain
export RISCV_ROOTFS_HOME=/path/to/riscv-rootfs
export CPU2006_RUN_DIR=/path/to/cpu2006_run_dir
export CPU2017_RUN_DIR=/path/to/cpu2017_run_dir
export CROSS_COMPILE=/path/to/riscv-toolchains/bin/riscv64-unknown-linux-gnu-
export GCPT_HOME=/path/to/LibCheckpoint
export NEMU_HOME=/path/to/NEMU
export QEMU_HOME=/path/to/qemu
```

### 单核检查点

- 修改环境变量
    - `export XIANGSHAN_FDT=/path/to/workload_build_env/dts/build/xiangshan.dtb`
- 修改下述配置文件
    - 修改字段 `copies` 为 1

### 多核检查点
- 在导入环境变量之后仅需按照下述说明修改配置文件，并保证 `copies` 字段大于 1 即可（目前的环境下请保证该字段小于 4 ）

### 使用说明
- 克隆这个仓库[https://github.com/xyyy1420/checkpoint_scripts.git](https://github.com/xyyy1420/checkpoint_scripts.git) 到任意目录
- 参数说明

```
usage: generate_checkpoint.py [--config]

Auto profiling and checkpointing

optional arguments:
  --config              指定配置文件
```

- 配置文件说明

```yaml
base_config:
  message: "NULL" # 通常为空
  spec_app_list: null # 与下面的 spec_apps 选项作用一致，这里填写一个 list 文件的路径，list 文件中每行一个子项
  spec_apps: "gcc_scilab" # 这里填写用英文逗号分割的子项
  elf_folder: "./jemalloc_elf" # 使用的 elf 的路径
  times: "1,1,1" # profiling cluster checkpoint 各运行的次数
  start_id: "0,0,0" # profiling cluster checkpoint 各运行的结果保存路径的起始 id
  emulator: "QEMU" # 用于 profiling 和 checkpoint 的模拟器，可选 "QEMU" 或者 "NEMU"
  build_bbl_only: false # 设置为 true 时编译完所有的 workload 后结束运行
  max_threads: 70 # profiling cluster checkpoint 时可以使用的最大线程数
  CPU2017: false # 目标 elf 是否是 speccpu2017
  generate_rootfs_script_only: false # 是否仅生成 rootfs 脚本之后停止
  copies: 2 # profiling 和 checkpoint 并行执行多少个 spec 子项，当 copies=1 时 kernel 将放置在 0x80200000，否则 kernel 将放置在 0x80800000
  archive_id: null # 如果设置了 archive_id 将跳过 workload 构建前的阶段，直接使用该 id 下已有的 workload
  redirect_output: false # 是否重定向子项的输出
  cpu_bind: 0 # useless
  mem_bind: 0 # useless
  bootloader: "opensbi" # 使用 opensbi 还是 riscv-pk 作为启动器，riscv-pk 的流程目前维护不佳
  all_in_one_workload: true # 如果使用 all in one workload，将会使用 gcpt 链接 workload，生成的 workload 可以直接被启动，在使用 QEMU 作为模拟器时，必须使用 all in one workload
  boot_for_test: true # 设置为 true 时将在构建完 workload 使用上述配置文件中指定的模拟器运行 1min
archive_id_config: # 配置生成的 archive id，仅影响结果放置在哪里
  gcc_version: "gcc12.2.0"
  riscv_ext: "rv64gcb"
  base_or_fixed: "base"
  special_flag: "intFppOff_for_qemu_dual_core"
  group: "archgroup"
```

- 一键checkpoint
```
python3 generate_checkpoint.py --config config.yaml
```
- 本脚本目前仅维护使用opensbi的环境
