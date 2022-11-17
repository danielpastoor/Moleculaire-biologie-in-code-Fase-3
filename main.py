"""
Name:
Version python: 3.11.0
Example python3 main.py --probes=input_data/Probes.csv --sampleannot=input_data/SampleAnnot.csv  --microarrayexpression=input_data/MicroarrayExpression.csv --regions=LHM,PHA --cutoff=17
"""
# TODO: add check for cutof in generating data microarray
# TODO: argument validation fields
import json
import multiprocessing
from csv import DictReader, Sniffer
from itertools import combinations, groupby, islice
from os import path
from statistics import mean
import time
from typing import Any

from library.InputArgumentParser import ArgumentInfo, InputArgumentParser


# !!!!!! MAX READ TMP
max_line_read = 100000

# region Validating and getting agruments


def validate_file_csv_extension(value: str, argument_settings: ArgumentInfo) -> bool:
    if ".csv" not in value.lower():
        raise Exception(
            f"The file of input argument {argument_settings.argument_name} is not a .csv")

    return True


def validate_path(value: str, argument_settings: ArgumentInfo) -> bool:
    if not path.exists(value):
        raise Exception(
            f"The file of input argument {argument_settings.argument_name} was not found")

    return True


def get_arguments() -> dict[str, Any]:  # type: ignore
    input_arg_parser = InputArgumentParser(
        "GenBank script", "This is a script that converts genbank to multi fasta")

    input_arg_parser.add_argument(lambda x: x.set_name(
        "probes").add_custom_validation(validate_path).add_custom_validation(validate_file_csv_extension).is_required())

    input_arg_parser.add_argument(lambda x: x.set_name(
        "sampleannot").add_custom_validation(validate_path).add_custom_validation(validate_file_csv_extension).is_required())

    input_arg_parser.add_argument(lambda x: x.set_name(
        "microarrayexpression").add_custom_validation(validate_path).add_custom_validation(validate_file_csv_extension).is_required())

    input_arg_parser.add_argument(lambda x: x.set_name(
        "regions").is_required().set_description("Must be ',' sepperated"))

    input_arg_parser.add_argument(lambda x: x.set_name(
        "cutoff").set_type(float).is_required())

    input_arg_parser.add_argument(lambda x: x.set_name(
        "field_name").set_default("gene_symbol"))

    return input_arg_parser.parse()

# endregion

# region util


def chunk(data, size=10000):
    it = iter(data)
    for i in range(0, len(data), size):
        yield {k: data[k] for k in islice(it, size)}
# region

# region Classes


class CSVFileClass:
    # type: ignore
    # type: ignore
    # type: ignore
    def __init__(self, headings: list[str], data: list[dict[str, Any]]) -> None:
        self.__headings = headings
        self.__data = data

    def get_headings(self) -> list[str]:
        return self.__headings

    def get_data(self) -> list[dict[str, Any]]:  # type: ignore
        return self.__data


class MicroExpressionClass:
    def __init__(self, line: list[str]) -> None:
        self.__probe_id = int(line[0])
        self.__expressions = [float(x) for x in line[1::]]

    def get_probe_id(self) -> int:
        return self.__probe_id

    def get_expressions(self) -> list[float]:
        return self.__expressions

    def get_expression(self, line_pos: int) -> float:
        if len(self.__expressions) >= line_pos:
            return self.__expressions[line_pos]

        return -1

    def get_average(self) -> float:
        return mean(self.__expressions)


class DiffStructure:
    diff_name: str
    unique_region_data: dict[str, set[int]]
    shared_region_data: set[int]

    def __init__(self, region_one_key: str, region_one_data: set[int], region_two_key: str, region_two_data: set[int]) -> None:
        self.shared_region_data = region_one_data.intersection(region_two_data)

        print(json.dumps(list(region_two_data)))

        print(json.dumps(list(region_one_data)))

        self.diff_name = region_one_key + " - " + region_two_key

        self.unique_region_data = {
            region_one_key: region_one_data.difference(region_two_data),
            region_two_key: region_two_data.difference(region_one_data)
        }


# endregion

# region Reading csv file


def read_csv_file(file_path: str, has_header: bool) -> CSVFileClass | None:
    csv_data = None

    with open(file_path, "r", encoding="UTF-8") as file_data:
        delimiter = Sniffer().sniff(file_data.read(20)).delimiter

        file_data.seek(0)

        csv_file = DictReader(file_data, delimiter=delimiter)

        headers = [
            x for x in csv_file.fieldnames] if csv_file.fieldnames is not None and has_header else list[str]()

        csv_data = CSVFileClass(headers, list(csv_file))

    return csv_data


# endregion

# region Microarray Expression

def sort_and_filter_microarray_expression(delimiter, grouped_micro_expressions: dict[str, list[str]]) -> dict[int, MicroExpressionClass]:
    return_micro_expression = dict[int, MicroExpressionClass]()

    for key, grouped in grouped_micro_expressions.items():
        return_micro_expression[int(key)] = list(
            sorted([MicroExpressionClass(item.split(delimiter)) for item in grouped], key=lambda x: x.get_average(), reverse=True))[0]

    return return_micro_expression


