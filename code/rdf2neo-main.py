__author__ = 'ktuser'

from rdf2neo import Rdf2neo
from OntologyBackbone import OntologyBackbone
from rdflib import Graph
import os, sys
import logging
from neo4jconnector import *
import json

FORMAT = '[%(asctime)-15s] %(levelname)s: %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)

requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

neoserver = "http://172.20.0.137:7474"


def main():

    #  neo_graph.clean_graph()

    #-----Neo4j Server setup
    logger.info("Setting up fulltex indexing in Neo4j")
    fulltext_setup(neoserver=neoserver)

    #-----Preliminaries----------------------------------------------------------------------------------------------
    logger.info("Preliminaries (labels)")
    ontology_files = [r"..\data\DBpedia\dbpedia_2014.rdf", r"..\data\DBpedia\schema.rdfs.org_all.nt"]
    ob = OntologyBackbone(ontology_files)

    neo_graph = Rdf2neo(neoserver, graph_name="SimpolKnowledgeBase")
    logger.info("Adding labels")
    neo_graph.labels_to_neo(["foaf_Person", "schema_Person"])
    neo_graph.labels_to_neo(["foaf_Organization", "reegle_ProjectOutput", "geonames_Feature", "reegle_CountryProfile", "reegle_Sector", "reegle_Technology", "w3_Resource", "reegle_Specialisation", "w3_Concept"])
    neo_graph.labels_to_neo(["twitter_UserProfile"])
    neo_graph.labels_to_neo(["news_Entity", "news_Source"])
    neo_graph.labels_to_neo(ob.get_all_labels())
    neo_graph.labels_to_neo(ob.get_all_labels("http://schema.org/Thing"))

    #------Main insert -----------------------------------------------------------------------------------------------

    #sample_dbpedia2neo(neoserver=neoserver)
    dbpedia2neo(neoserver=neoserver)
    reegle2neo(neoserver=neoserver)

    #------Simpol Knowledge base specifics----------------------------------------------------------------------------
    logger.info("Insert metadata hierarchy and set subgraph properties")
    neo_graph = Rdf2neo(neoserver, graph_name="SimpolKnowledgeBase")
    insert_graph_hierarchy(neoserver=neoserver)
    #neo_graph.graph_properties_to_neo(graph_name="DBpedia_sample", author="Petra", description="Test sample DBpedia 3.9 data, from Wikipedia dump April 2013", email="Petra.Kralj.Novak@ijs.si")
    neo_graph.graph_properties_to_neo(graph_name="DBpedia", author="Petra", description="DBpedia 3.9 data, from Wikipedia dump April 2013", email="Petra.Kralj.Novak@ijs.si")
    neo_graph.graph_properties_to_neo(graph_name="reegle", author="Petra", description="reegle, from www.reegle.info, latest snapshot June 2014", email="Petra.Kralj.Novak@ijs.si")


def fulltext_setup(neoserver="http://localhost:7474"):
    logger.info("To setup fulltext index in Neo4j version 2.1.3 on node property 'name':")
    logger.info("1. edit neo4j.properties and add (uncomment) the following lines")
    logger.info("   node_auto_indexing=true ")
    logger.info("   node_keys_indexable=name ")
    logger.info("2. restart the neo4j service")
    logger.info("3. if this does not work, also delete the graph.db folder (when service is stopped) -- this will delete all your data")
    lucene_setup = {
      "name": "node_auto_index",
      "config": {
        "type": "fulltext",
        "provider": "lucene"
      }
    }
    headers = {'content-type': 'application/json'}
    try:
        r = requests.post(neoserver+"/db/data/index/node/", data=json.dumps(lucene_setup), headers=headers)
        logger.info("Fulltext setup response:\n%s" % r.text)
    except Exception as e:
        logger.exception("Error setting up fulltext index with parameters %s \n %s" % (lucene_setup, e))




def sample_dbpedia2neo(neoserver="http://localhost:7474"):
    logger.info("Inserting sample dbpedia")
    neo_graph = Rdf2neo(neoserver, graph_name="DBpedia_sample", bulk_size=10000)
    file_names = [r"..\data\DBpedia\dbpedia-properties-sample.nt",
                  r"..\data\DBpedia\dbpedia-instance_types_en-sample.nt"]
    file_name_mapping = r"..\data\DBpedia\dbpedia2014-lod2neo.n3 "

    logger.info("Loading the main data")
    logger.info("Reading the data with RdfLib ...")
    memg = Graph()
    for file_name in file_names:
        logger.debug("Reading file " + file_name)
        name, extension = os.path.splitext(file_name)
        memg.parse(file_name, format=extension[1:])
    logger.debug("The RDF graph has %s statements." % len(memg))
    logger.debug("Reading the RDF mapping file " + file_name_mapping)
    memg.parse(file_name_mapping, format='n3')
    logger.debug("The RDF graph has %s statements." % len(memg))

    logger.info("rdf2neo main insert")
    neo_graph.to_neo4j(memg)


def dbpedia2neo(neoserver="http://localhost:7474"):
    logger.info("Inserting dbpedia")
    neo_graph = Rdf2neo(neoserver, graph_name="DBpedia", bulk_size=10000)

    file_names = [r"..\data\DBpedia\instance_types_en.nt",
                  r"..\data\DBpedia\mappingbased_properties_cleaned_en.nt",
                  r"..\data\DBpedia\homepages_en.nt"]

    file_name_mapping = r"..\data\DBpedia\dbpedia2014-lod2neo.n3 "


    logger.info("Loading the main data")
    logger.info("Reading the data with RdfLib ...")
    memg = Graph()
    for file_name in file_names:
        logger.debug("Reading file " + file_name)
        name, extension = os.path.splitext(file_name)
        logger.info("reading file %s %s" % (file_name, extension[1:]))
        memg.parse(file_name, format=extension[1:])
    logger.debug("The RDF graph has %s statements." % len(memg))
    logger.debug("Reading the RDF mapping file " + file_name_mapping)
    memg.parse(file_name_mapping, format='n3')
    logger.debug("The RDF graph has %s statements." % len(memg))

    #-------------------------------------------------------------------------------------------------

    logger.info("rdf2neo main insert")
    neo_graph.to_neo4j(memg)


