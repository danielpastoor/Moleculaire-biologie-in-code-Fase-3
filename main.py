from library.InputArgumentParser import InputArgumentParser

def main():
    input_arg_parser = InputArgumentParser(
        "GenBank script", "This is a script that converts genbank to multi fasta")
    input_arg_parser.add_argument(lambda x: x.set_name(
        "input_file"))

    input_arg_parser.add_argument(lambda x: x.set_name(
        "input_file_test").is_required().set_type(float))

    print(input_arg_parser.parse())
    
if __name__ == "__main__":
    main()