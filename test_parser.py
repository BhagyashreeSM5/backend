from code_parsers.code_parser import parse_file

# Test with a simple Python code
test_code = """
def greet(name):
    print(name)

def main():
    greet("hello")
    print("done")
"""

result = parse_file("test.py", test_code)
print("Functions found:", result["nodes"])
print("Calls found:", result["edges"])
print("Language:", result["language"])