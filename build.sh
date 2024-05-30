#!/bin/bash

set -x
set -o errexit
source prepare_env.sh

export ENV_HOME=`pwd`

clone_repo()
{
  git clone https://github.com/OpenXiangShan/riscv-pk -b noop $RISCV_PK_HOME

  git clone https://github.com/OpenXiangShan/riscv-linux -b nanshan $RISCV_LINUX_HOME

  git clone https://github.com/OpenXiangShan/riscv-rootfs -b master $RISCV_ROOTFS_HOME

  git clone https://github.com/OpenXiangShan/qemu.git -b checkpoint $QEMU_HOME

  git clone https://github.com/OpenXiangShan/NEMU.git -b master $NEMU_HOME

  cd nemu_rv64gc_checkpoint && git submodule update --init

  git clone https://github.com/OpenXiangShan/NEMU.git -b gcpt_new_mem_layout nemu_rv64gcvh_checkpoint

  cd nemu_rv64gcvh_checkpoint && git submodule update --init
}

export -f clone_repo

if [ $CLONE ]; then
  clone_repo
fi

config_linux()
{
  config=$1
  cd $RISCV_LINUX_HOME && \
    make ARCH=riscv CROSS_COMPILE=riscv64-unknown-linux-gnu- $config
    if [ $? -ne 0 ]; then
      exit -1
    fi
}

export -f config_linux
if [ $CONFIG_LINUX ]; then
  config_linux $CONFIG_LINUX
fi

if [ $BUILD_BBL ]; then
cd $RISCV_PK_HOME && \
  make clean && mkdir build && make -j
  if [ $? -ne 0 ]; then
    exit -1
  fi
fi

if [ $CLEAN_REPO ]; then
  rm -irf $RISCV_PK_HOME
  rm -irf $RISCV_LINUX_HOME
  rm -irf $RISCV_ROOTFS_HOME
  rm -irf $QEMU_HOME
fi

build_bbl ()
{
  elf_dir=$1
  spec_apps=$2
  if [ -f "$spec_app" ]; then
    python3 generate_checkpoint.py --elfs $elf_dir --spec-app-list $spec_apps
  else
    python3 generate_checkpoint.py --elfs $elf_dir --spec-apps $spec_apps
  fi
}
export -f build_bbl

if [ $SPEC_APPS ]; then
    build_bbl $ELF_FOLDER $SPEC_APPS
fi

build_NEMU ()
{
  cd $NEMU_HOME
  make riscv64-xs-cpt_defconfig
  make -j
  git submodule update --init
  cd $NEMU_HOME/resource/gcpt_restore && make -j
  cd $NEMU_HOME/resource/simpoint/simpoint_repo && make -j
  if [ $? -ne 0 ]; then
    exit -1
  fi
}

export -f build_NEMU

if [ $INIT_NEMU ]; then
  build_NEMU
fi

if [ $LINK_PAYLOAD ]; then
  build_GCPT_PAYLOAD $LINK_PAYLOAD
fi

