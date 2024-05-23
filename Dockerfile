FROM ubuntu:noble
WORKDIR /
RUN apt-get update && apt-get install wget tar git make gcc g++ gdb bison flex bc device-tree-compiler zstd libzstd-dev libsdl2-dev libreadline-dev man build-essential -y
RUN wget https://github.com/riscv-collab/riscv-gnu-toolchain/releases/download/2024.04.12/riscv64-glibc-ubuntu-22.04-gcc-nightly-2024.04.12-nightly.tar.gz -O riscv64-glibc.tar.gz
RUN wget https://github.com/riscv-collab/riscv-gnu-toolchain/releases/download/2024.04.12/riscv64-elf-ubuntu-22.04-gcc-nightly-2024.04.12-nightly.tar.gz -O riscv64-elf.tar.gz
# COPY riscv64-glibc.tar.gz /riscv64-glibc.tar.gz
# COPY riscv64-elf.tar.gz /riscv64-elf.tar.gz
RUN tar -xf riscv64-glibc.tar.gz && mv riscv riscv-glibc && rm riscv64-glibc.tar.gz
RUN tar -xf riscv64-elf.tar.gz && mv riscv riscv-elf && rm riscv64-elf.tar.gz
ENV PATH="${PATH}:/riscv-glibc/bin:/riscv-elf/bin"
ENV RISCV="/riscv-glibc"
COPY build.sh /home/ubuntu/build.sh
COPY prepare_env.sh /home/ubuntu/prepare_env.sh
RUN chmod +x /home/ubuntu/build.sh
RUN git config --global http.postBuffer 1048576000 && git config --global core.compression -1 && git config --global http.lowSpeedLimit 0 && git config --global http.lowSpeedTime 999999
RUN cd /home/ubuntu && CLONE=1 ./build.sh

#COPY riscv-pk /home/ubuntu/riscv-pk
#COPY riscv-rootfs /home/ubuntu/riscv-rootfs
#COPY riscv-linux /home/ubuntu/riscv-linux
#COPY qemu /home/ubuntu/qemu

COPY patch/yylloc.patch /home/ubuntu/riscv-linux
COPY patch/riscv_linux_Makefile.patch /home/ubuntu/riscv-linux

WORKDIR /home/ubuntu/riscv-linux
RUN git apply yylloc.patch && git apply riscv_linux_Makefile.patch
WORKDIR /home/ubuntu/riscv-pk
RUN git apply gcpt.patch
WORKDIR /home/ubuntu
RUN CONFIG_LINUX=emu_defconfig bash build.sh
RUN BUILD_BBL=1 bash build.sh

#COPY nemu_rv64gc_checkpoint /home/ubuntu/nemu_rv64gc_checkpoint
#COPY nemu_rv64gcvh_checkpoint /home/ubuntu/nemu_rv64gcvh_checkpoint
RUN INIT_NEMU=1 bash build.sh

COPY cpu2006rundir /home/ubuntu/cpu2006_run_dir
ENV CPU2006_RUN_DIR=/home/ubuntu/cpu2006_run_dir

COPY checkpoint_scripts/dump_result.py /home/ubuntu/dump_result.py
COPY checkpoint_scripts/generate_bbl.py /home/ubuntu/generate_bbl.py
COPY checkpoint_scripts/generate_checkpoint.py /home/ubuntu/generate_checkpoint.py
COPY checkpoint_scripts/spec_gen.py /home/ubuntu/spec_gen.py
COPY checkpoint_scripts/take_checkpoint.py /home/ubuntu/take_checkpoint.py

#COPY test/elf /home/ubuntu/elfs

RUN sed -i 's/initramfs.txt/initramfs-spec.txt/' /home/ubuntu/riscv-linux/arch/riscv/configs/fpga_defconfig
RUN CONFIG_LINUX=fpga_defconfig bash build.sh
#RUN SPEC_APPS=gcc_scilab ELF_FOLDER=/home/ubuntu/elfs bash build.sh
