from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_java as tsjava
import os

# 🧠 WHY: In version 0.21, Language() takes the language function directly
PY_LANGUAGE   = Language(tspython.language(), "python")
JS_LANGUAGE   = Language(tsjavascript.language(), "javascript")
JAVA_LANGUAGE = Language(tsjava.language(), "java")

LANGUAGE_MAP = {
    ".py":   PY_LANGUAGE,
    ".js":   JS_LANGUAGE,
    ".jsx":  JS_LANGUAGE,
    ".java": JAVA_LANGUAGE,
}

LANGUAGE_NAMES = {
    ".py": "Python", ".js": "JavaScript",
    ".jsx": "JavaScript", ".java": "Java"
}

# 🧠 WHY: tree-sitter uses query strings to find patterns in the AST
# Each language has different syntax so different query strings
FUNCTION_QUERIES = {
    ".py":  "(function_definition name: (identifier) @func_name)",
    ".js":  """
        (function_declaration name: (identifier) @func_name)
        (method_definition key: (property_identifier) @func_name)
    """,
    ".jsx": """
        (function_declaration name: (identifier) @func_name)
        (method_definition key: (property_identifier) @func_name)
    """,
    ".java": "(method_declaration name: (identifier) @func_name)",
}

CALL_QUERIES = {
    ".py":   "(call function: (identifier) @call_name)",
    ".js":   "(call_expression function: (identifier) @call_name)",
    ".jsx":  "(call_expression function: (identifier) @call_name)",
    ".java": "(method_invocation name: (identifier) @call_name)",
}


def parse_file(file_path: str, source_code: str) -> dict:
    """
    🧠 HOW IT WORKS:
    1. Detect language from file extension
    2. Parse source code into AST
    3. Use queries to find function definitions → NODES
    4. Use queries to find function calls → EDGES
    5. Return graph data
    """
    _, ext = os.path.splitext(file_path.lower())

    if ext not in LANGUAGE_MAP:
        return {"nodes": [], "edges": [], "language": "unknown"}

    # Step 1: Parse the source code into AST
    parser = Parser()
    parser.set_language(LANGUAGE_MAP[ext])
    # 🧠 encode() converts string to bytes — tree-sitter needs bytes not string
    tree = parser.parse(source_code.encode())

    # Step 2: Find all function definitions
    # 🧠 .captures() returns list of (node, capture_name) tuples in v0.21
    func_query = LANGUAGE_MAP[ext].query(FUNCTION_QUERIES[ext])
    func_captures = func_query.captures(tree.root_node)

    functions = []
    for node, capture_name in func_captures:
        func_name = source_code[node.start_byte:node.end_byte]
        if func_name and func_name not in functions:
            functions.append(func_name)

    # Step 3: Find all function calls
    call_query = LANGUAGE_MAP[ext].query(CALL_QUERIES[ext])
    call_captures = call_query.captures(tree.root_node)

    calls = []
    for node, capture_name in call_captures:
        call_name = source_code[node.start_byte:node.end_byte]
        if call_name:
            calls.append(call_name)

    # Step 4: Build edges
    # 🧠 Edge = function A calls function B
    # We only add edge if BOTH functions are defined in this codebase
    edges = []
    for func in functions:
        for call in calls:
            if call != func and call in functions:
                edge = {"from": func, "to": call}
                if edge not in edges:
                    edges.append(edge)

    return {
        "nodes": functions,
        "edges": edges,
        "language": LANGUAGE_NAMES.get(ext, "Unknown")
    }


def parse_multiple_files(files: list) -> dict:
    """
    🧠 WHY: Real codebases have many files.
    We merge all functions and calls into one big graph.

    files = list of {"path": "...", "content": "..."}
    """
    all_nodes = []
    all_edges = []
    file_map  = {}

    for file in files:
        result = parse_file(file["path"], file["content"])

        for node in result["nodes"]:
            if node not in all_nodes:
                all_nodes.append(node)
                file_map[node] = {
                    "file": file["path"],
                    "language": result["language"]
                }

        for edge in result["edges"]:
            if edge not in all_edges:
                all_edges.append(edge)

    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "file_map": file_map
    }