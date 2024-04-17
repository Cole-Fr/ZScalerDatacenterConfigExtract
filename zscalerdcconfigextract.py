import requests
import json
import ipaddress
import argparse
import configparser
import os
import csv
from datetime import datetime

# Defining Functions 
def ip_range(input):
    first_usable = input.get('first usable')
    last_usable = input.get('last usable')
    usable_range = str(first_usable) + ' - ' + str(last_usable)
    return usable_range
def print_values(requested):
    w = 0
    requested.sort()
    while w < len(requested):
        if 'None' not in requested[w]:
            print(requested[w])
        w = w + 1
def clean_item(input):
    clean_item = (str(input).split(' : '))[1]
    return clean_item
def dir_path(string):
    if os.path.isdir(string):
        return string
    else:
        raise NotADirectoryError(string)

# Command Line Options
parser = argparse.ArgumentParser(
    prog = "ZScaler Datacenter Config Extract Tool",
    description = "This script pulls the configuration for the specified ZScaler datacenters. Configuration can be done in the command-line or provided by a config file named 'config.ini'.",
    epilog = "Although there are many safeguards to stop from the use of bad configs or errors not all situations can be caught. If no output is provided check the configuration and verify its accuracy."
)
parser.add_argument('-nocfg', '-noconfig', dest = 'no_config', action = 'store_true', help = 'Specifies if the present config file should be ignored if one is present.')
parser.add_argument('-c', '-cloud', dest = 'cloud', type = str, help = 'Specifies ZScaler cloud that the data will be pulled for ex. "zscaler.net"')
parser.add_argument('-r', '-regions', dest = 'regions', type = str, help = 'Specifies ZScaler regions, for the specified cloud, that will be used for the data pull. for ex."Americas,EMEA" ')
parser.add_argument('-d', '-datacenters', dest = 'datacenters', type = str, help = 'Specifies ZScaler datacenters for the specified cloud, that will be used for the data pull. ex. "Atlanta II,Atlanta III, Boston I"')
parser.add_argument('-i', '-ipformat', dest = 'ipformat', type = str, help = 'Specifies the type of information pulled ex. "range", "cidr", "wildcard" or "all". As a note "all" will print all information into a csv file available for further analysis.')
parser.add_argument('-o', '-output_format', dest = 'output_format', type = str, help = 'Denotes the type of output "simple" will list all data without denoting location. "bydatacenter" will give the data structured with the datacenter city as a label. "All" ipformat will print as a CSV file.')
parser.add_argument('-p', '-path', dest = 'path', type = dir_path, help = r'Specifies the directory path that should be used to deposit csv files.*Required for all/csv export*')
args = parser.parse_args()

# Variable Requirment Initialization
if os.path.exists('config.ini') and args.no_config == False:
    config = configparser.ConfigParser()
    config.read('config.ini')
    cloud = config['Default']['Cloud']
    regions = config['Default']['Regions'].split(',')
    datacenters = config['Default']['Datacenters'].split(',')
    ipformat = config['Parameters']['IPType']
    output_format = config['Parameters']['Format']
    path = config['Parameters']['Path']
elif args.cloud is None: 
    exit(print('Config Error: ZScaler Cloud not specified'))
elif all([args.cloud]) and args.ipformat == 'all' or args.ipformat == 'All' :
    cloud = args.cloud
    regions = args.regions
    datacenters = args.datacenters
    ipformat = args.ipformat
    output_format = 'All'
    path = args.path
elif all([args.cloud, args.ipformat, args.output_format]):
    cloud = args.cloud
    regions = args.regions
    datacenters = args.datacenters
    ipformat = args.ipformat
    output_format = args.output_format
else:
    exit(print('Config Error: Incomplete Command-Line arguments or incomplete config file. ** IPFormat or Output Format not defined **- verify config.ini or add parameters run --help for more info'))

# Parameter Validation:
if ipformat == 'all' or ipformat == 'All':
    if output_format != 'all' and output_format != 'All':
        exit(print('Config Error: "All" data format only supports CSV export. Define the directory path or file will be created in directory script is run from.'))

