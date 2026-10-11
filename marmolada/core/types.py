type JSONDict = dict[str, "JSONValue"]
type JSONList = list["JSONValue"]
type JSONValue = str | int | float | bool | JSONDict | JSONList | None
type JSONCompound = JSONDict | JSONList
