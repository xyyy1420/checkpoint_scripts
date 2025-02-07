import os
import stat
import magic

def is_dynamic_library(file_path):
    try:
        with open(file_path, 'rb') as file:
            header = file.read(4)
            return header.startswith(b'\x7fELF')
    except Exception as e:
        print(f"Could not check file type for {file_path}: {e}")
        return False

def find_dynamic_libraries(search_dir='.'):
    dynamic_libraries = []
    for root, _, files in os.walk(search_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                if is_dynamic_library(file_path) or os.path.islink(file_path):
                    dynamic_libraries.append(file_path)
            except OSError as e:
                print(f"Error accessing file {file_path}: {e}")
    return dynamic_libraries

def get_dynamic_libraries_list(search_dir):
    libraries = find_dynamic_libraries(search_dir)
    initramfs_string_list = []
    for lib in libraries:
        initramfs_string_list.append([f"file /lib/{lib.split('/')[-1]}", lib, "755 0 0"])

    return initramfs_string_list

def get_jemalloc_libraries_list(riscv_toolchains_top):
    initramfs_string_list = [
        ["file /lib/libjemalloc.so", f"{riscv_toolchains_top}/lib/libjemalloc.so", "755 0 0"],
        ["file /lib/libjemalloc.so.2", f"{riscv_toolchains_top}/lib/libjemalloc.so.2", "755 0 0"],
    ]
    return initramfs_string_list

def check_file_exists(file_path):
    if os.path.exists(file_path):
        return True
    return False


def get_libraries_str(riscv_toolchains_top, using_jemalloc):
    libraries = get_dynamic_libraries_list(os.path.join(riscv_toolchains_top, "sysroot", "lib"))
    if using_jemalloc:
        libraries += get_jemalloc_libraries_list(riscv_toolchains_top)
#    for i in libraries:
#        assert(check_file_exists(i[1]))
    libraries_str = list(map(lambda x: f"{x[0]} {x[1]} {x[2]}", libraries))
    return libraries_str
