

def find_SCPI(config, name, SCPI_dict, default = None):
    command = config.get(name, default)

    processed_command = command
    if isinstance(processed_command, str):
        processed_command = processed_command.lower()

    for key in SCPI_dict:
        if processed_command in SCPI_dict[key]:
            return key

    return default
