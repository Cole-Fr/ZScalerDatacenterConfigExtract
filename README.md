# ZScalerDatacenterConfigExtract
Tool that will pull and enhance the configuration of specified ZScaler clouds, regions, and datacenters. 

Configuration: 
The script pulls configuration either by config file stored as a config.ini in the same directory or as command-line arguments given at time of execution of the script. This configuration will specify key parameters although not all are required. 

Required Fields: 
- Cloud - Uses the cloudname to identify where to pull information from. ex. 'zscaler.net' 
- IPType - defines the requested material.
    - CIDR or cidr - Returns CIDR for the datacenter. ex. 136.226.116.0/23
    - Range or range - Returns the range of IPs that could be seen. ex. '136.226.82.1 - 136.226.83.254'
    - Wildcard - Returns IPv4 wildcard IPs for the specified resources. ex. '136.226.83.*'
    - All - Returns all information structured in CSV format. By default the file will be created with the date and time in the directory the script was ran from unless 'path' is specified. 
- Format - Returns data in the requested format.
    - Simple or simple - Prints the values and does not specify the origin.
    - ByDatacenter or bydatacenter - Prints the name of the Region then Datacenter then the requested information.

 Optional Fields:
- Regions - Identifies the Regions to pull the data from. ex 'Americas,EMEA'
- Datacenters - Identifies the Datacenters to pull the data from. ex 'Atlanta II,Boston I,Abu Dhabi II'
- Path - Denotes the directory that the CSV from an 'All' data extract will be deposited.

Configuration File Syntax:
Below shows the syntax for the config.ini file that can be used for regular or complex extracts. 

[Default]
Cloud = *Specify ZScaler Cloud*
Regions = *Specify the regions in the ZScaler Cloud information is requested for, blank will return all regions.*
Datacenters = *Specify Datacenters information is requested for, blank will return all in the datacenters.*

[Parameters]
IPType = *Denotes the requested information.*
Format = *Denotes how the data should be output*
Path: *Specifies the directory that should be used for CSV export - only applicable for "All" data exports*

