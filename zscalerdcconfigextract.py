#!/usr/bin/env python3
"""
ZScaler Datacenter Config Extract Tool

This script pulls the configuration for specified ZScaler datacenters.
Configuration can be done via command-line or provided by a config file named 'config.ini'.
"""

import requests
import json
import ipaddress
import argparse
import configparser
import os
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional, Union


class IPFormatType:
    """Constants for IP format types"""
    RANGE = "range"
    CIDR = "cidr"
    WILDCARD = "wildcard"
    ALL = "all"


class OutputFormatType:
    """Constants for output format types"""
    SIMPLE = "simple"
    BY_DATACENTER = "bydatacenter"
    ALL = "all"


class ZScalerCloud:
    """Constants for ZScaler cloud domains"""
    ZSCALER = "zscaler.net"
    ZSCALER_ONE = "zscalerone.net"
    ZSCALER_TWO = "zscalertwo.net"
    ZSCALER_THREE = "zscalerthree.net"
    ZSCLOUD = "zscloud.net"
    ZSCALER_BETA = "zscalerbeta.net"
    ZSCALER_GOV = "zscalergov.net"
    ZSCALER_TEN = "zscalerten.net"
    
    @classmethod
    def get_api_url(cls, cloud: str) -> str:
        """Get the API URL for a given cloud"""
        return f"https://config.zscaler.com/api/{cloud}/cenr/json"


def setup_argparse() -> argparse.ArgumentParser:
    """Set up and return the argument parser"""
    parser = argparse.ArgumentParser(
        prog="ZScaler Datacenter Config Extract Tool",
        description="This script pulls the configuration for the specified ZScaler datacenters. "
                    "Configuration can be done in the command-line or provided by a config file named 'config.ini'.",
        epilog="Although there are many safeguards to stop from the use of bad configs or errors, "
               "not all situations can be caught. If no output is provided, check the configuration "
               "and verify its accuracy."
    )
    
    parser.add_argument('-nocfg', '-noconfig', dest='no_config', action='store_true', 
                      help='Specifies if the present config file should be ignored if one is present.')
    parser.add_argument('-c', '-cloud', dest='cloud', type=str, 
                      help='Specifies ZScaler cloud that the data will be pulled for ex. "zscaler.net"')
    parser.add_argument('-r', '-regions', dest='regions', type=str, 
                      help='Specifies ZScaler regions, for the specified cloud, that will be used for the data pull. for ex."Americas,EMEA"')
    parser.add_argument('-d', '-datacenters', dest='datacenters', type=str, 
                      help='Specifies ZScaler datacenters for the specified cloud, that will be used for the data pull. ex. "Atlanta II,Atlanta III, Boston I"')
    parser.add_argument('-i', '-ipformat', dest='ipformat', type=str, 
                      help='Specifies the type of information pulled ex. "range", "cidr", "wildcard" or "all". '
                           'As a note "all" will print all information into a csv file available for further analysis.')
    parser.add_argument('-o', '-output_format', dest='output_format', type=str, 
                      help='Denotes the type of output "simple" will list all data without denoting location. '
                           '"bydatacenter" will give the data structured with the datacenter city as a label. '
                           '"All" ipformat will print as a CSV file.')
    parser.add_argument('-p', '-path', dest='path', type=dir_path, 
                      help=r'Specifies the directory path that should be used to deposit csv files. *Required for all/csv export*')
    
    return parser


def dir_path(string: str) -> str:
    """Validate if the string is a valid directory path"""
    if os.path.isdir(string):
        return string
    else:
        raise NotADirectoryError(string)


def clean_item(input_str: str) -> str:
    """Extract the value after the colon in a string"""
    clean_item = (str(input_str).split(' : '))[1]
    return clean_item


def ip_range(input_dict: Dict[str, str]) -> str:
    """Format IP range as 'first_usable - last_usable'"""
    first_usable = input_dict.get('first usable', '')
    last_usable = input_dict.get('last usable', '')
    usable_range = f"{first_usable} - {last_usable}"
    return usable_range


def print_values(requested: List[str]) -> None:
    """Print non-None values from a sorted list"""
    requested.sort()
    for item in requested:
        if 'None' not in item:
            print(item)


def read_config(config_file: str = 'config.ini') -> Dict[str, Any]:
    """Read configuration from config file"""
    config = configparser.ConfigParser()
    config.read(config_file)
    
    return {
        'cloud': config['Default']['Cloud'],
        'regions': config['Default']['Regions'].split(','),
        'datacenters': config['Default']['Datacenters'].split(','),
        'ipformat': config['Parameters']['IPType'].lower(),
        'output_format': config['Parameters']['Format'].lower(),
        'path': config['Parameters']['Path']
    }


