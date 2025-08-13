import rdflib
import json
import hashlib
import os
import re
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, SKOS
from typing import List, Dict, Any, Set
from collections import defaultdict
import math

# Define namespaces
CQ = Namespace("http://example.org/cq-vocabulary#")
EX = Namespace("http://example.org/data#")
SCHEMA = Namespace("http://schema.org/")
ANIML = Namespace("https://w3id.org/animl/")
ALLOTROPE = Namespace("http://purl.allotrope.org/ontologies/")
MOUSE_HUMAN = Namespace("http://mouse.owl#")

# Define available ontology namespaces
ONTOLOGY_NAMESPACES = {
    "animl": {
        "uri": "https://w3id.org/animl/",
        "prefix": "animl"
    },
    "allotrope": {
        "uri": "http://purl.allotrope.org/ontologies/",
        "prefix": "allotrope"
    },
    "mouse-human": {
        "uri": "http://mouse.owl#",
        "prefix": "mouse"
    }
}

def get_ontology_namespace(ontology_type: str) -> Namespace:
    """Get the appropriate namespace for the ontology type."""
    if ontology_type.lower() in ONTOLOGY_NAMESPACES:
        return Namespace(ONTOLOGY_NAMESPACES[ontology_type.lower()]["uri"])
    else:
        raise ValueError(f"Unsupported ontology type: {ontology_type}. Supported types: {list(ONTOLOGY_NAMESPACES.keys())}")

def _normalize_label(s: str) -> str:
    return re.sub(r'[^a-z0-9_ ]','',
                  s.lower().strip()
                 ).replace('-', ' ').replace('_',' ').replace('  ',' ').strip()

def _tokenize(s: str) -> List[str]:
    return [t for t in _normalize_label(s).split() if t]

def extract_ontology_elements(ontology_path: str, ontology_type: str) -> Dict[str, Any]:
    """
    Extract classes & properties with multiple lookup indices:
      - exact label
      - id (local part)
      - normalized label (underscores/spaces ignored)
      - token signature (unordered)
    Also builds reverse maps and token indices for fuzzy resolution.
    """
    try:
        g = Graph()
        g.parse(ontology_path, format="xml")
        info = ONTOLOGY_NAMESPACES[ontology_type.lower()]
        base = info["uri"]

        classes: Set[str] = set()
        properties: Set[str] = set()

        label_to_uri: Dict[str,str] = {}
        uri_to_label: Dict[str,str] = {}
        id_to_uri: Dict[str,str] = {}
        token_index: Dict[str, Set[str]] = defaultdict(set)  # token -> set(uris)
        signature_index: Dict[str, Set[str]] = defaultdict(set)  # sorted token signature -> uris

        def register(subj: URIRef, is_property=False):
            uri = str(subj)
            if not (uri.startswith(base)):
                return
            local_id = uri.split('#')[-1]
            target_set = properties if is_property else classes
            target_set.add(uri)
            id_to_uri[local_id.lower()] = uri
            # collect labels (may be none)
            labels = [str(o).strip() for _,_,o in g.triples((subj, RDFS.label, None))]
            if not labels:
                labels = [local_id]  # fallback
            for lbl in labels:
                norm_lbl = lbl.lower()
                label_to_uri[norm_lbl] = uri
                uri_to_label[uri] = lbl
                # normalized variant (remove punctuation / unify)
                normalized_variant = _normalize_label(lbl).replace(' ','_')
                label_to_uri[normalized_variant] = uri
                # token indexing
                tokens = _tokenize(lbl)
                if tokens:
                    for t in tokens:
                        token_index[t].add(uri)
                    signature = ' '.join(sorted(tokens))
                    signature_index[signature].add(uri)
            # also map id variants
            label_to_uri[local_id.lower()] = uri
            label_to_uri[local_id.lower().replace('_',' ')] = uri

        # Classes
        for subj,_,_ in g.triples((None, RDF.type, OWL.Class)):
            register(subj, is_property=False)

        # Object & Datatype Properties
        for subj,_,_ in g.triples((None, RDF.type, OWL.ObjectProperty)):
            register(subj, is_property=True)
        for subj,_,_ in g.triples((None, RDF.type, OWL.DatatypeProperty)):
            register(subj, is_property=True)

        # Handle UNDEFINED_* properties extra variants
        for uri in list(properties):
            local = uri.split('#')[-1]
            if local.lower().startswith('undefined_'):
                trimmed = local[len('UNDEFINED_'):].lower()
                label_to_uri[trimmed] = uri
                label_to_uri[trimmed.replace('_',' ')] = uri

        return {
            "classes": classes,
            "properties": properties,
            "label_to_uri_map": label_to_uri,
            "uri_to_label_map": uri_to_label,
            "id_to_uri_map": id_to_uri,
            "token_index": token_index,
            "signature_index": signature_index
        }
    except Exception as e:
        print(f"Error extracting ontology elements: {e}")
        return {
            "classes": set(),
            "properties": set(),
            "label_to_uri_map": {},
            "uri_to_label_map": {},
            "id_to_uri_map": {},
            "token_index": {},
            "signature_index": {}
        }

