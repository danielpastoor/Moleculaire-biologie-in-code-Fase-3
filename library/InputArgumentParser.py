from enum import Enum
from sys import argv
from typing import Callable, Self, Union


class InputArgumentNotExists(Exception):
    def __init__(self, argument: str) -> None:
        super().__init__(f"The {argument} is a required parameter")


class InputArgumentInvalid(Exception):
    def __init__(self, argument: str) -> None:
        super().__init__(f"The {argument} has invalid data")


class ArgumentInfo:
    # devines argument type
    argument_name: str
    validating_functions = list[Callable[[str, str, Self], bool]]()
    value = ""
    required = True
    description = ""

    def set_name(self, argument_name: str) -> Self:
        self.argument_name = argument_name

        return self

    def add_custom_validation(self, function: Callable[[str, str, Self], bool]) -> Self:
        self.validating_functions.append(function)
        return self

    def set_default(self, default: Union[str, int, float]) -> Self:
        self.value = default
        self.required = False

        return self

    def set_type(self, type_input: type) -> Self:
        self.value = type_input()

        return self

    def is_required(self) -> Self:
        if len(self.value) > 0:
            raise Exception(
                "You were trying to set the required true but you already have defined a default")

        self.required = True
        return self

    def set_description(self, description: str) -> Self:
        self.description = description

        return self


class InputArgumentParser:
    __arguments: dict[str, ArgumentInfo]

    def __init__(self, application_name: str, description: str) -> None:
        self.__application_name = application_name
        self.__description = description
        self.__arguments = dict[str, ArgumentInfo]()

    # region add

    def add_argument(self, parameters: Callable[[ArgumentInfo], ArgumentInfo]) -> None:
        argument = parameters(ArgumentInfo())

        if argument:
            self.__arguments[argument.argument_name] = argument

    # endregion

    # region get
    def parse(self) -> list[any]:
        arguments = self.__parse_system_args()

        if "help" in arguments or len(arguments) <= 0:
            self.__show_help()

        return self.__validate_and_return_arguments(arguments)

    # endregion

    # region private
    def __validate_and_return_arguments(self, arguments: dict[str, str]) -> dict[str, any]:
        return_dict = dict[str, any]()

        arguments_settings = self.__arguments

        for key in arguments_settings:
            argument_setting = self.__arguments[key]
            
            if argument_setting.required and (argument_setting.argument_name in arguments) == False:
                raise InputArgumentNotExists(argument_setting.argument_name)

            if argument_setting.argument_name in arguments:
                if not arguments[argument_setting.argument_name]:
                    raise InputArgumentInvalid(
                        argument_setting.argument_name)

                for custom_validation in argument_setting.validating_functions:
                    custom_validation_output = custom_validation()

                    if custom_validation_output:
                        raise InputArgumentInvalid(
                            argument_setting.argument_name)

                try:
                    return_dict[argument_setting.argument_name] = type(
                        argument_setting.value)(arguments[argument_setting.argument_name])
                except:
                    raise InputArgumentInvalid(
                        argument_setting.argument_name)

            else:
                return_dict[argument_setting.argument_name] = ""

        return return_dict

    def __parse_system_args(self) -> dict[str, str]:
        system_args = argv

        if len(system_args) > 0:
            del system_args[0]

        # list arguments to dictionary
        arguments = dict((item.split("=")[0].replace(
            "-", ""), item.split("=")[1]) for item in list(filter(lambda x: "=" in x, argv)))

        # add argument that has "--" and not a "="
        for item in list(filter(lambda x: "=" not in x, argv)):
            key = item.replace(
                "-", "")
            if not item in arguments:
                arguments[key] = ""

        return arguments

    def __show_help(self):
        """show_help is a function that returns a help
        """
        argument_helper_text = ""

        for key in self.__arguments:
            item = self.__arguments[key]
            argument_helper_text += \
                f">> --{key} : type ({type(item.value).__name__}) :  :{' [Optional] ' if not item.required else ' '} {item.description if item.description else 'No description provided'} \n" \
                + f">> > -{key} \n"

        # print help
        print(f"""------------------------------------------------------
-- Helper: {self.__application_name}
------------------------------------------------------
>> Description = {self.__description}
arguments:
{argument_helper_text}
-----------------------------------------------------
""")
        # stop program
        exit()

    # endregion


if __name__ == "__main__":
    pass
