import xml.etree.ElementTree as ET
import pandas as pd
import json

# Substitutions = {
#     "Waste Pump" : "WP",
#     "Contactor" : "CT",
#     "Valve" : "V"
    
# }


class Node:
    def __init__(self, node_name: str='', part_name: str='', is_external: bool=False):
        self.node_name = node_name
        self.part_name = part_name
        self.is_external = is_external
        self.net_name = ''
    def __repr__(self):
        return self.node_name
    def __dict__(self):
        return {
            "Node Name" : self.node_name,
            "Part Name" : self.part_name,
            "Is External" : self.is_external,
            "Net Name" : self.net_name
        }



class Net:
    def __init__(self, net_name):
        self.net_name = net_name
        
        self.nodes: list[Node] = []
        self.contains_ext_connection = False
        self.type = ''
    def get_node_count(self):
        return len(self.nodes)
    def add_node(self, node: Node):
        self.nodes.append(node)
        if node.is_external:
            self.contains_ext_connection = True
    def __repr__(self):
        return self.net_name
    def __dict__(self):
        self_dict = {}
        for node in self.nodes:
            self_dict[node.node_name] = node.__dict__()
        
        return self_dict
    
def get_nets(filename: str):
    tree = ET.parse(filename)
    root = tree.getroot()


    nets: dict[str, Net] = {}


    diode_subs = {
        "A" : "-",
        "C" : "+"
    }

    # Iterate over nets
    for net_ele in root:
        newNet = Net(f'N{len(nets)}')
        
        if net_ele.tag != "net":
            continue
        net_name_priority = 0
        type_priority = 0
        newNet.type = "Interconnection"
        NC_flag = False
        for connector in net_ele:
            newNode = Node()
            
            part = connector[0]
            part_type = part.get("title")
            part_name = part.get("label")
            node_name = part_name
            connector_name = connector.get("name")
            if part_name == "NC" or connector_name == "NC":
                NC_flag = True
                break
            match part_type:
                case "Net Label":
                    newNode.is_external = True
                    node_name+=(" EXT")
                    if net_name_priority < 4 and "PSU" in part_name:
                        newNet.net_name = part_name
                        net_name_priority = 4                        
                    if net_name_priority < 3:
                        newNet.net_name = part_name
                        net_name_priority = 3
                    
                    if type_priority < 2 and "PSU" in part_name:
                        newNet.type = part_name
                        type_priority = 2
        
                    if type_priority < 1:
                        newNet.type = "Logical Output"
                        type_priority = 1
                case "Micro 850":
                    part_name = "PLC"
                    node_name = f"PLC {connector_name}"
                    
                    if net_name_priority < 2:
                        newNet.net_name = node_name   
                        net_name_priority = 2
                        
                    
                    if type_priority < 3:
                        if connector_name[:2] == 'O-':
                            newNet.type = "PLC Output"
                        elif connector_name[:2] == 'I-':
                            newNet.type = "PLC Input"
                        type_priority = 3
                case "DPDT Relay":
                    node_name+=(f" P{connector_name}")
                    if net_name_priority < 1:
                        newNet.net_name = node_name
                        net_name_priority = 1
                case "Diode":
                    node_name+=(f" {diode_subs[connector_name]}")
                    if net_name_priority == 0:
                        newNet.net_name = node_name 
                        
            
            if NC_flag:
                NC_flag = False
                continue   
            
            newNode.node_name=node_name
            newNode.part_name = part_name
            newNode.net_name = newNet.net_name
            newNet.add_node(newNode)
        if len(newNet.nodes) > 1:
            nets[newNet.net_name] = newNet
            
            
    return nets



def get_net_row(net: Net):
    return 

class NetEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__()

if __name__ == "__main__":
    filename = "PLC_Diag_two_valve_netlist_2.xml"
    nets = get_nets(filename)
    
    net_column_labels = [ "Net Name", "# Nodes", "External?", "Type"  ]
    
    
    net_row_list = []
    
    for net in nets.values():
        data = [net.net_name, len(net.nodes), net.contains_ext_connection, net.type]
        net_row_list.append(data)
    
    net_df = pd.DataFrame(data=net_row_list, columns=net_column_labels)
        
        
    net_df.to_csv(filename[:-4] + ".csv")
    
    with open(filename[:-4]+"_nets.json", '+w') as jsf:
        json.dump(nets, jsf, cls = NetEncoder)
    