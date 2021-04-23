import json
import os
import sys
from pprint import pprint
from os import getenv
import paramiko
from graphviz import Graph
from paramiko import AutoAddPolicy


def get_hosts():
    """
    read the host file and create a list of hosts to connect to
    :return:
    """
    host_list = []
    if not os.path.exists('hosts.txt'):
        print("hosts.txt file missing in current directory. Please create the file and populate the host details")
        sys.exit()
    with open('hosts.txt', 'r') as file_handle:
        for host_val in file_handle.readlines():
            host_list.append(host_val.strip())
    if len(host_list) < 1:
        print("Hosts file is empty, please populate the file and try again")
        sys.exit()
    return host_list


def run_ssh_command(hostname=None):
    """
    runs the ssh command to get the connection information from the cumulus node
    :return:
    """
    if not hostname:
        print(" Hostname must be specified ")
        sys.exit()
    username = getenv('SSHUSER')
    if not username:
        username = 'cumulus'
    password = getenv('SSHPASS')
    if not password:
        print("Password is a necessary parameter. Add the password as an environment variable called SSHPASS")
        sys.exit()
    ssh_client = paramiko.client.SSHClient()
    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
    ssh_client.connect(hostname=hostname, username=username, password=password, look_for_keys=False)
    stdin, stdout, stderr = ssh_client.exec_command('net show interface json')
    output = stdout.read().decode("utf-8")
    output_json = json.loads(output)
    stdin.close()
    stdout.close()
    stderr.close()
    ssh_client.close()
    return output_json


def build_adjacency_data(hosts_data):
    """
    filter the interfaces data to extract relevant adjacency data for each interface on each host
    :param hosts_data:
    :return:
    """
    adjacency_data = {}
    ip_hostname_mapping = {}
    for host in hosts_data:
        host_data = hosts_data[host]
        adjacency_data[host] = {}
        adjacency_data[host]["interfaces"] = {}
        for interface in host_data:
            interface_data = host_data[interface]
            if interface_data['iface_obj']['lldp']:
                adjacency_data[host]['interfaces'][interface] = {}
                lldp_data = interface_data['iface_obj']['lldp'][0]
                connected_ip = lldp_data['adj_mgmt_ip4']
                connected_hostname = lldp_data['adj_hostname']
                ip_hostname_mapping[connected_ip] = connected_hostname
                adjacency_data[host]['interfaces'][interface]['connected_hostname'] = connected_hostname
                adjacency_data[host]['interfaces'][interface]['connected_ip'] = connected_ip
                adjacency_data[host]['interfaces'][interface]['connected_port'] = lldp_data['adj_port']
    # Populate the records with the discovered hostnames
    for host in adjacency_data:
        adjacency_data[host]['hostname'] = ip_hostname_mapping[host]
    return adjacency_data


def build_graph(hosts_data: dict = None, output_file: str = 'network-diagram'):
    """
    create the network diagram from the data in the hosts_data dictionary
    :param hosts_data: dict object of data containing the details of the hosts and interface connections
    :param output_file: output file path for saving the image
    :return:
    """
    graph_attributes = {'pad': "0.7", 'ranksep': "0.925", 'nodesep': "5"}
    dot = Graph(comment="test Graph", strict=True, graph_attr=graph_attributes, format='png')
    edges = []
    for host in hosts_data:
        hostname = hosts_data[host]['hostname']
        dot.node(name=hostname, label=hostname, shape='box')
    for host in hosts_data:
        hostname = hosts_data[host]['hostname']
        for interface in hosts_data[host]['interfaces']:
            interface_data = hosts_data[host]['interfaces'][interface]
            edge = (
                interface_data['connected_hostname'] + ":" + interface_data["connected_port"],
                hostname + ":" + interface)
            edge_exists = False
            for existing_edge in edges:
                if (edge[0] == existing_edge[0] and edge[1] == existing_edge[1]) or (
                        edge[0] == existing_edge[1] and edge[1] == existing_edge[0]):
                    edge_exists = True
            if not edge_exists:
                edges.append(edge)
    for edge in edges:
        print(edge)
        head_hostname, head_port = edge[0].split(":")
        tail_hostname, tail_port = edge[1].split(":")
        dot.edge(head_name=head_hostname, tail_name=tail_hostname, headlabel=head_port, taillabel=tail_port)
    dot.render(filename=output_file)


if __name__ == '__main__':
    hosts_dict = {}
    hosts_list = get_hosts()
    print(f"List of hosts provided: {hosts_list}")
    for host_ip in hosts_list:
        hosts_dict[host_ip] = run_ssh_command(host_ip)
    adjacency_graph = build_adjacency_data(hosts_data=hosts_dict)
    print("Adjacency Data:")
    pprint(adjacency_graph)
    build_graph(adjacency_graph)