def validate_and_create_uri(element_name: str,
                            ontology_elements: Dict[str, Any],
                            ontology_ns: Namespace,
                            element_type: str) -> str:
    """
    Resolve element_name to a URI with layered strategy.
    Safe against missing keys in ontology_elements.
    """
    raw = element_name.strip().strip('"').strip("'")
    if not raw:
        return None

    if not ontology_elements:
        print(f"  ✗ ontology index empty; cannot resolve {element_type} '{raw}'")
        return None

    q_lower = raw.lower()
    label_map = ontology_elements.get("label_to_uri_map", {}) or {}
    token_index = ontology_elements.get("token_index", {}) or {}
    signature_index = ontology_elements.get("signature_index", {}) or {}
    pool = ontology_elements.get("classes" if element_type == "class" else "properties", set()) or set()

    print(f"Validating {element_type}: '{raw}'")

    # 1 direct label/id
    if q_lower in label_map:
        uri = label_map[q_lower]
        if not pool or uri in pool:
            print(f"  ✓ exact label/id match -> {uri}")
            return uri

    # 2 normalized
    norm = _normalize_label(raw)
    for key in (norm, norm.replace(' ','_')):
        if key in label_map:
            uri = label_map[key]
            if not pool or uri in pool:
                print(f"  ✓ normalized match '{key}' -> {uri}")
                return uri

    # 3 token signature
    q_tokens = _tokenize(raw)
    if q_tokens and signature_index:
        signature = ' '.join(sorted(q_tokens))
        if signature in signature_index:
            cands = [u for u in signature_index[signature] if (not pool or u in pool)]
            if len(cands) == 1:
                print(f"  ✓ token-signature match -> {cands[0]}")
                return cands[0]

    # 4 token overlap fuzzy
    if q_tokens and token_index:
        q_set = set(q_tokens)
        seen = set()
        best = None
        for t in q_set:
            for cand in token_index.get(t, []):
                if (pool and cand not in pool) or cand in seen:
                    continue
                seen.add(cand)
                lbl = ontology_elements.get("uri_to_label_map", {}).get(cand, cand.split('#')[-1])
                cand_tokens = set(_tokenize(lbl))
                if not cand_tokens:
                    continue
                j = len(q_set & cand_tokens) / len(q_set | cand_tokens)
                overlap = len(q_set & cand_tokens) / len(q_set)
                if j >= 0.5 or overlap >= 0.75:
                    score = (j, overlap)
                    if not best or score > best[0]:
                        best = (score, cand)
        if best:
            (j, ov), uri = best
            print(f"  ✓ fuzzy token match J={j:.2f} overlap={ov:.2f} -> {uri}")
            return uri

    # 5 direct construction
    constructed = str(ontology_ns[raw.replace(' ','_')])
    if not pool or constructed in pool:
        if constructed in label_map.values() or constructed in pool:
            print(f"  ✓ direct URI match -> {constructed}")
            return constructed

    print(f"  ✗ not found: '{raw}'")
    # suggestions
    if label_map:
        q_tokens_top = set(q_tokens[:3])
        suggestions = []
        for lbl, uri in label_map.items():
            if not pool or uri in pool:
                if q_tokens_top and any(tok in lbl for tok in q_tokens_top):
                    suggestions.append((lbl, uri))
        if not suggestions:
            # fallback pick first few
            suggestions = list(label_map.items())[:5]
        print("    Suggestions:")
        for lbl, uri in suggestions[:5]:
            print(f"      - {lbl} -> {uri}")
    return None

