"""
Class to loads LOD files to neo4j.

"""

import os
from rdflib import Namespace, Graph, util
from rdflib.namespace import RDFS, RDF
from neo4jconnector import *
import time
import datetime
from node import *
from OntologyBackbone import OntologyBackbone, uri2short

FORMAT = '[%(asctime)-15s] %(levelname)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)


namespace = Namespace("http://simpol.ijs.si/lod2graph#")


class Rdf2neo:
    def __init__(self, neo4j_connection_string, graph_name, bulk_size=1000):
        self.g = BaseNeo4jConnector(neo4j_connection_string+"/db/data/transaction")
        self._nodes_dict = {}  # uri: neo4j_id
        self.graph_name = graph_name
        self.bulk_size = bulk_size

    def to_neo4j(self, rdf_graph):
        self.__refresh_nodes_dict()
        self.__nodes2neo(rdf_graph=rdf_graph)
        self.__relations2neo(rdf_graph=rdf_graph)

    def graph_properties_to_neo(self, graph_name, author="Anonymus", description="A graph.", version=1.0, subgraph_of ='http://simpol.ijs.si/lod2graph#LOD', **kwargs):  # add *args
        uri = namespace+graph_name
        node = Node(namespace+graph_name)
        node.add_meta_label("_SubgraphMetaData")
        node.add_name("_"+graph_name)
        node.add_property("author", author)
        node.add_property("description", description)
        node.add_property("version", version)
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        node.add_property("timestamp", st)
        for property_name, property_value in kwargs.items():
            node.add_property(property_name, property_value)
        query = node.to_neo4j_command()
        logger.info("Inserting graph metadata: " + str(query))
        statements= [query]
        statements.append("MATCH (n:__SubgraphMetaData),(m:__SubgraphMetaData) "
                          "WHERE n.uri ='"+uri+"' and m.uri = '%s'  MERGE (n)-[:_subgraph]->(m)" %subgraph_of)
        self.neo4j_commit_get_result(statements)

    def labels_to_neo(self, labels):
        """
        Adds the labels to the NEO4j database. It is useful only for the visualization in the Neo4j Browser.
        :param labels: The labels to be added to the database, specific to general.
        """
        counter = 0
        labels_string = ''
        for lab in labels:
            labels_string = labels_string+":`"+lab+"`"
            counter += 1
            if counter % 1000 ==0 and len(labels_string):
                query = "CREATE (n"+labels_string+") RETURN id(n) as nid"
                result = self.neo4j_commit_get_result(query)
                nid = result[0][u'nid']
                query = "MATCH n WHERE id(n) = %(nid)d DELETE n" % {"nid": nid}
                self.neo4j_commit(query)
                labels_string = ''
        query = "CREATE (n"+labels_string+") RETURN id(n) as nid"
        result = self.neo4j_commit_get_result(query)
        nid = result[0][u'nid']
        query = "MATCH n WHERE id(n) = %(nid)d DELETE n" % {"nid": nid}
        self.neo4j_commit(query)
        logger.info(str(counter) + " labels inserted")

    def clean_graph(self):
        logger.info("Truncate neo4j graph")
        clean_graph = raw_input('Clean neo4j graph (delete all nodes and relationships? (y/n): ')
        if clean_graph in ['y', 'Y']:
            logger.info("Cleaning neo4j graph")
            self.neo4j_commit('MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r;')

    def __refresh_nodes_dict(self):
        logger.debug("__refresh_nodes_dict")
        self._nodes_dict = {}
        page = 0
        limit = 100000
        result = " "
        while len(result):
            query = "MATCH (n) RETURN id(n) as nid , n.uri as uri SKIP %d LIMIT %d" % (limit*page, limit)
            result = self.neo4j_commit_get_result(query)
            for r in result:
                self._nodes_dict[r[u'uri']] = r[u'nid']
            page += 1
        logger.info("Building nodes dictionary, %d nodes found.", len(self._nodes_dict))

    def __nodes2neo(self, rdf_graph):
        logger.debug("__nodes2neo")
        start_time = time.time()
        rdf_nodes = set()

        for relation in rdf_graph.subjects(RDFS.subPropertyOf, namespace["relation"]):
            for (subj, obj) in rdf_graph.subject_objects(relation):
                rdf_nodes.add(subj)
                rdf_nodes.add(obj)
        logger.info("Building nodes: %d ", len(rdf_nodes))

        properties = dict()
        for prop in rdf_graph.subjects(RDFS.subPropertyOf, namespace["property"]):
            properties[prop] = rdf_graph.value(subject=prop, predicate=namespace["name"], default=uri2short(prop))

        nodes = []
        statements = []
        i = 0
        for uri in rdf_nodes:
            i += 1
            node = Node(uri)
            node_types = rdf_graph.objects(subject=uri, predicate=RDF.type)
            node.add_labels([uri2short(nt) for nt in node_types])
            node.add_meta_labels([self.graph_name, "LOD", "Graph"])
            for name_predicate in rdf_graph.subjects(RDFS.subPropertyOf, namespace["name"]):
                name = rdf_graph.value(subject=uri, predicate=name_predicate)
                node.add_name(name)
            for (pred, obj) in rdf_graph.predicate_objects(subject=uri):
                if pred in properties:
                    node.add_property(properties[pred], obj)
            if "%s" % uri in self._nodes_dict:                                # if uri already in the database
                logger.debug("Should merge with uri = %s" % uri)
              #  statements.append(node.to_neo4j_set_command())
            else:
                statements.append(node.to_neo4j_command())
                nodes.append(node)
            if i % self.bulk_size == 0:
                result = self.neo4j_commit_get_result(statements)
                for j in range(len(nodes)):
                    self._nodes_dict[nodes[j].uri] = result[j]['nid']
                statements = []
                nodes = []
                logger.info('n %s', i)
        if len(statements):
            result = self.neo4j_commit_get_result(statements)
            for j in range(len(nodes)):
                self._nodes_dict[nodes[j].uri] = result[j]['nid']
        end_time = time.time()
        time_diff = end_time - start_time
        logger.info("%d nodes inserted in %.3f seconds; %.3f per second.", i, time_diff, i / time_diff)

    def __relations2neo(self, rdf_graph):
        logger.debug("__relations2neo")
        logger.info('Processing relations')
        start_time = time.time()
        i = 0
        statements = []
     #   reltypes = set()

        for relation in rdf_graph.subjects(RDFS.subPropertyOf, namespace["relation"]):
            rel_name = rdf_graph.value(subject=relation, predicate=namespace["name"], default=uri2short(relation))
            logger.debug(relation)
            for subj, obj in rdf_graph.subject_objects(predicate=relation):
                i += 1
      #          reltypes.add(rel_name)
                statement = ['start n=node({origin}), m=node({target}) create unique n-[:`%s`]->m' % rel_name,
                             dict(origin=self._nodes_dict[str(subj)],
                                  target=self._nodes_dict[str(obj)])]
                statements.append(statement)
                if i % self.bulk_size == 0 and len(statements) >= 0:
                    self.neo4j_commit(statements)
                    statements = []
                    logger.info('r %d', i)
        if len(statements):
            self.neo4j_commit(statements)
            logger.info('finally %d', len(statements))

        end_time = time.time()
        time_diff = end_time - start_time
        logger.info("%d relations inserted in %.3f seconds; %.3f per second.", i, time_diff, i/time_diff)

    def neo4j_commit(self, statements, retry_count=20):
        if retry_count > 0:
            try:
                self.g.query(statements)
                self.g.commitTx()
            except Exception, e:
                self.g.rollbackTx()
                logger.warning("Error: %s" % str(e))
                delay = 3*(20 - retry_count)
                logger.warning("Transaction rollback, retrying in %d seconds..." % delay)
                time.sleep(delay)
                self.neo4j_commit(statements, retry_count=retry_count-1)
        else:
            logger.error("Unable to commit transaction.")

    def neo4j_commit_get_result(self, statements, retry_count=20):
        if retry_count > 0:
            try:
                result = self.g.queryd(statements)
                self.g.commitTx()
                return result
            except Exception, e:
                self.g.rollbackTx()
                logger.warning("Error: %s" % str(e))
                delay = 3*(20 - retry_count)
                logger.warning("Transaction rollback, retrying in %d seconds..." % delay)
                time.sleep(delay)
                return self.neo4j_commit_get_result(statements, retry_count=retry_count-1)
        else:
            raise Exception("Unable to commit transaction.")




