from Bio import Phylo
import numpy as np
import tqdm as tqdm
import random
import pandas as pd
import math
from collections import defaultdict
import tree_pb2
import gzip



tree = Phylo.read(gzip.open("public-latest.all.nwk.gz","rt"), "newick")
tree.ladderize()
root=tree.clade
from collections import defaultdict
by_level = defaultdict(list)


def assign_x(tree, current_branch_length=0, current_level=0):
    
    by_level[current_level].append(tree)
    tree.x = current_branch_length
    if tree.branch_length :
        current_branch_length = current_branch_length + tree.branch_length
    current_level+=1
    
    for clade in tree.clades:
        assign_x(clade,current_branch_length,current_level)


def assign_terminal_y(terminals):
    for i,node in enumerate(terminals):
        node.y=i
    

def align_parents(tree_by_level):
    for level in tqdm.tqdm(sorted( list(by_level.keys()), reverse=True)):
        for node in by_level[level]:
            childrens_y = [item.y for item in node.clades]
            if len(childrens_y):
                node.y=np.mean(childrens_y)

assign_x(root)
terminals = root.get_terminals()
assign_terminal_y(terminals)
align_parents(by_level)

all_nodes= terminals
all_nodes.extend(root.get_nonterminals())
all_nodes.sort(key=lambda x: x.y)
lookup = {x:i for i,x in enumerate(all_nodes)}

def add_paths(tree_by_level):
    for level in tqdm.tqdm(sorted( list(by_level.keys()))):
        for node in by_level[level]:
            this_node_id = lookup[node]
            for clade in node.clades:
                clade.path_list = node.path_list + [this_node_id,]
root.path_list = []
add_paths(by_level)





genotypes = defaultdict(list)

for line in tqdm.tqdm(open("out.txt")):
    cols = line.split("\t")
    cols[4]=cols[4].strip()
    name = cols[0]#.split("|")[0]
    if(cols[4]):
        genotypes[name].append(cols[4])


metadata = pd.read_csv("public-latest.metadata.tsv.gz",sep="\t")
lineage_lookup = defaultdict(lambda: "unknown")
date_lookup = defaultdict(lambda: "unknown")
country_lookup = defaultdict(lambda: "unknown")
for i,row in  tqdm.tqdm(metadata.iterrows()):
    name = row['strain']#.split("|")[0]
    lineage_lookup[name] = row['pangolin_lineage']
    date_lookup[name] = row['date']
    row['country']=str(row['country'])
    if row['country']=="UK":
        country_lookup[name] = row['strain'].split("/")[0]
    elif "Germany" in row['country']:
        country_lookup[name] = "Germany"
    elif "Austria" in row['country']:
        country_lookup[name] = "Austria"
    elif "USA" in row['country']:
        country_lookup[name] = "USA"
    else:
        country_lookup[name] = row['country']
    

def make_mapping(list_of_strings):
    sorted_by_value_counts = pd.Series(list_of_strings).value_counts(sort=True).index.tolist()
    return sorted_by_value_counts, {x:i for i,x in enumerate(sorted_by_value_counts)}



def make_node(x):
    parents = x.path_list[::-1]
    if len(parents)>0:
        return tree_pb2.Node(name=x.name,x=0.2*x.x,y=x.y/40000,parent=parents[0])
    else:
        return tree_pb2.Node(name=x.name,x=0.2*x.x,y=x.y/40000)

pb_list = [make_node(x) for i,x in tqdm.tqdm(enumerate(all_nodes))]
node_list = tree_pb2.NodeList(nodes=pb_list)
node_list.SerializeToString()

f = open("../public/nodelist.pb", "wb")
f.write(node_list.SerializeToString())
f.close()


metadata = [tree_pb2.MetadataItem(name=str(x.name),lineage=str(lineage_lookup[x.name]),date=str(date_lookup[x.name]),country=str(country_lookup[x.name]),aa_subs=genotypes[x.name])  for i,x in tqdm.tqdm(enumerate(all_nodes))]

metadata =tree_pb2.MetadataList(items=metadata)

f = open("../public/metadata.pb", "wb")
f.write(metadata.SerializeToString())
f.close()
