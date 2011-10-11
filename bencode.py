import numbers

"""
This is not supposed to be useful for large bencoded messages.
"""

class BencodeBadTypeError(TypeError):
    pass

def bencode_str(obj):
    assert isinstance(obj, str)
    return "%d:%s" % (len(obj), obj)

def bencode_integral(obj):
    assert isinstance(obj, numbers.Integral)
    return "i%de" % obj

def bencode_list(obj):
    assert isinstance(obj, list)
    return "l" + ''.join(map(bencode, obj)) + "e"

def bencode_dict(obj):
    s = "d"
    for key in sorted(obj.keys()):
        s += bencode_str(key)
        s += bencode(obj[key])
    s += 'e'
    return s

def bencode(obj):
    type_funcs = [
        (str, bencode_str),
        (numbers.Integral, bencode_integral),
        (list, bencode_list),
        (dict, bencode_dict),
    ]
    for type_, func in type_funcs:
        if isinstance(obj, type_):
            return func(obj)
    raise BencodeBadTypeError("Couldn't encode %s" % repr(obj))

