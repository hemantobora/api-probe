# XML/SOAP Support Guide

## Overview

api-probe supports XML and SOAP APIs using XPath expressions for value extraction and validation.

## Content-Type Detection

The tool automatically detects XML/SOAP responses based on Content-Type header:
- `application/xml`
- `text/xml`
- `application/soap+xml`

When XML is detected, path expressions are treated as XPath instead of JSONPath.

## XPath Basics

### Simple Paths

```yaml
# Extract element text
path: "//elementName"

# Extract from nested elements  
path: "//parent/child"

# Extract attribute
path: "//element/@attribute"
```

### Namespace Handling

XML responses often use namespaces. api-probe automatically extracts namespaces from the root element.

**Default namespace** (no prefix in XML):
```xml
<root xmlns="http://example.com/ns">
  <element>value</element>
</root>
```

Use `default:` prefix in XPath:
```yaml
path: "//default:element"
```

**Named namespaces**:
```xml
<root xmlns:custom="http://example.com/custom">
  <custom:element>value</custom:element>
</root>
```

Use the namespace prefix directly:
```yaml
path: "//custom:element"
```

### Common XPath Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `//element` | Find all elements | `//user` |
| `/root/child` | Absolute path | `/envelope/body/response` |
| `//parent/child` | Descendant | `//user/email` |
| `//element[1]` | First element (1-indexed) | `//item[1]/price` |
| `//element[@attr='value']` | Attribute filter | `//item[@id='123']` |
| `//element/text()` | Text content only | `//user/name/text()` |
| `//element/@attribute` | Extract attribute | `//user/@id` |
| `//*` | All elements | `//*` |

## Examples

### SOAP Request/Response

```yaml
tests:
  - name: "SOAP API Call"
    type: rest
    endpoint: "http://example.com/soap"
    method: POST
    headers:
      Content-Type: "text/xml; charset=utf-8"
      SOAPAction: "http://example.com/GetUser"
    body: |
      <?xml version="1.0"?>
      <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
          <GetUser xmlns="http://example.com/">
            <userId>123</userId>
          </GetUser>
        </soap:Body>
      </soap:Envelope>
    validation:
      status: 200
      body:
        # Extract from SOAP response
        present:
          - "//default:GetUserResponse/default:name"
          - "//default:GetUserResponse/default:email"
        equals:
          "//default:GetUserResponse/default:name": "John Doe"
```

### XML REST API

```yaml
tests:
  - name: "XML REST Endpoint"
    type: rest
    endpoint: "http://example.com/api/data.xml"
    validation:
      status: 200
      body:
        # XPath validation
        present:
          - "//items/item/id"
          - "//items/item/name"
        
        # Type checking
        type:
          "//items/item[1]/id": string
        
        # Value matching
        equals:
          "//items/item[1]/name": "First Item"
        
        # Pattern matching
        matches:
          "//items/item[1]/id": "^[0-9]+$"
```

### Multiple Elements

When XPath matches multiple elements, an array is returned:

```yaml
validation:
  body:
    # This returns array of all IDs: ["1", "2", "3"]
    present:
      - "//items/item/id"
```

For validation:
- `present` - checks if path exists (even if returns array)
- `equals` - fails on arrays (single values only)
- `type` - checks type of first element

### SOAP Fault Handling

```yaml
validation:
  body:
    # Ensure no SOAP fault
    absent:
      - "//soap:Fault"
      - "//default:Fault"
```

## Validation Keywords with XML

All validation keywords work with XPath:

### Status
```yaml
validation:
  status: 200
```

### Headers
```yaml
validation:
  headers:
    present:
      - "Content-Type"
    contains:
      Content-Type: "xml"
```

### Body (XPath)

**present**
```yaml
body:
  present:
    - "//user/name"
    - "//user/email"
```

**absent**
```yaml
body:
  absent:
    - "//error"
    - "//fault"
```

**equals**
```yaml
body:
  equals:
    "//user/name": "John Doe"
    "//user/age": "30"
```

**matches**
```yaml
body:
  matches:
    "//user/email": "^[a-z]+@example\\.com$"
    "//user/id": "^[0-9]+$"
```

**type**
```yaml
body:
  type:
    "//user/name": string
    "//user/active": string  # Note: XML values are always strings
```

**contains**
```yaml
body:
  contains:
    "//description": "premium"  # Substring match
```

**range**
```yaml
body:
  range:
    "//user/age": [0, 120]  # Numeric comparison (string converted to number)
```

## Output Variables

Extract XML values to variables:

```yaml
output:
  USER_ID: "body.//user/id"
  USER_NAME: "body.//user/name"
```

Then use in subsequent tests:
```yaml
- name: "Use Extracted ID"
  type: rest
  endpoint: "http://example.com/user/${USER_ID}"
```

## Tips

1. **Default Namespace** - Always use `default:` prefix for elements in default namespace
2. **Array Results** - XPath can return arrays; use `[1]` for first element
3. **Text vs Elements** - `//element` returns element, `//element/text()` returns text only
4. **Debugging** - Test XPath expressions in a browser console or XPath tester first
5. **SOAP Envelopes** - Navigate through `soap:Envelope/soap:Body/...`

## Limitations

1. **XPath 1.0** - Uses XPath 1.0 (not 2.0/3.0)
2. **Namespace Required** - Elements with default namespace must use `default:` prefix
3. **String Values** - All XML text content is treated as strings (convert in validation)

## Dependencies

XML/SOAP support requires:
```
lxml==5.1.0
```

Already included in requirements.txt.

## Complete Example

See [examples/passing/xml-soap.yaml](../examples/passing/xml-soap.yaml) for a working example.