# Data pull for respective cloud from config.zscaler.com
match cloud: 
    case "zscaler.net": 
        data = json.loads((requests.get('https://config.zscaler.com/api/zscaler.net/cenr/json')).text)
    case "zscalerone.net":
        data = json.loads((requests.get('https://config.zscaler.com/api/zscalerone.net/cenr/json')).text)
    case "zscalertwo.net": 
        data = json.loads((requests.get('https://config.zscaler.com/api/zscalertwo.net/cenr/json')).text)
    case 'zscalerthree.net':
        data = json.loads((requests.get('https://config.zscaler.com/api/zscalerthree.net/cenr/json')).text)
    case "zscloud.net": 
        data = json.loads((requests.get('https://config.zscaler.com/api/zscloud.net/cenr/json')).text)
    case "zscalerbeta.net":
        data = json.loads((requests.get('https://config.zscaler.com/api/zscalerbeta.net/cenr/json')).text)
    case "zscalergov.net": 
        data = json.loads((requests.get('https://config.zscaler.com/api/zscalergov.net/cenr/json')).text)
    case "zscalerten.net":
        data = json.loads((requests.get('https://config.zscaler.com/api/zscalerten.net/cenr/json')).text)

# Removal of regions and datacenters that are not defined. No defenition returns all 
if any([args.regions, args.datacenters]):
    remove_region = []
    for region in data[cloud]:
        remove_datacenter = []
        if args.regions is not None:
            clean_rg = clean_item(region)
            if clean_rg not in regions:
                remove_region.append(region)
        if args.datacenters is not None:
            for datacenter in data[cloud][region]:
                clean_dc = clean_item(datacenter)
                if clean_dc not in datacenters:
                    remove_datacenter.append(datacenter)
        for datacenter in remove_datacenter:
            del data[cloud][region][datacenter]
    for region in remove_region:
        del data[cloud][region]

# Sanitize/manipulate data
for region in data[cloud]:
    for city in data[cloud][region]:
        clean_city = clean_item(city)
        location = data[cloud][region][city]
        cidr_range = [block.get('range') for block in location] 
        x = 0
        for cidr in cidr_range:
            if cidr != '':
                check_network = ipaddress.ip_network(cidr)
                first, last = check_network[1], check_network[-2]
                location[x]['first usable'] = str(first)
                location[x]['last usable'] = str(last)
                if first.version == 4:
                    wildcard = []
                    location[x]['wildcard'] = wildcard
                    first_split = str(first).split('.')
                    last_split = str(last).split('.')
                    wildcard.append(first_split[0] + '.' + first_split[1] + '.' + first_split[2]+'.*')
                    diff = (int(last_split[2]) - int(first_split[2]))
                    while  diff >= 0 :
                        new_wild = (first_split[0] + '.' + first_split[1] + '.' + str((int(first_split[2]) + diff)) +'.*')
                        diff = diff - 1
                        if new_wild in wildcard or new_wild is None:
                            continue
                        else: 
                            wildcard.append(new_wild)  
                wildcard.sort()
            x = x + 1

