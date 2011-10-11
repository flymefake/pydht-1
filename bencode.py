import numbers

"""
This is not supposed to be useful for large bencoded messages.
"""

class BencodeBadTypeError(TypeError):
    pass

class BdecodeError(ValueError):
    pass

def _bencode_str(obj):
    assert isinstance(obj, str)
    return "%d:%s" % (len(obj), obj)

def _bencode_integral(obj):
    assert isinstance(obj, numbers.Integral)
    return "i%de" % obj

def _bencode_list(obj):
    assert isinstance(obj, list)
    return "l" + ''.join(map(bencode, obj)) + "e"

def _bencode_dict(obj):
    s = "d"
    for key in sorted(obj.keys()):
        s += _bencode_str(key)
        s += _bencode(obj[key])
    s += 'e'
    return s

def bencode(obj):
    type_funcs = [
        (str, _bencode_str),
        (numbers.Integral, _bencode_integral),
        (list, _bencode_list),
        (dict, _bencode_dict),
    ]
    for type_, func in type_funcs:
        if isinstance(obj, type_):
            return func(obj)
    raise BencodeBadTypeError("Couldn't encode %s" % repr(obj))

def _bdecode_str(buf, pos):
    i = pos
    while buf[i] != ':': i += 1
    length = int(buf[pos:i])
    return buf[i+1:i+length+1], i+length+1

def _bdecode_integral(buf, pos):
    assert buf[pos] == 'i'
    pos += 1 # consume the `i'
    i = pos
    while buf[i] != 'e':
        i += 1
    return int(buf[pos:i]), i+1

def _bdecode_list(buf, pos):
    assert buf[pos] == 'l'
    pos += 1 # consume the `l'
    out = []
    while True:
        item, pos = _bdecode(buf, pos)
        out.append(item)
        if 'e' == buf[pos]:
            break
    return out, pos+1

def _bdecode_dict(buf, pos):
    assert buf[pos] == 'd'
    pos += 1 # consume the `d'
    out = {}
    while True:
        key, pos = _bdecode_str(buf, pos)
        val, pos = _bdecode(buf, pos)
        out[key] = val
        if 'e' == buf[pos]:
            break
    return out, pos+1

def _bdecode(buf, pos=0):
    if buf[pos] in '123456789':
        return _bdecode_str(buf, pos)
    elif 'i' == buf[pos]:
        return _bdecode_integral(buf, pos)
    elif 'l' == buf[pos]:
        return _bdecode_list(buf, pos)
    elif 'd' == buf[pos]:
        return _bdecode_dict(buf, pos)
    else:
        raise BdecodeError("Bad token `%s' at %d" % (buf[pos], pos))

def bdecode(buf):
    item, pos = _bdecode(buf)
    return item
