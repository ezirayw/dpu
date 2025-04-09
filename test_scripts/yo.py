# person.py
from typing import cast, TypedDict, Optional


class Person(TypedDict):
    name: str
    age: Optional[int]


def to_person(d: dict) -> Person:
    if ("name" in d) and isinstance(d["name"], str) and (("age" not in d) or (("age" in d) and (isinstance(d["age"], str)))):
        return cast(d, Person)  # this will work at runtime even though it shouldn't
    raise ValueError("d is not a Person")
