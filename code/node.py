import logging
"""

A simple class for setting node properties and labels to be later converted to a Cypher create query.


"""

from urllib2 import unquote
import re

class Node:
    def __init__(self, uri):
        self.uri = str(uri)
        self.labels = []
        self.name = ""
        self.names = []
        self.properties = dict()

    def add_label(self, label):
        if label != "_None" and label !="w3_Thing" and label not in self.labels:
            self.labels.append(label)

    def add_labels(self, labels):
            for label in labels:
                self.add_label(label)

    def add_meta_label(self, label):
        if label != "_None" and label not in self.labels:
            self.labels.append("_"+label)

    def add_meta_labels(self, labels):
        for label in labels:
            self.add_meta_label(label)

    # def set_type(self, rdf_type):
    #     self.properties["type"] = str(rdf_type)
    #     self.add_label(str(rdf_type))

    def add_name(self, name):
        if name and name not in self.names and name != self.name:
            if self.name != "":
                self.names.append(self.name)
            self.name = name

    def add_property(self, property_name, property_value):
        self.properties[property_name] = property_value

    # def merge(self, node):
    #     a = len(self.properties) + len(node.properties)
    #     self.properties = dict(self.properties.items() + node.properties.items())
    #     if a != len(self.properties):
    #         logger = logging.getLogger(__name__)
    #         logger.INFO("Some properties were lost when merging nodes %s nad #s", self.uri[0], node.uri[0])
    #     self.uri.append(node.uri)
    #     self.names.append(node.names)
    #     self.labels.append(node.get_all_types)

    def to_neo4j_command(self):
        self.setNameIfNotExists()
        self.properties["name"] = self.name
        if len(self.names):
            self.properties["names"] = self.names
        self.properties["uri"] = self.uri

        self.properties["labels"] = ""
        for label in self.labels:
            label = label.split("_")[1]
            label = re.sub("([a-z])([A-Z])", "\g<1> \g<2>", label)
            self.properties["labels"] += " " + label

        node_command = 'CREATE (n'
        for label in self.labels:
            node_command += ":`" + label+"`"
        node_command += ' {kw}) RETURN id(n) AS nid;'
        statement = [node_command, dict(kw=self.properties)]
        return statement

    def to_neo4j_merge_command(self):
        self.setNameIfNotExists()
        self.properties["name"] = self.name
        if self.names:
            self.properties["names"] = self.names
        self.properties["uri"] = self.uri

        node_command = 'MERGE (n'
        for label in self.labels:
            node_command += ":`" + label + "`"
        node_command += "{uri:'%s' })\n " % self.uri
        node_command += " ON CREATE SET "
        for p in self.properties:
            node_command += "n.%s = '%s',\n" % (p, self.properties[p])
        node_command += "n.version = 1\n"
        node_command += " ON MATCH SET "
        for p in self.properties:
            node_command += "n.%s = '%s',\n" % (p, self.properties[p])
        node_command += "n.version = 2\n"
        node_command += ' RETURN id(n) AS nid;'
        statement = [node_command]
        print node_command
        return statement

    def to_neo4j_set_command(self):
        self.setNameIfNotExists()
        self.properties["name"] = self.name
        if len(self.names):
            self.properties["names"] = self.names
        self.properties["uri"] = self.uri
        self.properties["version"] = 2

        node_command = "MATCH (n:_Graph {uri:'%s' })\n " % self.uri
        node_command += "SET "
        # node_command += "n"
        # for label in self.labels:
        #     node_command += ":`%s`" % label
        node_command += " n += {kw}"
        statement = [node_command, dict(kw=self.properties)]
        return statement

    def setNameIfNotExists(self):
        if self.name == "":
            self.name = uri2name(self.uri)


def uri2name(uri):
    uri_str = str(uri)
    uri_str = unquote(uri_str)
    name = (uri_str[uri_str.rfind('/') + 1:]).replace('_', ' ')
    return name + "***"