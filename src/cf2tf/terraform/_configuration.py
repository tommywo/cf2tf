from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional

from cf2tf.conversion import expressions as functions

from .code import Data
from cf2tf.terraform.hcl2 import Block, Variable, Output
from cf2tf.convert import pascal_to_snake
import logging

log = logging.getLogger("cf2tf")


class Configuration:
    def __init__(self, output_path: Path, resources: List[Block]) -> None:
        self.resources = resources
        self.output_path = output_path

    def save(self):

        # We should probably handle the actual saving of resources here

        self.resolve_objects()

        for resource in self.resources:
            try:
                print()
                print(resource.write())
            except Exception as e:
                log.error(
                    f"Unable to write {resource.name} {resource.type} {resource.attributes}"
                )
                raise e

    def resolve_objects(self):

        for resource in self.resources:

            # These dont have anything to resolve
            if isinstance(resource, (Variable, Data)):
                continue

            self.resolve_values(resource.arguments, functions.ALL_FUNCTIONS)

    # def resolve_arguments(self, arguments: Dict[str, Any]):

    #     for arg_name in list(arguments):

    #         arg_value = arguments[arg_name]

    #         if self.contains_functions(arg_value)

    def resolve_values(self, data: Any, allowed_func: functions.Dispatch) -> Any:
        """Recurses through a Cloudformation template. Solving all
        references and variables along the way.

        Args:
            data (Any): Could be a dict, list, str or int.

        Returns:
            Any: Return the rendered data structure.
        """

        if isinstance(data, dict):

            # for key, value in data.items():

            for key in list(data):

                value = data[key]

                if key == "Ref":
                    return functions.ref(self, value)

                if "Fn::" not in key:
                    data[key] = self.resolve_values(value, allowed_func)
                    continue

                if key not in allowed_func:
                    raise ValueError(f"{key} not allowed here.")

                value = self.resolve_values(value, functions.ALLOWED_FUNCTIONS[key])

                return allowed_func[key](self, value)

            return data
        elif isinstance(data, list):
            return [self.resolve_values(item, allowed_func) for item in data]
        else:
            return data

    def contains_functions(self, data: Dict[str, Any]):

        functions = ["Ref", "Fn::"]

        for key in list(data):

            if key in functions:
                return True

        return False

    def block_lookup(self, name: str) -> Optional[Block]:

        name = pascal_to_snake(name)

        # log.debug(f"Searching for terraform block named {name}")

        for resource in self.resources:
            if isinstance(resource, Output):
                continue

            # log.debug(f"Checking {resource.name}")
            if resource.name == name:
                return resource


def resource_lookup(config: "Configuration", name: str):

    for resource in config.resources:

        if hasattr(resource, "cf_resource") and resource.cf_resource.logical_id == name:
            return resource
        else:
            if resource.name == name:
                return resource