def clean_uri_component(component: str) -> str:
    """Clean URI component by removing quotes and invalid characters."""
    # Remove quotes and whitespace
    cleaned = component.strip().strip('"').strip("'")
    # Replace spaces with underscores
    cleaned = cleaned.replace(" ", "_")
    return cleaned

def load_ontology(ontology_path: str) -> str:
    """
    Load an ontology from a given file path.

    Args:
        ontology_path (str): The path to the ontology file.

    Returns:
        str: The content of the ontology file.
    """
    format = ontology_path.split(".")[-1]
    
    if format.lower() == "ttl":
        format_for_parser = "turtle"
    elif format.lower() == "rdf":
        format_for_parser = "xml"
    elif format.lower() == "jsonld":
        format_for_parser = "json-ld"
    else:
        format_for_parser = "xml"  # Default to xml
    
    try:
        with open(ontology_path, 'r', encoding='utf-8') as file:
            ontology_content = file.read()
        return ontology_content
    except FileNotFoundError:
        print(f"Error: The file {ontology_path} was not found.")
        return ""
    except Exception as e:
        print(f"Error loading ontology: {e}")
        return ""

def create_cq_vocabulary_triples(graph: Graph) -> None:
    """
    Add the CQ vocabulary definitions to the graph.
    
    Args:
        graph (Graph): The RDF graph to add triples to.
    """
    # Define CompetencyQuestion class
    graph.add((CQ.CompetencyQuestion, RDF.type, OWL.Class))
    graph.add((CQ.CompetencyQuestion, RDFS.subClassOf, SKOS.Concept))
    
    # Define properties
    graph.add((CQ.involvesClass, RDF.type, OWL.ObjectProperty))
    graph.add((CQ.involvesClass, RDFS.subPropertyOf, SCHEMA.about))
    
    graph.add((CQ.involvesProperty, RDF.type, OWL.ObjectProperty))
    graph.add((CQ.involvesProperty, RDFS.subPropertyOf, SCHEMA.about))

def cq_json_to_rdf_triples(cq_data: dict, ontology_ns: Namespace, ontology_elements: Dict[str, Set[str]]) -> list:
    """Convert a single CQ JSON object to RDF triples using validated ontology elements."""
    triples = []
    
    # Create CQ URI using hash
    cq_uri = cq_data.get("@URI", "unknown")
    cq_id = cq_uri[:8] if len(cq_uri) > 8 else cq_uri
    cq_resource = EX[f"CQ_{cq_id}"]
    
    # CQ instance
    triples.append((cq_resource, RDF.type, CQ.CompetencyQuestion))
    
    # Question text
    question = cq_data.get("question", "")
    if question:
        triples.append((cq_resource, SKOS.definition, Literal(question)))
        # Add prefLabel with truncated question
        #pref_label = f"CQ: {question[:50]}{'...' if len(question) > 50 else ''}"
        #triples.append((cq_resource, SKOS.prefLabel, Literal(pref_label)))
    
    # Link to classes - VALIDATE they exist in ontology
    classes = cq_data.get("Class(es)", [])
    valid_class_count = 0
    if classes:
        print(f"\nProcessing classes for CQ: {question[:50]}...")
        for cls in classes:
            validated_uri = validate_and_create_uri(cls, ontology_elements, ontology_ns, "class")
            if validated_uri:
                triples.append((cq_resource, CQ.involvesClass, URIRef(validated_uri)))
                valid_class_count += 1
            else:
                print(f"  Skipping invalid class: '{cls}'")
    
    # Link to properties - VALIDATE they exist in ontology
    properties = cq_data.get("Relationship(s)", [])
    valid_prop_count = 0
    if properties:
        print(f"Processing properties for CQ: {question[:50]}...")
        for prop in properties:
            validated_uri = validate_and_create_uri(prop, ontology_elements, ontology_ns, "property")
            if validated_uri:
                triples.append((cq_resource, CQ.involvesProperty, URIRef(validated_uri)))
                valid_prop_count += 1
            else:
                print(f"  Skipping invalid property: '{prop}'")
    
    # Only return triples if we have valid classes or properties
    if valid_class_count > 0 or valid_prop_count > 0:
        print(f"  ✓ CQ valid: {valid_class_count} classes, {valid_prop_count} properties")
        return triples
    else:
        print(f"  ✗ CQ invalid: no valid classes or properties found")
        return []

