'''
Example:
python3 select_points.py -i /path/to/cluster-0-0.json -o name_prefix_of_output -w 0.8
'''

import json
import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', '--count-limit', type=int)
argparser.add_argument('-w', '--weight-limit', type=float, default=1.0)
argparser.add_argument('-t', '--test-set', type=str, default='int')
argparser.add_argument('-i', '--input-json', required=True)
argparser.add_argument('-o', '--output-name', type=str, default='output')

args = argparser.parse_args()

if args.count_limit is None:
    count_limit = 10000
    count_limit_str = ''
else:
    count_limit = args.count_limit
    count_limit_str = f'_top{count_limit}'

coverage_limit = args.weight_limit

ver = '06'
weight_file = args.input_json
test_set = 'int'

with open(weight_file) as f:
    js = json.load(f)

new_js = {}
rest_js = {}
files = []
rest_files = []

workloads = []
if len(test_set):
    with open(f'spec_info/spec{ver}_{test_set}.lst') as f:
        for line in f:
            workloads.append(line.strip())

for workload, info in js.items():
    if workload not in workloads:
        continue
    cumm_weight = 0.0
    count = 0

    if workload not in new_js:
        new_js[workload] = {}
        rest_js[workload] = {}
    new_js[workload]['insts'] = js[workload]['insts']
    new_js[workload]['points'] = {}
    rest_js[workload]['insts'] = js[workload]['insts']
    rest_js[workload]['points'] = {}
    # sorted_points = sorted(info['points'], reverse=True)
    # sort info['points'] by value
    sorted_points = sorted(info['points'], key=lambda x: info['points'][x], reverse=True)
    cover_satisfied = False
    for point in sorted_points:
        weight = info['points'][point]

        cumm_weight += float(weight)
        count += 1
        print(workload, point, weight)

        if cover_satisfied:
            rest_files.append(f'{workload}_{point} {workload}_{point}_{weight}/0/')
            rest_js[workload]['points'][point] = weight
        else:
            files.append(f'{workload}_{point} {workload}_{point}_{weight}/0/')
            new_js[workload]['points'][point] = weight
            if count >= count_limit or cumm_weight >= coverage_limit:
                cover_satisfied = True

n_chunks = 1
chunk_size = len(files) // n_chunks
for i in range(n_chunks):
    chunk = files[:chunk_size]
    with open(f'{args.output_name}_{test_set}_cover{coverage_limit:.2f}{count_limit_str}.lst.{i}', 'w') \
            as outf:
        outf.write('\n'.join(chunk))
    files = files[chunk_size:]

with open(f'{args.output_name}_{test_set}_cover{coverage_limit:.2f}{count_limit_str}-unused.lst.{i}', 'w') \
        as outf:
    outf.write('\n'.join(rest_files))

with open(f'{args.output_name}_{test_set}_cover{coverage_limit:.2f}{count_limit_str}.json', 'w') as outf:
    json.dump(new_js, outf, indent=4)

with open(f'{args.output_name}_{test_set}_cover{coverage_limit:.2f}{count_limit_str}-unused.json', 'w') as outf:
    json.dump(rest_js, outf, indent=4)