if __name__ == "__main__":
    neo_graph = Rdf2neo("http://localhost:7474", graph_name="DBpedia", bulk_size=5000)
    # testing metadata


    # logger.info("Preliminaries")
    # logger.info("clear")
    # neo_graph.clean_graph()

    # file_names = [r"..\data\DBpedia\dbpedia-properties-sample.nt",
    #               r"..\data\DBpedia\dbpedia-instance_types_en-sample.nt"]
    #
    # file_name_mapping = r"..\data\DBpedia\dbpedia-lod2neo.n3"
    #
    # logger.info("Constructing the ontology backbone ...")
    # ontology_files = [r"..\data\DBpedia\dbpedia_3.9-ontology.n3", r"..\data\DBpedia\schema.rdfs.org_all.nt"]

    file_names = [r"..\data\DBpedia\dbpedia-mappingbased_properties_cleaned_en.nt",
                  r"..\data\DBpedia\dbpedia-instance_types_en.nt"]

    file_name_mapping = r"..\data\DBpedia\dbpedia-lod2neo.n3"

    logger.info("Constructing the ontology backbone ...")
    ontology_files = [r"..\data\DBpedia\dbpedia_3.9-ontology.n3", r"..\data\DBpedia\schema.rdfs.org_all.nt"]



    ob = OntologyBackbone(ontology_files)

    logger.info("adding labels")
    neo_graph.labels_to_neo("xmlns_Person")
    labels = ob.get_all_labels()
    neo_graph.labels_to_neo(labels)
    labels = ob.get_all_labels("http://schema.org/Thing")
    neo_graph.labels_to_neo(labels)

    logger.info("Loading the main data")
    logger.info("Reading the data with RdfLib ...")
    memg = Graph()
    for file_name in file_names:
        logger.debug("Reading file " + file_name)
        name, extension = os.path.splitext(file_name)
        memg.parse(file_name, extension[1:])
    logger.debug("The RDF graph has %s statements." % len(memg))
    logger.debug("Reading the RDF mapping file " + file_name_mapping)
    memg.parse(file_name_mapping, "n3")
    logger.debug("The RDF graph has %s statements." % len(memg))

    #-------------------------------------------------------------------------------------------------

    logger.info("rdf2neo main insert")
    neo_graph.to_neo4j(memg, ontology_backbone=ob)