def reegle2neo(neoserver="http://localhost:7474"):
    logger.info("Inserting reegle")
    neo_graph = Rdf2neo(neoserver, graph_name="reegle", bulk_size=5000)
    logger.info("Reading data files ...")
    file_names = [r"..\data\reegle\latest_reegle_dump.nt",
                  r"..\data\reegle\reegle_lod_links.nt"]
    file_name_mapping = r"..\data\reegle\reegle-lod2neo.n3"

    logger.info("Loading the main data")
    logger.info("Reading the data with RdfLib ...")
    memg = Graph()
    for file_name in file_names:
        logger.debug("Reading file " + file_name)
        name, extension = os.path.splitext(file_name)
        memg.parse(file_name, format=extension[1:])
    logger.debug("The RDF graph has %s statements." % len(memg))
    logger.debug("Reading the RDF mapping file " + file_name_mapping)
    memg.parse(file_name_mapping, format='n3')
    logger.debug("The RDF graph has %s statements." % len(memg))

    #-------------------------------------------------------------------------------------------------

    logger.info("rdf2neo main insert")
    neo_graph.to_neo4j(memg)


def insert_graph_hierarchy(neoserver="http://localhost:7474"):  # add *args
    neo_graph = BaseNeo4jConnector(neoserver+"/db/data/transaction")
    logger.info("Creating constraints")
    statements = []
    try:
        statements.append("CREATE CONSTRAINT ON (m:`__SubgraphMetaData`) ASSERT m.uri IS UNIQUE")
        neo_graph.queryd(statements)
        neo_graph.commitTx()
    except:
        logger.warn("Failed to build index on :`__SubgraphMetaData`(uri)", sys.exc_info()[:2])
    try:
        statements.append("CREATE CONSTRAINT ON (n:`_Graph`) ASSERT n.uri IS UNIQUE")
        neo_graph.queryd(statements)
        neo_graph.commitTx()
    except:
        logger.warn("Failed to build index on :`_Graph`(uri)", sys.exc_info()[:2])

    logger.info("Inserting meta nodes")

    statements = []
    # Graph
    details = {"uri": "http://simpol.ijs.si/lod2graph#Graph",
          "name": "_Graph",
          "description": "Simpol Knowledge Base."}
    statements.append(["CREATE (n:`__SubgraphMetaData` {kw}) RETURN id(n) as nid", dict(kw=details)])

    # LOD
    details = {'uri': "http://simpol.ijs.si/lod2graph#LOD",
          'name': "_LOD",
          'description': "Linked Open Data (LOD)."}
    statements.append(["CREATE (n:`__SubgraphMetaData` {kw}) RETURN id(n) as nid",  dict(kw=details)])

    # Twitter
    details = {'uri': "http://simpol.ijs.si/lod2graph#Twitter",
          'name': "_Twitter",
          'description': "Graph from Twitter."}
    statements.append(["CREATE (n:`__SubgraphMetaData` {kw}) RETURN id(n) as nid",  dict(kw=details)])

    # Project
    details = {'uri': "http://simpol.ijs.si/lod2graph#Project",
          'name': "_Project",
          'description': "Internal SIMPOL Project data source."}
    statements.append(["CREATE (n:`__SubgraphMetaData` {kw}) RETURN id(n) as nid", dict(kw=details)])

    # Crowdsourcing
    details = {'uri': "http://simpol.ijs.si/lod2graph#Crowdsourcing",
          'name': "_Crowdsourcing",
          'description': "Crowdsourced graph."}
    statements.append(["CREATE (n:`__SubgraphMetaData` {kw}) RETURN id(n) as nid", dict(kw=details)])

    # News
    details = {'uri': "http://simpol.ijs.si/lod2graph#News",
          'name': "_News",
          'description': "Graph from news and blogs."}
    statements.append(["CREATE (n:`__SubgraphMetaData` {kw}) RETURN id(n) as nid", dict(kw=details)])

    neo_graph.queryd(statements)
    neo_graph.commitTx()

    logger.info("Inserting relations between meta nodes (the subgraph hierarchy)")
    pairs = [('http://simpol.ijs.si/lod2graph#Graph',	 'http://simpol.ijs.si/lod2graph#LOD'),
             ('http://simpol.ijs.si/lod2graph#Graph', 	 'http://simpol.ijs.si/lod2graph#Twitter'),
             ('http://simpol.ijs.si/lod2graph#Graph',	 'http://simpol.ijs.si/lod2graph#Project'),
             ('http://simpol.ijs.si/lod2graph#Graph', 	 'http://simpol.ijs.si/lod2graph#Crowdsourcing'),
             ('http://simpol.ijs.si/lod2graph#Graph', 	 'http://simpol.ijs.si/lod2graph#News')]

    statements = []
    for n, m in pairs:
        statements.append("MATCH (n:`__SubgraphMetaData`),(m:`__SubgraphMetaData`) "
                          "WHERE n.uri ='" + n + "' and m.uri = '" + m + "' MERGE (n)<-[:_subgraph]-(m)")
    neo_graph.queryd(statements)
    neo_graph.commitTx()

if __name__ == "__main__":
    main()

