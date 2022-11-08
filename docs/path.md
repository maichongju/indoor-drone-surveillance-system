# Path
Path it to represent a fly path, each path contain a name and a list of position. By default, all the path information is loaded from `path.json`

## Data Structure

The json file contain list of path. each path have a name and a list of position. each position is a list of number `[x, y, z]`

```json
[
  {
    "name": "test",
    "pos": [
      {
        "x": 0,
        "y": 1,
        "z": 1
      },
      {
        "x": 1,
        "y": 1,
        "z": 1
      },
      {
        "x": 1,
        "y": 0,
        "z": 1
      }
    ],
    "connected": true
  },
  {
    "name": "test1",
    "pos": [
      {
        "x": 0,
        "y": 1,
        "z": 1
      },
      {
        "x": 1,
        "y": 1,
        "z": 1
      },
      {
        "x": 1,
        "y": 0,
        "z": 1
      }
    ]
  }
]
```