# [Rest of the functions remain the same but with enhanced error handling...]

def get_triples_from_enrichment_json(json_ld_path: str,
                                     output_file: str = None,
                                     ontology: str = "mouse-human",
                                     ontology_path: str = None) -> Graph:
    """
    Convert enrichment JSON-LD to RDF triples and save as XML.
    Requires ontology_path for proper validation.
    """
    if ontology.lower() not in ONTOLOGY_NAMESPACES:
        raise ValueError(f"Unsupported ontology type: {ontology}. Supported: {list(ONTOLOGY_NAMESPACES.keys())}")

    if not ontology_path or not os.path.exists(ontology_path):
        print("ERROR: ontology_path missing or not found. Pass ontology_path to enable class/property resolution.")
        return Graph()

    print(f"Processing CQs for {ontology.upper()} ontology...")
    ontology_ns = get_ontology_namespace(ontology)
    info = ONTOLOGY_NAMESPACES[ontology.lower()]
    print(f"Using namespace: {info['prefix']} -> {info['uri']}")

    ontology_elements = extract_ontology_elements(ontology_path, ontology)
    if not ontology_elements.get("label_to_uri_map"):
        print("ERROR: ontology indexing produced no label mappings; aborting.")
        return Graph()

    g = Graph()
    g.bind("rdf", RDF); g.bind("rdfs", RDFS); g.bind("owl", OWL)
    g.bind("skos", SKOS); g.bind("schema", SCHEMA)
    g.bind("cq", CQ); g.bind("ex", EX)
    g.bind(info["prefix"], ontology_ns)
    create_cq_vocabulary_triples(g)

    try:
        with open(json_ld_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON-LD {json_ld_path}: {e}")
        return g

    total = 0; valid = 0
    items = data if isinstance(data, list) else [data]
    for cq in items:
        if not isinstance(cq, dict):
            continue
        total += 1
        triples = cq_json_to_rdf_triples(cq, ontology_ns, ontology_elements)
        for tr in triples:
            g.add(tr)
        if triples:
            valid += 1

    print(f"\nSummary:\n  Total CQs processed: {total}\n  Valid CQs: {valid}\n  Skipped: {total - valid}")

    if output_file:
        g.serialize(destination=output_file, format="xml")
        print(f"RDF triples saved to {output_file}")

    return g

def combine_ontology_with_cqs(ontology_path: str, json_ld_path: str, output_file: str = None, ontology: str = "mouse-human") -> Graph:
    """
    Combine existing ontology with CQ triples while preserving original structure.
    """
    
    # Validate ontology type
    if ontology.lower() not in ONTOLOGY_NAMESPACES:
        raise ValueError(f"Unsupported ontology type: {ontology}. Supported: {list(ONTOLOGY_NAMESPACES.keys())}")
    
    print(f"Combining {ontology.upper()} ontology with CQs...")
    
    # Get ontology namespace
    ontology_ns = get_ontology_namespace(ontology)
    ontology_info = ONTOLOGY_NAMESPACES[ontology.lower()]
    
    print(f"Using namespace: {ontology_info['prefix']} -> {ontology_info['uri']}")
    
    # Extract actual ontology elements for validation
    ontology_elements = extract_ontology_elements(ontology_path, ontology)
    
    # Create RDF graph for CQs only
    cq_graph = Graph()
    
    # Bind namespaces
    cq_graph.bind("rdf", RDF)
    cq_graph.bind("rdfs", RDFS)
    cq_graph.bind("owl", OWL)
    cq_graph.bind("skos", SKOS)
    cq_graph.bind("schema", SCHEMA)
    cq_graph.bind("cq", CQ)
    cq_graph.bind("ex", EX)
    cq_graph.bind(ontology_info["prefix"], ontology_ns)
    
    # Add CQ vocabulary
    create_cq_vocabulary_triples(cq_graph)
    
    # Load and process JSON-LD data
    try:
        with open(json_ld_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON-LD file not found: {json_ld_path}")
        return cq_graph
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file {json_ld_path}: {e}")
        return cq_graph
    
    # Process each CQ with validation
    cq_count = 0
    valid_cq_count = 0
    if isinstance(data, list):
        for cq_data in data:
            if isinstance(cq_data, dict):
                # Pass ontology elements for validation
                triples = cq_json_to_rdf_triples(cq_data, ontology_ns, ontology_elements)
                if triples:
                    for triple in triples:
                        cq_graph.add(triple)
                    valid_cq_count += 1
                cq_count += 1
    elif isinstance(data, dict):
        triples = cq_json_to_rdf_triples(data, ontology_ns, ontology_elements)
        if triples:
            for triple in triples:
                cq_graph.add(triple)
            valid_cq_count = 1
        cq_count = 1
    
    print(f"Processed {cq_count} competency questions, {valid_cq_count} valid for {ontology.upper()}")
    
    # Use the improved serialization that preserves original structure
    if output_file:
        serialize_ontology_with_sections(cq_graph, output_file, ontology_path, ontology)
        print(f"Combined ontology saved to {output_file}")
    
    return cq_graph

# [Include all the remaining functions from the previous version...]
def serialize_ontology_with_sections(graph: Graph, output_file: str, original_ontology_path: str, ontology: str) -> None:
    """Generate XML content with proper OWL structure and append to original ontology."""
    
    # Get ontology info
    ontology_info = ONTOLOGY_NAMESPACES[ontology.lower()]
    ontology_ns = get_ontology_namespace(ontology)
    
    print(f"Serializing with {ontology.upper()} namespace: {ontology_info['uri']}")
    
    # Generate CQ vocabulary section
    vocab_content = f"""
    <!-- 
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Competency Question Vocabulary
    //
    ///////////////////////////////////////////////////////////////////////////////////////
     -->

    <!-- 1. Define CQ Vocabulary -->
    <!-- Competency Question class and properties for linking CQs to {ontology.upper()} ontology elements -->

    <owl:Class rdf:about="http://example.org/cq-vocabulary#CompetencyQuestion">
        <rdfs:subClassOf rdf:resource="http://www.w3.org/2004/02/skos/core#Concept"/>
    </owl:Class>

    <owl:ObjectProperty rdf:about="http://example.org/cq-vocabulary#involvesClass">
        <rdfs:subPropertyOf rdf:resource="http://schema.org/about"/>
    </owl:ObjectProperty>

    <owl:ObjectProperty rdf:about="http://example.org/cq-vocabulary#involvesProperty">
        <rdfs:subPropertyOf rdf:resource="http://schema.org/about"/>
    </owl:ObjectProperty>
"""

    # Generate CQ instances section
    instances_content = f"""
    <!-- 
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Competency Question Instances for {ontology.upper()}
    //
    ///////////////////////////////////////////////////////////////////////////////////////
     -->

    <!-- 2. Create and describe Competency Question instances -->
    <!-- Generated competency questions with links to {ontology.upper()} ontology classes and properties -->
"""

    # Add CQ instances - ENSURE correct namespace URIs
    for subj, pred, obj in graph:
        if (subj, RDF.type, CQ.CompetencyQuestion) in graph:
            # This is a CQ instance
            cq_id = str(subj).split('#')[-1] if '#' in str(subj) else str(subj).split('/')[-1]
            
            instances_content += f"""
    <cq:CompetencyQuestion rdf:about="{subj}">"""
            
            # Add properties for this CQ
            for s, p, o in graph:
                if s == subj and p != RDF.type:
                    if p == SKOS.definition:
                        instances_content += f"""
        <skos:definition>{o}</skos:definition>"""
                    elif p == SKOS.prefLabel:
                        instances_content += f"""
        <skos:prefLabel>{o}</skos:prefLabel>"""
                    elif p == CQ.involvesClass:
                        # Verify the URI uses the correct ontology namespace
                        uri_str = str(o)
                        # Check for namespace mismatches
                        expected_namespace = ontology_info["uri"]
                        if not uri_str.startswith(expected_namespace):
                            print(f"WARNING: Found unexpected namespace URI in {ontology} ontology: {uri_str}")
                        instances_content += f"""
        <cq:involvesClass rdf:resource="{o}"/>"""
                    elif p == CQ.involvesProperty:
                        # Verify the URI uses the correct ontology namespace
                        uri_str = str(o)
                        # Check for namespace mismatches
                        expected_namespace = ontology_info["uri"]
                        if not uri_str.startswith(expected_namespace):
                            print(f"WARNING: Found unexpected namespace URI in {ontology} ontology: {uri_str}")
                        instances_content += f"""
        <cq:involvesProperty rdf:resource="{o}"/>"""
            
            instances_content += """
    </cq:CompetencyQuestion>
"""

    # Combine all content
    full_cq_content = vocab_content + instances_content
    
    # Append to original ontology
    append_cq_content_to_original(original_ontology_path, full_cq_content, output_file, ontology)

def append_cq_content_to_original(original_path: str, cq_content: str, output_path: str, ontology: str) -> None:
    """Append CQ content to original ontology while preserving structure."""
    try:
        with open(original_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Get ontology namespace info
        ontology_info = ONTOLOGY_NAMESPACES[ontology.lower()]
        
        print(f"Adding namespace declarations for {ontology.upper()}: {ontology_info['uri']}")
        
        # Add CQ namespace to the RDF element if not present
        if 'xmlns:cq=' not in original_content:
            # Find the RDF element and add CQ namespace
            rdf_pattern = r'(<rdf:RDF[^>]*)'
            match = re.search(rdf_pattern, original_content, re.DOTALL)
            if match:
                rdf_element = match.group(1)
                # Add CQ namespace declaration
                new_rdf_element = rdf_element + f'\n    xmlns:cq="http://example.org/cq-vocabulary#"'
                original_content = original_content.replace(rdf_element, new_rdf_element)
        
        # Also add the ontology-specific namespace if not present
        ontology_prefix = ontology_info["prefix"]
        ontology_uri = ontology_info["uri"]
        if f'xmlns:{ontology_prefix}=' not in original_content:
            # Find the RDF element and add ontology namespace
            rdf_pattern = r'(<rdf:RDF[^>]*)'
            match = re.search(rdf_pattern, original_content, re.DOTALL)
            if match:
                rdf_element = match.group(1)
                # Add ontology namespace declaration
                new_rdf_element = rdf_element + f'\n    xmlns:{ontology_prefix}="{ontology_uri}"'
                original_content = original_content.replace(rdf_element, new_rdf_element)
        
        # Find insertion point (before closing </rdf:RDF>)
        insertion_point = original_content.rfind('</rdf:RDF>')
        if insertion_point == -1:
            raise ValueError("Could not find closing </rdf:RDF> tag in original ontology")
        
        # Insert CQ content
        new_content = (
            original_content[:insertion_point] + 
            '\n' + cq_content + '\n' + 
            original_content[insertion_point:]
        )
        
        # Write enhanced ontology
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"Enhanced {ontology.upper()} ontology saved to {output_path}")
        
    except Exception as e:
        print(f"Error appending CQ content: {e}")
        raise

def extract_cq_vocabulary_xml(graph: Graph) -> str:
    """Extract CQ vocabulary definitions as XML."""
    cq_vocab_lines = []
    
    # Add section header
    cq_vocab_lines.extend([
        "",
        "    <!-- ",
        "    ///////////////////////////////////////////////////////////////////////////////////////",
        "    //",
        "    // Competency Question Vocabulary",
        "    //",
        "    ///////////////////////////////////////////////////////////////////////////////////////",
        "     -->",
        "",
        "    <!-- Competency Question class and properties for linking CQs to ontology elements -->",
        "",
        ""
    ])
    
    # CompetencyQuestion class
    cq_vocab_lines.extend([
        "    <!-- http://example.org/cq-vocabulary#CompetencyQuestion -->",
        "",
        "    <owl:Class rdf:about=\"http://example.org/cq-vocabulary#CompetencyQuestion\">",
        "        <rdfs:subClassOf rdf:resource=\"http://www.w3.org/2004/02/skos/core#Concept\"/>",
        "        <rdfs:label>Competency Question</rdfs:label>",
        "        <rdfs:comment>A question that an ontology should be able to answer.</rdfs:comment>",
        "    </owl:Class>",
        "",
        ""
    ])
    
    # involvesClass property  
    cq_vocab_lines.extend([
        "    <!-- http://example.org/cq-vocabulary#involvesClass -->",
        "",
        "    <owl:ObjectProperty rdf:about=\"http://example.org/cq-vocabulary#involvesClass\">",
        "        <rdfs:subPropertyOf rdf:resource=\"http://www.w3.org/2002/07/owl#topObjectProperty\"/>",
        "        <rdfs:domain rdf:resource=\"http://example.org/cq-vocabulary#CompetencyQuestion\"/>",
        "        <rdfs:range rdf:resource=\"http://www.w3.org/2002/07/owl#Class\"/>",
        "        <rdfs:label>involves class</rdfs:label>",
        "        <rdfs:comment>Links a competency question to an ontology class it involves.</rdfs:comment>",
        "    </owl:ObjectProperty>",
        "",
        ""
    ])
    
    # involvesProperty property
    cq_vocab_lines.extend([
        "    <!-- http://example.org/cq-vocabulary#involvesProperty -->",
        "",
        "    <owl:ObjectProperty rdf:about=\"http://example.org/cq-vocabulary#involvesProperty\">",
        "        <rdfs:subPropertyOf rdf:resource=\"http://www.w3.org/2002/07/owl#topObjectProperty\"/>",
        "        <rdfs:domain rdf:resource=\"http://example.org/cq-vocabulary#CompetencyQuestion\"/>",
        "        <rdfs:range rdf:resource=\"http://www.w3.org/2002/07/owl#Property\"/>",
        "        <rdfs:label>involves property</rdfs:label>",
        "        <rdfs:comment>Links a competency question to an ontology property it involves.</rdfs:comment>",
        "    </owl:ObjectProperty>",
        "",
        ""
    ])
    
    return '\n'.join(cq_vocab_lines)

def extract_cq_instances_xml(graph: Graph) -> str:
    """Extract CQ instances as XML."""
    cq_instances_lines = []
    
    # Add section header
    cq_instances_lines.extend([
        "",
        "    <!-- ",
        "    ///////////////////////////////////////////////////////////////////////////////////////",
        "    //",
        "    // Competency Question Instances",
        "    //",
        "    ///////////////////////////////////////////////////////////////////////////////////////",
        "     -->",
        "",
        "    <!-- Generated competency questions with links to ontology classes and properties -->",
        "",
        ""
    ])
    
    # Extract CQ instances from graph
    for subj, pred, obj in graph.triples((None, RDF.type, CQ.CompetencyQuestion)):
        cq_id = str(subj).split('#')[-1]
        
        # Get the question text
        question_text = None
        for s, p, o in graph.triples((subj, SKOS.definition, None)):
            question_text = str(o)
            break
            
        if not question_text:
            for s, p, o in graph.triples((subj, SKOS.prefLabel, None)):
                question_text = str(o).replace("CQ: ", "")
                break
        
        cq_instances_lines.extend([
            f"    <!-- {subj} -->",
            "",
            f"    <owl:NamedIndividual rdf:about=\"{subj}\">",
            f"        <rdf:type rdf:resource=\"http://example.org/cq-vocabulary#CompetencyQuestion\"/>",
        ])
        
        if question_text:
            cq_instances_lines.append(f"        <skos:definition>{question_text}</skos:definition>")
            
        # Add involved classes
        for s, p, o in graph.triples((subj, CQ.involvesClass, None)):
            cq_instances_lines.append(f"        <cq:involvesClass rdf:resource=\"{o}\"/>")
            
        # Add involved properties  
        for s, p, o in graph.triples((subj, CQ.involvesProperty, None)):
            cq_instances_lines.append(f"        <cq:involvesProperty rdf:resource=\"{o}\"/>")
            
        cq_instances_lines.extend([
            "    </owl:NamedIndividual>",
            "",
            ""
        ])
    
    return '\n'.join(cq_instances_lines)

def load_existing_ontology_graph(ontology_path: str) -> Graph:
    """
    Load an existing ontology into an RDF graph.
    
    Args:
        ontology_path (str): Path to the ontology file.
    
    Returns:
        Graph: RDF graph containing the ontology.
    """
    g = Graph()
    
    # Determine format from file extension
    format = ontology_path.split(".")[-1].lower()
    format_map = {
        "ttl": "turtle",
        "rdf": "xml",
        "owl": "xml",
        "jsonld": "json-ld",
        "nt": "nt",
        "n3": "n3"
    }
    
    rdf_format = format_map.get(format, "xml")
    
    try:
        g.parse(ontology_path, format=rdf_format)
        print(f"Loaded ontology from {ontology_path} (format: {rdf_format})")
        return g
    except Exception as e:
        print(f"Error loading ontology graph: {e}")
        return Graph()