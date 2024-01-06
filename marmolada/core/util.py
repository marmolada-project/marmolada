def merge_dicts(*src_dicts):
    """Create a deep merge of several dictionaries.

    The structure of the dictionaries must be compatible, i.e. sub-dicts
    may not be differently typed between the source dictionaries."""
    if not src_dicts:
        raise ValueError("Can't merge nothing")

    if not all(isinstance(src_dict, dict) for src_dict in src_dicts):
        raise TypeError("All objects to be merged have to be dictionaries")

    res_dict = {}

    for src_dict in src_dicts:
        for key, src_value in src_dict.items():
            if isinstance(src_value, dict):
                if key not in res_dict:
                    res_dict[key] = src_value.copy()
                else:
                    res_dict[key] = merge_dicts(res_dict[key], src_value)
            elif key in res_dict and isinstance(res_dict[key], dict):
                raise TypeError("All objects to be merged have to be dictionaries")
            else:
                res_dict[key] = src_value

    return res_dict
