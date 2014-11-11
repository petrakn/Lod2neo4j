"""
Loads LOD files in formats supported by RDFlib (n3, nt) and generates a file file_out (default "_lod2neo.n3")
with a mapping of predicates from rdf graph to property gaph.
There are four types of predicates that are used by lod_insert.py: type, name, relation and property.
It also generates names for the relations/properties.
"""
import rdflib
from sets import Set
from rdflib.namespace import RDFS
from rdflib import URIRef, Namespace, Literal, util
from rdflib.graph import Graph
import logging
import os
from OntologyBackbone import uri2short


FORMAT = '[%(asctime)-15s] %(levelname)s: %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)

ns = Namespace("http://simpol.ijs.si/lod2graph#")


file_out = r"..\data\DBpedia\dbpedia2014-lod2neo.n3"
#file_out = r"..\data\reegle\reegle-lod2neo.n3"


def main():
    file_names = [#r"..\data\DBpedia\dbpedia_3.9-ontology.owl",
                  r"..\data\DBpedia\instance_types_en.nt",
                  r"..\data\DBpedia\mappingbased_properties_cleaned_en.nt",
                  r"..\data\DBpedia\homepages_en.nt"]
#    file_names = [r"..\data\reegle\latest_reegle_dump.nt"]
    rdf_inspect(file_names)


def rdf_inspect(file_names, verbose=1):
    logger.info("Reading the data with RdfLib ...")

    memg = rdflib.Graph()
    for file_name in file_names:
        name, extension = os.path.splitext(file_name)
        memg.parse(file_name, format=util.guess_format(file_name))
    print("Graph has %s statements." % len(memg))


    pred_set = Set()
    for pred in memg.predicates(None, None):
        pred_set.add(pred)
    print("Graph has %s distinct predicates." % len(pred_set))

    types = []
    properties = []
    relations = []
    names = []

    for pred in pred_set:
        if pred in [URIRef(u'http://www.w3.org/2004/02/skos/core#prefLabel'),
                    URIRef(u'http://www.w3.org/2000/01/rdf-schema#label'),
                    URIRef(u'http://www.geonames.org/ontology#name'),
                    URIRef(u'http://xmlns.com/foaf/0.1/name'),
                    URIRef(u'http://purl.org/dc/elements/1.1/title'),
                    URIRef(u'http://dbpedia.org/ontology/personName'),
                    URIRef(u'http://reegle.info/schema#projectTitle')]:
            names.append(pred)
            properties.append(pred)
        elif pred == URIRef(u'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
            types.append(pred)
        else:
            (s, p, o) = memg.triples((None, pred, None)).next()
            o_uri = ("%s" % o).lower()
            if isinstance(o, rdflib.term.Literal) \
                    or o_uri.endswith("jpg") \
                    or o_uri.endswith("png") \
                    or o_uri.endswith("pdf") \
                    or o_uri.endswith("doc") \
                    or p == URIRef(u'http://xmlns.com/foaf/0.1/homepage'):
                properties.append(p)
            else:
                relations.append(p)
    lod2graph_mapping(file_out, types, properties, relations, names)

    if verbose:
        logger.info("Types of RDF relations:")
        logger.info("Properties: %d" %len(properties))
        for pred in properties:
            (s, p, o) = memg.triples((None, pred, None)).next()
            logger.info("%s \t %s  %s  %s" % (pred, s, p, o))

        logger.info("Relations: %d" %len(relations))
        for pred in relations:
            (s, p, o) = memg.triples((None, pred, None)).next()
            logger.info("%s \t %s  %s  %s" % (pred, s, p, o))

        logger.info("Types: %d" % len(types))
        for pred in types:
            (s, p, o) = memg.triples((None, pred, None)).next()
            logger.info("%s \t %s  %s  %s" % (pred, s, p, o))

        logger.info("Names: %d" % len(names))
        for pred in names:
            (s, p, o) = memg.triples((None, pred, None)).next()
            logger.info("%s \t %s  %s  %s" % (pred, s, p, o))


def lod2graph_mapping(file_out, types, properties, relations, names):
    g = Graph()
    g.bind("lod2graph", ns)
    for pred in types:
        g.add((pred, RDFS.subPropertyOf, ns["type"]))
        g.add((pred, ns["name"], Literal(uri2short(pred))))
    for pred in properties:
        g.add((pred, RDFS.subPropertyOf, ns["property"]))
        g.add((pred, ns["name"], Literal(uri2short(pred))))
    for pred in relations:
        g.add((pred, RDFS.subPropertyOf, ns["relation"]))
        g.add((pred, ns["name"], Literal(uri2short(pred))))
    for pred in names:
        g.add((pred, RDFS.subPropertyOf, ns["name"]))
        g.add((pred, ns["name"], Literal(uri2short(pred))))
    g.serialize(file_out, format="n3")
    logger.info("\nMapping file writen to: " + os.path.abspath(file_out))


if __name__ == "__main__":
    main()