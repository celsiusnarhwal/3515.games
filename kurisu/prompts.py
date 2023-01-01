########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from functools import wraps

from InquirerPy import inquirer


def prompt_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs.get("multiselect"):
            keybindings = {
                "toggle": [{"key": "c-z"}],
                "toggle-all-true": [{"key": "c-a"}],
                "toggle-all-false": [{"key": "c-a"}],
            }
        else:
            keybindings = {
                "answer": [{"key": "enter"}, {"key": "c-z"}],
            }

        overrides = {
            "keybindings": keybindings,
            "qmark": "•",
            "amark": "✓",
            "mandatory_message": "You can't skip this.",
            "raise_keyboard_interrupt": True,
        }

        kwargs.get("qmark")

        for key, value in overrides.items():
            kwargs[key] = kwargs.get(key) or value

        return func(*args, **kwargs)

    return wrapper


checkbox = prompt_decorator(inquirer.checkbox)
confirm = prompt_decorator(inquirer.confirm)
expand = prompt_decorator(inquirer.expand)
filepath = prompt_decorator(inquirer.filepath)
fuzzy = prompt_decorator(inquirer.fuzzy)
text = prompt_decorator(inquirer.text)
select = prompt_decorator(inquirer.select)
number = prompt_decorator(inquirer.number)
rawlist = prompt_decorator(inquirer.rawlist)
secret = prompt_decorator(inquirer.secret)
