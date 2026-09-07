import needle

@needle.tool
def get_folder_dir_by_name(name: str):
    """Get the directory path of a folder by its name.

    Args:
        name: The folder name to look up. Supported values: 'ddi', 'desktop'
    """
    if name == "ddi":
        return {"dir": "~/Dawnloads/ddi"}
    return {"dir": "~/desktop/"}


@needle.tool
def move_to_dir(dir: str):
    """Move to a directory by its directory path.

    Args:
        dir: The directory path to move to.
    """
    if dir == "~/Dawnloads/ddi":
        return {"TRUE"}
    return {"FALSE"}

agent = needle.Needle(tools=[get_folder_dir_by_name, move_to_dir])
print(agent.run("let me move to my ddi project")["results"])
# [{'dir': '~/Dawnloads/ddi'}]
