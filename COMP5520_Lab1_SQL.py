# William Doyle
# COMP.5520-201 Foundations in Digital Health
# Lab #1
# Due 2/15/23

# Lab #1 - UMLS
# Find and print the first three circles with at least 3 and less than 40 nodes.

# Credit to Prof. Hong Yu and Prof. Weisong Liu as the following GitHub repo was used as a base for this program:
# https://github.com/uml-digital-health/Labs

# -------
# Imports
# -------
import mysql.connector
import pprint
import numpy as np

# -----------------
# UML DB Connection
# -----------------
conn = mysql.connector.connect(host="172.16.34.1", port="3307", user="umls", password="umls", database="umls2022")
cur = conn.cursor()

# ------------------
# DB Query Functions
# ------------------
# run_query(cur, query)
# Takes cursor and SQL string input and prints results of SQL query/command.
def run_query(cur, query):
    cur.execute(query)
    query_result = cur.fetchall()
    col_names = [ col[0] for col in cur.description]
    pprint.pprint(col_names)
    pprint.pprint(query_result)

# run_query_return(cur, query)
# Modified version of run_query() that returns the result as a string instead of printing.
def run_query_return(cur, query):
    cur.execute(query)
    query_result = cur.fetchall()
    col_names = [ col[0] for col in cur.description]
    return(query_result)

# find_relation(cui, relation)
# Takes CUI and relation (PAR, CHD) as a string input and returns SQL query to find parents as a string.
def find_relation(cui, relation):
	return """
	select *
	  from MRREL 
	  where 
		CUI1='"""+cui+"""'  
		and REL='"""+relation+"""' 
		and SAB='SNOMEDCT_US';
	"""

# recursive_child(cui, depth)
# Takes CUI as a string input and depth as string-typecasted integer input and returns recursively list of children up to depth. Needs direct child CUI as integer input to start recursive branch.
def recursive_child(cui, depth, childcui):
	return """ with recursive cui_node (n, CUI1, CUI2, path_info) as (
   select 0 as n, CUI1 as CUI1, CUI2 as CUI2, 
   cast(concat('"""+cui+""",', CUI2) as char(200)) as path_info
   from MRREL
   where CUI1='"""+cui+"""'
    and
    SAB='SNOMEDCT_US'
    AND
    REL='CHD'
    AND
    CUI1<>CUI2
   union all
   select n+1, p.CUI1, p.CUI2, concat(path_info, ',', p.CUI2) as path_info
   from MRREL p
   inner join cui_node
     on p.CUI1=cui_node.CUI2
   where p.REL='CHD'
    and
    SAB='SNOMEDCT_US'
    and 
    n < """+depth+"""
    AND
    p.CUI1<>p.CUI2
	 )
	select distinct a.*, b.str 
	FROM cui_node a
	  join MRCONSO b
		on a.CUI2=b.CUI
	WHERE
	  b.SAB='MTH'
	  AND
	  b.LAT='ENG'
	  and
	  a.path_info like '%"""+childcui+"""%'
	;"""

# direct_child(cur, cui)
# Takes CUI as string and returns numpy array of each direct child's CUI, if any.
def direct_child(cur, cui):
	children = np.array(run_query_return(cur, find_relation(cui, "CHD")))
	if(len(children) > 0):
		return np.unique(children[:,4])
	return 0

# direct_parent(cur, cui)
# Takes CUI as string and returns numpy array of each direct parent's CUI, if any.
def direct_parent(cur, cui):
	parents = np.array(run_query_return(cur, find_relation(cui, "PAR")))
	if(len(parents) > 0):
		return np.unique(parents[:,4])
	return 0

# ------------------------------
# Data Loading and Preprocessing
# ------------------------------
LIMIT = "1000"
# grabs first LIMIT non-repeated CUI1 values from the table and formats them
cuiList = np.array(run_query_return(cur, "SELECT DISTINCT CUI1 FROM MRREL LIMIT "+LIMIT+";")).flatten() 

# offset the starting point (to make running this program multiple times easier)
START = 210
cuiList = cuiList[START:]

# -------------------
# Main Iterative Loop
# -------------------
DEPTH = "10" # maximum depth for recursively finding hierarchal relationships (MAXIMUM OF 40)
FILE = "chain.txt" # name of file to write chains to

for i in range(len(cuiList)): # iterate through every CUI, within the limit defined above
	print("Node: ",i+1," / ",len(cuiList)," (",cuiList[i],")")
	directChildren = direct_child(cur, cuiList[i]) # get a list of direct children
	directParents = direct_parent(cur, cuiList[i])

	if((type(directChildren) is int) or (type(directParents) is int)): # checks to make sure the node has parents and children (so that it is possible to be a circle)
		print("\tERR: No parents/children")
		continue

	for j in range(len(directChildren)): # find list of recursive children, starting with each direct child, up to DEPTH defined above
		recursiveChildren = np.array(run_query_return(cur, recursive_child(cuiList[i], DEPTH, directChildren[j])))
			
		if(len(recursiveChildren) > 0): # make sure that there are recursive children (grandchildren & further)
			recursiveChildren = np.char.split(recursiveChildren, sep=',')
			chain = recursiveChildren[:,3] # gets the path of CUIs
		
			print("\tChild: ",j+1," / ",len(directChildren)," (",directChildren[j],")")

			try:
				print("\t\tChain...")
				for k in range(len(chain)): # iterate thru every chain
					print("\t\t\t(",k+1," / ",len(chain),")")
					flag = 0 # flips to 1 if circle has been found
					if(len(chain[k]) >= 3): # ensure minimum chain length of 3
						for l in range(2, len(chain[k])):
							if(chain[k][l] == chain[k][0]): # if element in the chain is equal to starting element
								raise MATCH # no need to check rest of the chain once match is found, break out and print

			except: # open and close file each time in case there's an error that crashes the program
				f = open(FILE, "a")
				f.write(str(chain[k]))
				f.write("\n")
				f.close() 

# end DB connection
conn.close()