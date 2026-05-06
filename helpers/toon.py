import json

def to_toon(data, indent=0):
    """
    Converts a Python object to TOON (Token-Oriented Object Notation) format.
    Optimized for LLM token consumption.
    """
    prefix = "  " * indent
    
    if isinstance(data, list):
        if not data:
            return "[]"
        
        # Check if it's a uniform list of dictionaries
        if all(isinstance(item, dict) for item in data) and len(data) > 0:
            # Get common keys (using the first item as reference)
            keys = list(data[0].keys())
            header = "{" + ", ".join(keys) + "}"
            
            lines = [f"{prefix}{header} [{len(data)}]"]
            for item in data:
                # Format values, handle None and escaping if needed
                vals = []
                for k in keys:
                    val = item.get(k)
                    if val is None:
                        vals.append("null")
                    elif isinstance(val, (int, float, bool)):
                        vals.append(str(val).lower() if isinstance(val, bool) else str(val))
                    else:
                        # String or other: escape if it contains commas or newlines
                        s_val = str(val).replace("\n", " ")
                        if "," in s_val or '"' in s_val:
                            s_val = f'"{s_val.replace("\"", '\\"')}"'
                        vals.append(s_val)
                lines.append(f"{prefix}- {', '.join(vals)}")
            return "\n".join(lines)
        else:
            # Non-uniform list
            lines = [f"{prefix}[{len(data)}]"]
            for item in data:
                lines.append(f"{prefix}- {to_toon(item, indent + 1).strip()}")
            return "\n".join(lines)
            
    elif isinstance(data, dict):
        if not data:
            return "{}"
        lines = []
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                lines.append(f"{prefix}{k}:\n{to_toon(v, indent + 1)}")
            else:
                formatted_v = "null" if v is None else str(v)
                lines.append(f"{prefix}{k}: {formatted_v}")
        return "\n".join(lines)
    
    else:
        # Primitives
        if data is None: return "null"
        if isinstance(data, bool): return str(data).lower()
        return str(data)
