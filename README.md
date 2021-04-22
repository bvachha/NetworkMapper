# Network Mapper 
This project is a small piece of python scripting that can be used to
generate a network graph from network devices running cumulus. It has been tested on 
a gns3 simulation with cumulus 4.3.0 virtual appliances.

## Methodology
The cumulus devices, once connected, use LLDP out of the box to get network information of the devices directly connected to 
its ports. The tool will basically pull this information from the appliances over SSH and then generate the map.

