import numpy as np

import json

from .. import util


def load_off(file_obj, **kwargs):
    """
    Load an OFF file into the kwargs for a Trimesh constructor


    Parameters
    ----------
    file_obj : file object
      Contains an OFF file

    Returns
    ----------
    loaded : dict
      kwargs for Trimesh constructor
    """
    text = file_obj.read()
    if hasattr(text, 'decode'):
        text = text.decode('utf-8')

    text = text.lstrip()
    # split the first key
    header, raw = text.split(None, 1)

    if header.upper() not in ['OFF', 'COFF']:
        raise NameError(
            'Not an OFF file! Header was: `{}`'.format(header))

    # split into lines and remove whitespace
    splits = [i.strip() for i in str.splitlines(raw)]
    # remove empty lines and comments
    splits = [i for i in splits if len(i) > 0 and i[0] != '#']

    # the first non-comment line should be the counts
    header = np.array(splits[0].split(), dtype=np.int64)
    vertex_count, face_count = header[:2]

    vertices = np.array([
        i.split()[:3] for i in
        splits[1: vertex_count + 1]],
        dtype=np.float64)

    # will fail if incorrect number of vertices loaded
    vertices = vertices.reshape((vertex_count, 3))

    # get lines with face data
    faces = [i.split() for i in
             splits[vertex_count + 1:vertex_count + face_count + 1]]
    # the first value is count
    faces = [line[1:int(line[0]) + 1] for line in faces]

    # convert faces to numpy array
    # will fail on mixed garbage as FSM intended -_-
    faces = np.array(faces, dtype=np.int64)

    # save data as kwargs for a trimesh.Trimesh
    kwargs = {'vertices': vertices,
              'faces': faces}

    return kwargs


def load_msgpack(blob, **kwargs):
    """
    Load a dict packed with msgpack into kwargs for
    a Trimesh constructor

    Parameters
    ----------
    blob : bytes
      msgpack packed dict containing
      keys 'vertices' and 'faces'

    Returns
    ----------
    loaded : dict
     Keyword args for Trimesh constructor, aka
     mesh=trimesh.Trimesh(**loaded)
    """

    import msgpack
    if hasattr(blob, 'read'):
        data = msgpack.load(blob)
    else:
        data = msgpack.loads(blob)
    loaded = load_dict(data)
    return loaded


def load_dict(data, **kwargs):
    """
    Load multiple input types into kwargs for a Trimesh constructor.
    Tries to extract keys:
    'faces'
    'vertices'
    'face_normals'
    'vertex_normals'

    Parameters
    ----------
    data: accepts multiple forms
          -dict: has keys for vertices and faces as (n,3) numpy arrays
          -dict: has keys for vertices/faces (n,3) arrays encoded as dicts/base64
                 with trimesh.util.array_to_encoded/trimesh.util.encoded_to_array
          -str:  json blob as dict with either straight array or base64 values
          -file object: json blob of dict
    file_type: not used

    Returns
    -----------
    loaded: dict with keys
            -vertices: (n,3) float
            -faces:    (n,3) int
            -face_normals: (n,3) float (optional)
    """
    if data is None:
        raise ValueError('data passed to load_dict was None!')
    if util.is_instance_named(data, 'Trimesh'):
        return data
    if util.is_string(data):
        if '{' not in data:
            raise ValueError('Object is not a JSON encoded dictionary!')
        data = json.loads(data.decode('utf-8'))
    elif util.is_file(data):
        data = json.load(data)

    # what shape should the data be to be usable
    mesh_data = {'vertices': (-1, 3),
                 'faces': (-1, (3, 4)),
                 'face_normals': (-1, 3),
                 'face_colors': (-1, (3, 4)),
                 'vertex_normals': (-1, 3),
                 'vertex_colors': (-1, (3, 4))}

    # now go through data structure and if anything is encoded as base64
    # pull it back into numpy arrays
    if isinstance(data, dict):
        loaded = {}
        data = util.decode_keys(data, 'utf-8')
        for key, shape in mesh_data.items():
            if key in data:
                loaded[key] = util.encoded_to_array(data[key])
                if not util.is_shape(loaded[key], shape):
                    raise ValueError('Shape of %s is %s, not %s!',
                                     key,
                                     str(loaded[key].shape),
                                     str(shape))
        if len(key) == 0:
            raise ValueError('Unable to extract any mesh data!')
        return loaded
    else:
        raise ValueError('%s object passed to dict loader!',
                         data.__class__.__name__)


_misc_loaders = {'off': load_off,
                 'dict': load_dict,
                 'dict64': load_dict,
                 'json': load_dict,
                 'msgpack': load_msgpack}