# All information to CSV
if (ipformat == 'all' or ipformat == 'All'):
    if args.path is not None:
        dir_path(args.path) 
        filename = args.path + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.csv'
    else:
        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.csv'
    fieldnames =  ['ZScaler Cloud', 'Region', 'City', 'CIDR', 'VPN', 'GRE', 'Hostname', 'Latitude', 'Longitude', 'First IP', 'Last IP', 'Wildcard']
    with open(filename, mode ='w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, quotechar = "'")
        csvwriter.writerow(fieldnames)
        for region in data[cloud]:
            for datacenter in data[cloud][region]:
                w = 0
                for item in data[cloud][region][datacenter]:
                    r = data[cloud][region][datacenter][w]
                    t = r.get('wildcard')
                    if t is not None: 
                        seperator = '-'
                        wildcard_all = seperator.join(r.get('wildcard'))
                    new_row = [str(cloud), str(clean_item(region)), str(clean_item(datacenter)), str(r.get('range')), str(r.get('vpn')), str(r.get('gre')), str(r.get('hostname')), str(r.get('latitude')), str(r.get('longitude')), str(r.get('first usable')), str(r.get('last usable')), str(wildcard_all)]
                    w = w + 1
                    csvwriter.writerow(new_row)
    print('CSV file written to: '+ filename)
# Creating simple output
elif output_format == 'simple' or output_format == 'Simple':
    if ipformat == 'wildcard' or ipformat == 'Wildcard':  
        simple_wildcard = []
        for region in data[cloud]:
            for datacenter in data[cloud][region]:
                possible_items = [part.get(ipformat) for part in data[cloud][region][datacenter]] 
                w = 0
                for list in possible_items:
                    if list is not None:
                        frst_usable = data[cloud][region][datacenter][w].get('first usable')
                        if ipaddress.ip_address(frst_usable).version == 4:
                            for wildcard_ip in list:
                                if wildcard_ip not in simple_wildcard:
                                    simple_wildcard.append(wildcard_ip)
                    w = w + 1
        print_values(simple_wildcard)
    elif ipformat == 'range' or ipformat == 'Range':  
        ranges = []
        for region in data[cloud]:
            for datacenter in data[cloud][region]:
                w = 0
                while w < len(data[cloud][region][datacenter]):
                    rnge = ip_range(data[cloud][region][datacenter][w])
                    if rnge not in ranges:
                        ranges.append(rnge)
                    w = w + 1
        print_values(ranges)   
    elif ipformat == 'cidr' or ipformat == 'CIDR':
        cidr_list = []
        for region in data[cloud]:
            for datacenter in data[cloud][region]:
                w = 0
                while w < len(data[cloud][region][datacenter]):
                    cidr = data[cloud][region][datacenter][w].get('range')
                    if cidr not in cidr_list:
                        cidr_list.append(cidr)
                    w = w + 1
        print_values(cidr_list)

# Output by Datacenter
elif output_format == 'bydatacenter' or output_format == 'ByDatacenter':
    if ipformat == 'wildcard' or ipformat == 'Wildcard':  
        for region in data[cloud]:
            if len(data[cloud][region]) != 0:
                print(clean_item(region))
            for datacenter in data[cloud][region]:
                print(clean_item(datacenter))
                simple_wildcard = []
                possible_items = [part.get(ipformat) for part in data[cloud][region][datacenter]] 
                w = 0
                for list in possible_items:
                    if list is not None:
                        frst_usable = data[cloud][region][datacenter][w].get('first usable')
                        if ipaddress.ip_address(frst_usable).version == 4:
                            for wildcard_ip in list:
                                if wildcard_ip not in simple_wildcard:
                                    simple_wildcard.append(wildcard_ip)
                    w = w + 1
                print_values(simple_wildcard)
    elif ipformat == 'range' or ipformat == 'Range': 
        for region in data[cloud]:
            if len(data[cloud][region]) != 0:
                print(clean_item(region))
            for datacenter in data[cloud][region]:
                print(clean_item(datacenter))
                ranges = []
                w = 0
                while w < len(data[cloud][region][datacenter]):
                    rnge = ip_range(data[cloud][region][datacenter][w])
                    if rnge not in ranges:
                        ranges.append(rnge)
                    w = w + 1
                print_values(ranges)   
    elif ipformat == 'cidr' or ipformat == 'CIDR':
        for region in data[cloud]:
            if len(data[cloud][region]) != 0:
                print(clean_item(region))
            for datacenter in data[cloud][region]:
                print(clean_item(datacenter))
                cidr_list = []
                w = 0
                while w < len(data[cloud][region][datacenter]):
                    cidr = data[cloud][region][datacenter][w].get('range')
                    if cidr not in cidr_list:
                        cidr_list.append(cidr)
                    w = w + 1
                print_values(cidr_list)
else:
    exit(print('Configuration Error: IPFormat, Output Format, or Path not specified. ** Path is only applicable if IPFormat and Output Format are "All".**  Run -h for help.'))
