def convert_html_to_python(variables={}, code=""):
    for variable in variables:
        code = code.replace("{{"+str(variable)+"}}", variables[variable])
    return code

some_code = """
<!DOCTYPE html>
<html>

<body>
    <h1>My First Heading</h1>
    <p>My first paragraph.</p>
    {{var}}
</body>
</html>
"""
print(convert_html_to_python({"var":"1"}, some_code))