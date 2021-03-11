from pathlib import Path
import os

CURRENT_PATH = Path(__file__).parent

def create_config_from_template():
    """
    create personalized configs using Jinja (not yet)
    """
    from shutil import copyfile
    template_config_path = os.path.join(CURRENT_PATH.parent,"config_templates/default_config.j2")
    
    if not os.path.exists("./config.yaml"):
        copyfile(template_config_path, "./config.yaml")


    