#!/usr/bin/env python3
"""
LSX Text Converter - Handles LSX <-> LSJ conversions (text-based, no wine needed)
"""

import json
import xml.etree.ElementTree as ET


class LSXTextConverter:
    """Converts between LSX (XML) and LSJ (JSON) formats"""
    
    def lsx_to_lsj(self, lsx_content):
        """Convert LSX (XML) to LSJ (JSON)"""
        try:
            root = ET.fromstring(lsx_content)
            
            # Build JSON structure
            json_data = {
                "save": {
                    "header": {
                        "version": root.get("version", "4.0.0.0")
                    },
                    "regions": {}
                }
            }
            
            # Convert regions
            for region in root.findall('.//region'):
                region_id = region.get('id', 'unknown')
                region_data = {}
                
                # Convert nodes
                for node in region.findall('.//node'):
                    node_id = node.get('id', 'unknown')
                    node_data = {}
                    
                    # Convert attributes
                    for attr in node.findall('.//attribute'):
                        attr_id = attr.get('id')
                        if attr_id:
                            node_data[attr_id] = {
                                "type": attr.get('type', 'string'),
                                "value": attr.get('value', '')
                            }
                    
                    if node_data:
                        region_data[node_id] = node_data
                
                if region_data:
                    json_data["save"]["regions"][region_id] = region_data
            
            return json.dumps(json_data, indent=2, ensure_ascii=False)
            
        except Exception as e:
            raise Exception(f"LSX to LSJ conversion failed: {e}")
    
    def lsj_to_lsx(self, lsj_content):
        """Convert LSJ (JSON) to LSX (XML)"""
        try:
            json_data = json.loads(lsj_content)
            
            # Create XML structure
            root = ET.Element("save")
            
            # Set version
            version = "4.0.0.0"
            if "save" in json_data and "header" in json_data["save"]:
                version = json_data["save"]["header"].get("version", version)
            root.set("version", version)
            
            # Convert regions
            if "save" in json_data and "regions" in json_data["save"]:
                regions_data = json_data["save"]["regions"]
                
                for region_id, region_content in regions_data.items():
                    region_elem = ET.SubElement(root, "region")
                    region_elem.set("id", region_id)
                    
                    for node_id, node_content in region_content.items():
                        node_elem = ET.SubElement(region_elem, "node")
                        node_elem.set("id", node_id)
                        
                        for attr_id, attr_data in node_content.items():
                            attr_elem = ET.SubElement(node_elem, "attribute")
                            attr_elem.set("id", attr_id)
                            
                            if isinstance(attr_data, dict):
                                attr_elem.set("type", attr_data.get("type", "string"))
                                attr_elem.set("value", str(attr_data.get("value", "")))
                            else:
                                attr_elem.set("type", "string")
                                attr_elem.set("value", str(attr_data))
            
            # Format and return
            self._indent_xml(root)
            xml_string = ET.tostring(root, encoding='unicode')
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_string
            
        except Exception as e:
            raise Exception(f"LSJ to LSX conversion failed: {e}")
    
    def _indent_xml(self, elem, level=0):
        """Add indentation to XML elements"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self._indent_xml(child, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i