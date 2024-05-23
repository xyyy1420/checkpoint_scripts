export RISCV_ROOTFS_HOME=`pwd`/riscv-rootfs
export RISCV_LINUX_HOME=`pwd`/riscv-linux
export RISCV_PK_HOME=`pwd`/riscv-pk
if [ -z $RISCV ]; then
	export RISCV=/nfs/home/share/riscv
fi
export QEMU_HOME=`pwd`/qemu
export NEMU_HOME=`pwd`/nemu_rv64gc_checkpoint
