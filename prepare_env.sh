#!/bin/bash
RISCV_ROOTFS_HOME="$(pwd)/riscv-rootfs"
RISCV_LINUX_HOME="$(pwd)/riscv-linux"
RISCV_PK_HOME="$(pwd)/riscv-pk"
QEMU_HOME="$(pwd)/qemu"
NEMU_HOME="$(pwd)/nemu_rv64gc_checkpoint"

export RISCV_ROOTFS_HOME
export RISCV_LINUX_HOME
export RISCV_PK_HOME
export QEMU_HOME
export NEMU_HOME

if [ -z "$RISCV" ]; then
	RISCV="/nfs/home/share/riscv"
	export RISCV
fi

