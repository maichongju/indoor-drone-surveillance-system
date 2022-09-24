# REST API for DSBS

The web server is using `Flask` library. End points provided the information of the drones, including video stream information, and the status of the drones. In the future, it can also provided control commands to the drones.

## End Points

> Click on each end point to see more details.

- [`drones`](endpoints/drones.md)
- [`drone/<id>`](endpoints/singledrone.md)

### Enabling Debug Mode

There are some end points that are only available in debug mode. To enable debug mode, set `debug` to `true` in the `config.toml` file.

- [`/debug/status/<int:code>`](endpoints/debug/status.md)

## Response

All the response are in JSON format. If there is no error, a response with status code `200` is returned. The response alway following the following format:

```json
{
  "status": 200,
  "data": "Any data needed to return. null if there is no data"
}
```

### Error

If an client side error or the none-critical server error occurs, an error response is return. If the error is critical, the server might crashed and needs to be restart. The response follow the general formate of error respond format.

```json
{
  "status": 404,
  "error": {
    "code": "404",
    "desc": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."
  }
}
```
