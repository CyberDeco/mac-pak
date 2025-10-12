#!/usr/bin/env python3
"""
LSX Text Converter - Handles LSX <-> LSJ conversions (text-based, no wine needed)
"""

import json
import xml.etree.ElementTree as ET
from collections import defaultdict

class LSXLSJConverter:
    """Converts between LSX (XML) and LSJ (JSON) formats"""
    
    def lsx_to_lsj(self, lsx_content):
        try:
            root = ET.fromstring(lsx_content)
            
            version_elem = root.find('version')
            version = "4.0.0.0"
            if version_elem is not None:
                version = f"{version_elem.get('major', '4')}.{version_elem.get('minor', '0')}.{version_elem.get('revision', '0')}.{version_elem.get('build', '0')}"
            
            json_data = {
                "save": {
                    "header": {"time": 0, "version": version},
                    "regions": {}
                }
            }
            
            for region in root.findall('region'):
                region_id = region.get('id')
                if region_id:
                    region_node = region.find('node')
                    if region_node is not None:
                        json_data["save"]["regions"][region_id] = self._node_to_dict(region_node)


            json_str = json.dumps(json_data, indent='\t', ensure_ascii=False)
            
            return json_str.replace('\n', '\r\n')
        except Exception as e:
            raise Exception(f"LSX to LSJ conversion failed: {e}")
    
    def _node_to_dict(self, node):
        result = {}
        
        # Convert <attribute> tags
        for attr in node.findall('attribute'):
            attr_id = attr.get('id')
            if attr_id:
                attr_type = attr.get('type', 'string')
                attr_obj = {"type": attr_type}
                
                if attr.get('value') is not None:
                    attr_obj['value'] = self._parse_val(attr.get('value'), attr_type)
                
                # Check for handle attribute (even if empty string)
                if 'handle' in attr.attrib:
                    attr_obj['handle'] = attr.get('handle')
                
                # Check for version attribute (even if "0")
                if 'version' in attr.attrib:
                    version_val = int(attr.get('version', '0'))
                    if version_val != 0:
                        attr_obj['version'] = version_val
                
                result[attr_id] = attr_obj
        
        # Check for <children> wrapper
        children_wrapper = node.find('children')
        if children_wrapper is not None:
            groups = defaultdict(list)
            for child in children_wrapper.findall('node'):
                nid = child.get('id')
                if nid:
                    groups[nid].append(self._node_to_dict(child))
            
            for nid, nlist in groups.items():
                result[nid] = nlist
        
        return result
    
    def _parse_val(self, s, attr_type=None):
        if s in ('True', 'False'):
            return s == 'True'
        
        if attr_type in ('FixedString', 'LSString', 'TranslatedString', 'guid'):
            return s
        
        if attr_type in ('int32', 'uint8', 'uint32', 'int64', 'uint64'):
            try:
                return int(s)
            except:
                return s
        
        if attr_type in ('float', 'double'):
            try:
                return float(s)
            except:
                return s
        
        try:
            if '.' in s:
                return float(s)
            return int(s)
        except:
            return s
    
    def lsj_to_lsx(self, lsj_content):
        try:
            data = json.loads(lsj_content)
            version = data.get("save", {}).get("header", {}).get("version", "4.0.0.0")
            
            root = ET.Element("save")
            parts = version.split('.')
            if len(parts) >= 4:
                v = ET.SubElement(root, "version")
                v.set("major", parts[0])
                v.set("minor", parts[1])
                v.set("revision", parts[2])
                v.set("build", parts[3])
            
            for rid, rdata in data.get("save", {}).get("regions", {}).items():
                region = ET.SubElement(root, "region")
                region.set("id", rid)
                node = ET.SubElement(region, "node")
                node.set("id", rid)
                self._dict_to_node(node, rdata)
            
            ET.indent(root, space="  ")
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode')
        except Exception as e:
            raise Exception(f"LSJ to LSX failed: {e}")
    
    def _dict_to_node(self, node, data):
        if not isinstance(data, dict):
            return
        
        has_node_children = False
        
        for k, v in data.items():
            if isinstance(v, dict) and 'type' in v:
                attr = ET.SubElement(node, "attribute")
                attr.set("id", k)
                attr.set("type", v['type'])
                if 'value' in v:
                    attr.set("value", str(v['value']))
                if 'handle' in v:
                    attr.set("handle", v['handle'])
                if 'version' in v:
                    attr.set("version", str(v['version']))
            elif isinstance(v, list):
                has_node_children = True
        
        if has_node_children:
            children_wrapper = ET.SubElement(node, "children")
            
            for k, v in data.items():
                if isinstance(v, list) and v:
                    for item in v:
                        if isinstance(item, dict) and 'type' not in item:
                            child_node = ET.SubElement(children_wrapper, "node")
                            child_node.set("id", k)
                            self._dict_to_node(child_node, item)