def parse_arguments() -> Dict[str, Any]:
    """Parse command line arguments and config file"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Initialize configuration
    config = {}
    
    # Check if config file exists and should be used
    if os.path.exists('config.ini') and not args.no_config:
        config = read_config()
    elif args.cloud is None:
        exit(print('Config Error: ZScaler Cloud not specified'))
    elif all([args.cloud]) and (args.ipformat and args.ipformat.lower() == IPFormatType.ALL):
        config = {
            'cloud': args.cloud,
            'regions': args.regions.split(',') if args.regions else None,
            'datacenters': args.datacenters.split(',') if args.datacenters else None,
            'ipformat': IPFormatType.ALL,
            'output_format': OutputFormatType.ALL,
            'path': args.path
        }
    elif all([args.cloud, args.ipformat, args.output_format]):
        config = {
            'cloud': args.cloud,
            'regions': args.regions.split(',') if args.regions else None,
            'datacenters': args.datacenters.split(',') if args.datacenters else None,
            'ipformat': args.ipformat.lower(),
            'output_format': args.output_format.lower(),
            'path': args.path
        }
    else:
        exit(print('Config Error: Incomplete Command-Line arguments or incomplete config file. '
                  '** IPFormat or Output Format not defined ** '
                  '- verify config.ini or add parameters run --help for more info'))
    
    # Parameter Validation:
    if config['ipformat'] == IPFormatType.ALL and config['output_format'] != OutputFormatType.ALL:
        exit(print('Config Error: "All" data format only supports CSV export. '
                  'Define the directory path or file will be created in directory script is run from.'))
    
    return config


def fetch_zscaler_data(cloud: str) -> Dict[str, Any]:
    """Fetch data from ZScaler API for the specified cloud"""
    api_url = ZScalerCloud.get_api_url(cloud)
    response = requests.get(api_url)
    return json.loads(response.text)


def filter_data(data: Dict[str, Any], cloud: str, regions: Optional[List[str]], 
                datacenters: Optional[List[str]]) -> Dict[str, Any]:
    """Filter data by regions and datacenters"""
    if not any([regions, datacenters]):
        return data
    
    filtered_data = {cloud: {}}
    
    for region in data[cloud]:
        clean_region = clean_item(region)
        region_data = {}
        
        # Skip if regions is specified and current region is not in the list
        if regions and clean_region not in regions:
            continue
        
        for datacenter in data[cloud][region]:
            clean_dc = clean_item(datacenter)
            
            # Skip if datacenters is specified and current datacenter is not in the list
            if datacenters and clean_dc not in datacenters:
                continue
                
            region_data[datacenter] = data[cloud][region][datacenter]
            
        if region_data:
            filtered_data[cloud][region] = region_data
            
    return filtered_data


def process_ip_data(data: Dict[str, Any], cloud: str) -> Dict[str, Any]:
    """Process IP data to add usable ranges and wildcard masks"""
    for region in data[cloud]:
        for city in data[cloud][region]:
            location = data[cloud][region][city]
            
            for i, block in enumerate(location):
                cidr = block.get('range')
                if cidr:
                    # Calculate network information
                    network = ipaddress.ip_network(cidr)
                    first, last = network[1], network[-2]
                    
                    # Add first and last usable IPs
                    location[i]['first usable'] = str(first)
                    location[i]['last usable'] = str(last)
                    
                    # Calculate wildcard masks for IPv4
                    if first.version == 4:
                        wildcard = []
                        location[i]['wildcard'] = wildcard
                        
                        first_split = str(first).split('.')
                        last_split = str(last).split('.')
                        
                        # Add base wildcard
                        base_wildcard = f"{first_split[0]}.{first_split[1]}.{first_split[2]}.*"
                        wildcard.append(base_wildcard)
                        
                        # Add additional wildcards if needed
                        diff = int(last_split[2]) - int(first_split[2])
                        for j in range(diff, -1, -1):
                            new_wild = f"{first_split[0]}.{first_split[1]}.{str(int(first_split[2]) + j)}.*"
                            if new_wild not in wildcard:
                                wildcard.append(new_wild)
                                
                        wildcard.sort()
                        
    return data


def export_to_csv(data: Dict[str, Any], cloud: str, path: Optional[str] = None) -> str:
    """Export all data to CSV format"""
    if path:
        dir_path(path)
        filename = os.path.join(path, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv")
    else:
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    
    fieldnames = [
        'ZScaler Cloud', 'Region', 'City', 'CIDR', 'VPN', 'GRE', 
        'Hostname', 'Latitude', 'Longitude', 'First IP', 'Last IP', 'Wildcard'
    ]
    
    with open(filename, mode='w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, quotechar="'")
        csvwriter.writerow(fieldnames)
        
        for region in data[cloud]:
            for datacenter in data[cloud][region]:
                for i, item in enumerate(data[cloud][region][datacenter]):
                    # Prepare wildcard string if exists
                    wildcards = item.get('wildcard')
                    wildcard_str = '-'.join(wildcards) if wildcards else ''
                    
                    new_row = [
                        cloud, 
                        clean_item(region), 
                        clean_item(datacenter), 
                        item.get('range', ''), 
                        item.get('vpn', ''), 
                        item.get('gre', ''), 
                        item.get('hostname', ''), 
                        item.get('latitude', ''), 
                        item.get('longitude', ''), 
                        item.get('first usable', ''), 
                        item.get('last usable', ''), 
                        wildcard_str
                    ]
                    
                    csvwriter.writerow(new_row)
    
    return filename


def output_simple_format(data: Dict[str, Any], cloud: str, ipformat: str) -> None:
    """Output data in simple format"""
    if ipformat == IPFormatType.WILDCARD:
        simple_wildcard = []
        for region in data[cloud]:
            for datacenter in data[cloud][region]:
                for i, item in enumerate(data[cloud][region][datacenter]):
                    wildcards = item.get('wildcard')
                    if wildcards:
                        first_usable = item.get('first usable')
                        if first_usable and ipaddress.ip_address(first_usable).version == 4:
                            for wildcard_ip in wildcards:
                                if wildcard_ip not in simple_wildcard:
                                    simple_wildcard.append(wildcard_ip)
        
        print_values(simple_wildcard)
        
    elif ipformat == IPFormatType.RANGE:
        ranges = []
        for region in data[cloud]:
            for datacenter in data[cloud][region]:
                for item in data[cloud][region][datacenter]:
                    range_str = ip_range(item)
                    if range_str not in ranges:
                        ranges.append(range_str)
                        
        print_values(ranges)
        
    elif ipformat == IPFormatType.CIDR:
        cidr_list = []
        for region in data[cloud]:
            for datacenter in data[cloud][region]:
                for item in data[cloud][region][datacenter]:
                    cidr = item.get('range')
                    if cidr and cidr not in cidr_list:
                        cidr_list.append(cidr)
                        
        print_values(cidr_list)


def output_by_datacenter(data: Dict[str, Any], cloud: str, ipformat: str) -> None:
    """Output data organized by datacenter"""
    for region in data[cloud]:
        if data[cloud][region]:
            print(clean_item(region))
            
        for datacenter in data[cloud][region]:
            print(clean_item(datacenter))
            
            if ipformat == IPFormatType.WILDCARD:
                simple_wildcard = []
                for i, item in enumerate(data[cloud][region][datacenter]):
                    wildcards = item.get('wildcard')
                    if wildcards:
                        first_usable = item.get('first usable')
                        if first_usable and ipaddress.ip_address(first_usable).version == 4:
                            for wildcard_ip in wildcards:
                                if wildcard_ip not in simple_wildcard:
                                    simple_wildcard.append(wildcard_ip)
                
                print_values(simple_wildcard)
                
            elif ipformat == IPFormatType.RANGE:
                ranges = []
                for item in data[cloud][region][datacenter]:
                    range_str = ip_range(item)
                    if range_str not in ranges:
                        ranges.append(range_str)
                
                print_values(ranges)
                
            elif ipformat == IPFormatType.CIDR:
                cidr_list = []
                for item in data[cloud][region][datacenter]:
                    cidr = item.get('range')
                    if cidr and cidr not in cidr_list:
                        cidr_list.append(cidr)
                
                print_values(cidr_list)


def main() -> None:
    """Main function to run the script"""
    # Parse arguments
    config = parse_arguments()
    
    # Fetch data
    data = fetch_zscaler_data(config['cloud'])
    
    # Filter data
    data = filter_data(data, config['cloud'], config['regions'], config['datacenters'])
    
    # Process IP data
    data = process_ip_data(data, config['cloud'])
    
    # Output data
    ipformat = config['ipformat']
    output_format = config['output_format']
    
    if ipformat == IPFormatType.ALL:
        filename = export_to_csv(data, config['cloud'], config['path'])
        print(f'CSV file written to: {filename}')
    elif output_format == OutputFormatType.SIMPLE:
        output_simple_format(data, config['cloud'], ipformat)
    elif output_format == OutputFormatType.BY_DATACENTER:
        output_by_datacenter(data, config['cloud'], ipformat)
    else:
        exit(print(
            'Configuration Error: IPFormat, Output Format, or Path not specified. '
            '** Path is only applicable if IPFormat and Output Format are "All".** '
            'Run -h for help.'
        ))


if __name__ == "__main__":
    main()