def read_microarray_expression(file_path: str) -> dict[int, MicroExpressionClass]:
    return_micro_expression = dict[int, MicroExpressionClass]()

    with open(file_path, "r", encoding="UTF-8") as file_data:
        delimiter = Sniffer().sniff(file_data.read(20)).delimiter

        file_data.seek(0)

        grouped_micro_expressions = {key: list(items) for key, items in groupby(
            file_data, lambda x: x.split(delimiter, maxsplit=1)[0])}

        pool = multiprocessing.Pool()

        chucked_data = [(delimiter, item) for item in chunk(grouped_micro_expressions, len(
            grouped_micro_expressions) // multiprocessing.cpu_count())]

        outputs = pool.starmap(
            sort_and_filter_microarray_expression, chucked_data)

        for item in outputs:
            return_micro_expression.update(item)

    return return_micro_expression


def filter_microarray_expression_by_cutoff(key: str, check_index: int, cutoff: int, micro_expressions: dict[int, MicroExpressionClass]) -> tuple[str, list[int]]:
    return (key, [probe_id for probe_id, val in micro_expressions.items() if val.get_expression(check_index) >= float(cutoff)])


def process_microarray_with_sample_annot(micro_expressions: dict[int, MicroExpressionClass], cutoff: int, sample_annots: dict[str, dict[int, dict[str, Any]]]) -> dict[str, list[int]]:
    return_dict = dict[str, list[int]]()

    process_data = list[tuple[str, int, int,
                              dict[int, MicroExpressionClass]]]()

    for structure_acronym, sample_annot in sample_annots.items():
        for item in sample_annot:
            process_data.append(
                (structure_acronym, item, cutoff, micro_expressions))

    pool = multiprocessing.Pool()

    outputs = pool.starmap(
        filter_microarray_expression_by_cutoff, process_data)

    for item in outputs:
        if item[0] in return_dict:
            return_dict[item[0]] += item[1]
        else:
            return_dict[item[0]] = item[1]

    return return_dict
    # endregion

    # region Sample Annot


def read_sample_annot(file_path: str, regions: list[str]) -> dict[str, dict[int, dict[str, Any]]]:
    file_data = read_csv_file(
        file_path, True)

    return_regions = {
        region: dict[int, dict[str, Any]]()
        for region in regions
    }

    if file_data is not None:
        for index, row in enumerate(file_data.get_data()):
            # why + 2
            if str(row["structure_acronym"]).upper() in return_regions:
                print(index + 1)
                return_regions[str(row["structure_acronym"]
                                   ).upper()][index + 1] = row

    # return data
    return return_regions
# endregion

# region Probe


def read_probes(file_path: str, structures_with_probes: dict[str, list[int]]) -> dict[int, dict[str, Any]]:
    probe_ids = []

    for _, item in structures_with_probes.items():
        probe_ids += item

    file_data = read_csv_file(
        file_path, True)

    if file_data is not None:
        return {int(item["probe_id"]): item for item in file_data.get_data() if int(item["probe_id"]) in probe_ids}
    else:
        return dict[int, dict[str, Any]]()


def format_data_probes_with_micro_array(structures_with_probe_ids: list[DiffStructure], probes:  dict[int, dict[str, Any]], field_name: str) -> list[str]:
    return_list = list[str]()

    for v in structures_with_probe_ids:
        tmp_str = f"""------------------------------ 
Regions: {v.diff_name}
---------------------------------
"""

        for i, diff in v.unique_region_data.items():
            tmp_str += f"{len(diff)} unique genes for {i}: " + \
                str([probes[item][field_name] for item in diff])
            tmp_str += "\n"

        tmp_str += f"{len(v.shared_region_data)} shared genes: " + \
            str([str(probes[item][field_name] + " : " + str(item))
                for item in v.shared_region_data])

        return_list.append(tmp_str)

    return return_list

# endregion

# region diffrence


def get_diffrence_between_structure_probes(structures_with_probes: dict[str, list[int]]) -> list[DiffStructure]:
    combinations_list = list(combinations(structures_with_probes.keys(), 2))

    return_list = [DiffStructure(item[0], set(structures_with_probes[item[0]]), item[1], set(
        structures_with_probes[item[1]])) for item in combinations_list]

    return return_list


# endregion


def main():
    start = time.time()
    
    # get the arguments
    arguments = get_arguments()

    # pre define variables
    microarray_expression_file_path = arguments["microarrayexpression"]
    probes_file_path = arguments["probes"]
    sample_annot_file_path = arguments["sampleannot"]
    regions = str(arguments["regions"]).upper().split(",")
    cutoff = arguments["cutoff"]
    field_name = arguments["field_name"]

    # reading files
    microarray_expressions = read_microarray_expression(
        microarray_expression_file_path)

    # reading files
    sample_annot = read_sample_annot(
        sample_annot_file_path, regions)

    structures_with_probe_ids = process_microarray_with_sample_annot(
        microarray_expressions, cutoff, sample_annot)

    # reading files
    probes = read_probes(probes_file_path, structures_with_probe_ids)

    diffs_by_structures = get_diffrence_between_structure_probes(
        structures_with_probe_ids)

    data_strings = format_data_probes_with_micro_array(
        diffs_by_structures, probes, field_name)

    for i in data_strings:
        print(i)
        
    end = time.time()
 
    # print the difference between start
    # and end time in milli. secs
    print("The time of execution of above program is :",
      (end-start) * 10**3, "ms")


if __name__ == "__main__":

    main()
