__author__ = 'Petra'

from urlparse import urlparse
import os
from rdflib import Namespace, Graph, util
from rdflib.namespace import RDFS, RDF
from rdflib.term import URIRef
from node import *

FORMAT = '[%(asctime)-15s] %(levelname)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)


class OntologyBackbone():
    ont = Graph()   # static
    lookup = dict()

    def __init__(self, file_names):

        logger.info("Reading the data with RdfLib ...")

        for file_name in file_names:
            try:
                name, extension = os.path.splitext(file_name)
                self.ont.parse(file_name, format=util.guess_format(file_name))
            except:
                logger.exception("Error reading file "+file_name+". Parser for "+extension[1:]+" needed.")

    def get_labels(self, classes):
        labels = []
        for label in classes:
            labels.extend(self.get_superclasses(label))
        return labels

    def get_superclasses(self, uri, labels=[]):
        labels.append(uri2short(uri))
        parents = self.ont.objects(subject=URIRef(uri), predicate=RDFS.subClassOf)
        for p in parents:
            return self.get_superclasses(p, labels)
        return labels

    def get_all_types_df(self, lab=[], ontology_top=r"http://www.w3.org/2002/07/owl#Thing"):
        if type(ontology_top) is not URIRef:
            ontology_top = URIRef(ontology_top)

        layer = self.ont.subjects(object=ontology_top, predicate=RDFS.subClassOf)
        for term in layer:
            self.get_all_types(lab, term)
        lab.append(ontology_top)
        return lab

    def get_all_types(self, ontology_top=r"http://www.w3.org/2002/07/owl#Thing"):
        """
        Returns all types in the ontology, general to specific (breath-first)
        :param ontology_top: the root node of the ontology
        :return: list of uris of ontology classes
        """
        if type(ontology_top) is not URIRef:
            ontology_top = URIRef(ontology_top)
        layer = [ontology_top]
        labels = []
        while len(layer):
            next_layer = []
            for term in layer:
                labels.append(term)
                next_layer.extend(self.ont.subjects(object=term, predicate=RDFS.subClassOf))
            layer = next_layer
        return labels

    def get_all_labels(self, ontology_top=r"http://www.w3.org/2002/07/owl#Thing"):
        types = self.get_all_types(ontology_top=ontology_top)
        labels = []
        for uri in reversed(types):
            labels.append(uri2short(uri))
        return labels


def uri2short(uri):
    uri_str = str(uri)
    u = urlparse(uri_str)
    parts = u.netloc.split('.')
    if len(parts) >= 2:
        short = parts[-2]
    else:
        short = u.netloc
    #standard namespaces from http://www.w3.org/TR/vocab-org/#namespaces-1
    if uri_str.startswith("http://xmlns.com/foaf/0.1/"): short ="foaf"
    elif uri_str.startswith("http://purl.org/goodrelations/v1#"): short ="gr"
    elif uri_str.startswith("http://www.w3.org/ns/prov#"): short ="prov"
    elif uri_str.startswith("http://www.w3.org/ns/org#"): short ="org"
    elif uri_str.startswith("http://www.w3.org/2002/07/owl#"): short ="owl"
    elif uri_str.startswith("http://www.w3.org/2006/time#"): short ="time"
    elif uri_str.startswith("http://www.w3.org/1999/02/22-rdf-syntax-ns#"): short ="rdf"
    elif uri_str.startswith("http://www.w3.org/2000/01/rdf-schema#"): short ="rdfs"
    elif uri_str.startswith("http://www.w3.org/2004/02/skos/core#"): short ="skos"
    elif uri_str.startswith("http://www.w3.org/2006/vcard/ns#"): short ="vcard"
    elif uri_str.startswith("http://purl.org/dc/terms/"): short ="dct"

    if u.fragment:
        short = short + "_" + u.fragment
    else:
        short = short + "_" + uri[uri.rfind('/') + 1:]
    short = short.replace('.', '_')
    short = short.replace('-', '_')
    return short


def main():
    ontology_files = [r"..\data\DBpedia\dbpedia_3.9-ontology.n3"]
    ob = OntologyBackbone(ontology_files)
    print "\nGet all types:"
    labels = ob.get_all_types()
    for l in labels:
        print l

    print "\nGet all labels:"
    labels = ob.get_all_labels()
    for l in labels:
        print l

    print "\nGet labels for instance"
    labels = ob.get_labels("http://dbpedia.org/ontology/RoadTunnel")
    for l in labels:
        print l

if __name__ == "__main__":
    main()