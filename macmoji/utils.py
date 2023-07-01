from macmoji.config import ASSET_FILE_NAME


def asset_file_name(unicode: str, size: int):
    return ASSET_FILE_NAME.format(unicode=unicode, size=size)
