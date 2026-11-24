"""Create a Super-User (SU) account. Run from the project root.

Public sign-up only ever creates Registered Customers, so this script is the
supported way to make an SU: it registers the account, then sets its role.
"""
from getpass import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gui import auth
from gui.store import Store


def create_su(store: Store, name: str, email: str, password: str) -> None:
    """Register ``email`` and promote it to SU. Refuses if the email exists."""
    auth.register(store, name, email, password)  # raises AuthError if taken
    store.set_role(email, "SU")


def main():
    store = Store()
    name = input("Name: ").strip()
    email = input("Email: ").strip().lower()
    if store.get_user(email):
        print("An account with that email already exists. Nothing changed.")
        return
    password = getpass("Password: ")
    if getpass("Confirm password: ") != password:
        print("Passwords do not match. Nothing saved.")
        return
    try:
        create_su(store, name, email, password)
    except auth.AuthError as error:
        print(error)
        return
    print(f"Super-User account created for {email}.")


if __name__ == "__main__":
    main()
