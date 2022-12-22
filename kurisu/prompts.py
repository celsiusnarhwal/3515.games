from InquirerPy import inquirer


def prompt_decorator(func):
    def wrapper(*args, **kwargs):
        if kwargs.get("multiselect"):
            keybindings = {
                "toggle": [
                    {"key": "c-z"}
                ],
                "toggle-all-true": [
                    {"key": "c-a"}
                ],
                "toggle-all-false": [
                    {"key": "c-a"}
                ],
            }
        else:
            keybindings = {
                "answer": [
                    {"key": "enter"},
                    {"key": "c-z"}
                ],
            }

        kwargs["keybindings"] = keybindings
        kwargs["qmark"] = "•"
        kwargs["amark"] = "✓"
        kwargs["mandatory_message"] = "You can't skip this."
        kwargs["raise_keyboard_interrupt"] = True

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
