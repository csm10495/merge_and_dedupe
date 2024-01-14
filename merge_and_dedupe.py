"""
This script attempts to merge and de-duplicate calls and sms from the SMS Backup & Restore app's xml files.

Dedup is tough. We can have multiple records that seem the same except have different contact names or display dates.
I'm not sure how the display dates got weird, but the date field is the one that matters.

MIT License - 2024 - Charles Machalow
"""
from xml.etree import ElementTree as ET
from pathlib import Path
from collections import defaultdict
from enum import Enum
from time import time
from datetime import datetime

from uuid import uuid4

import argparse

UNKNOWN_CONTACT = "(Unknown)"
READABLE_DATE = "readable_date"
CONTACT_NAME = "contact_name"
ADDRESS = "address"

# When comparing items, we don't care about these fields
FIELDS_TO_IGNORE = (
    READABLE_DATE,
    CONTACT_NAME,
)

# calls use number, sms use address
POSSIBLE_ADDRESS_KEYS = ("number", "address")


class BackupType(Enum):
    """
    Enum for call or sms backup type
    """

    Calls = "Calls"
    SMS = "SMS"

    def get_root_xml_tag(self) -> str:
        """
        Get the root xml tag for this backup type
        """
        if self == BackupType.Calls:
            return "calls"
        else:
            return "smses"


class BackupRestoreItems:
    """
    Class to keep track of items we've seen. This is used to de-duplicate items.
    """

    def __init__(self):
        """
        Initializer for the class. Sets up the internal data structures.
        """
        self._item_dict: dict[str, ET.Element] = dict()
        self._number_to_contact_name: dict[str, str] = defaultdict(
            lambda: UNKNOWN_CONTACT
        )

    @classmethod
    def get_slug(cls, item: ET.Element) -> str:
        """
        Get a slug for the item. This is a string representation of the item's attributes, minus the ones we don't care about.
        """
        attrib = dict(item.attrib)
        for i in FIELDS_TO_IGNORE:
            attrib.pop(i)
        return str(attrib)

    @classmethod
    def get_address_key(self, item: ET.Element) -> str:
        """
        Figure out which key is the address key. It's either 'number' or 'address'.
        """
        for i in POSSIBLE_ADDRESS_KEYS:
            if i in item.attrib:
                return i
        raise KeyError("No address key found")

    def add(self, new_item: ET.Element) -> None:
        """
        Add a new item to the list. If it's already there, do nothing.

        Internally keeps track of a mapping from contact name -> number.
        """
        slug = self.get_slug(new_item)
        if slug not in self._item_dict:
            # add item
            self._item_dict[slug] = new_item

            # add contact name
            address_key = self.get_address_key(new_item)
            if new_item.attrib[address_key] != UNKNOWN_CONTACT:
                self._number_to_contact_name[
                    new_item.attrib[address_key]
                ] = new_item.attrib[CONTACT_NAME]
                self._number_to_contact_name[
                    new_item.attrib[address_key].lstrip("+")
                ] = new_item.attrib[CONTACT_NAME]
                self._number_to_contact_name[
                    new_item.attrib[address_key].lstrip("1")
                ] = new_item.attrib[CONTACT_NAME]

    def _fix_contact_names(self) -> None:
        """
        Do one final attempt to fix contact names. If we see an unknown, check if we have it defined in the number_to_contact_name dict.
        """
        for item in self._item_dict.values():
            if item.attrib["contact_name"] == UNKNOWN_CONTACT:
                item.attrib["contact_name"] = self._number_to_contact_name[
                    item.attrib[self.get_address_key(item)]
                ]

    def get_list(self) -> list[ET.Element]:
        """
        Return a list of items sorted by date (oldest first)
        """
        self._fix_contact_names()
        return list(sorted(self._item_dict.values(), key=lambda x: x.attrib["date"]))


def get_ordered_list_of_items(typ: BackupType, input_dir: Path) -> list[ET.Element]:
    """
    Gets the items corresponding with the given BackupType
    from the input_dir and returns a list of them, sorted by date (oldest first)
    """
    item_list = BackupRestoreItems()
    for file in input_dir.glob(f"{typ.name.lower()}-*.xml"):
        tree = ET.parse(file)
        root = tree.getroot()
        for child in root:
            item_list.add(child)

    return item_list.get_list()


def render_from_list(
    typ: BackupType, items: list[ET.Element], output_dir: Path, backup_set: str
) -> None:
    """
    Render the given list of items to the given output_dir
    """
    root = ET.Element(typ.get_root_xml_tag())

    # format matching the app's behavior with these fields
    root.attrib["backup_set"] = backup_set
    root.attrib["backup_date"] = str(int(time() * 1000))
    root.attrib["type"] = "incremental"
    root.attrib["count"] = str(len(items))

    for item in items:
        root.append(item)

    tree = ET.ElementTree(root)

    # pretty-ifies the output
    ET.indent(tree)

    # match default app file-name format
    tree.write(
        output_dir / datetime.now().strftime(f"{typ.name.lower()}-%Y%m%d%H%M%S.xml"),
        encoding="utf-8",
        xml_declaration=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge and de-duplicate calls and sms from the SMS Backup & Restore app's xml files."
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=Path,
        required=True,
        help="Directory path containing call-*.xml and sms-*.xml file to work with",
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path, required=True, help="Output directory path"
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    backup_set = str(uuid4())
    print("Backup set: " + backup_set)
    all_calls = get_ordered_list_of_items(BackupType.Calls, args.input_dir)
    print(f"Total calls: {len(all_calls)}")
    render_from_list(BackupType.Calls, all_calls, args.output_dir, backup_set)
    print("Finished doing calls.")

    all_sms = get_ordered_list_of_items(BackupType.SMS, args.input_dir)
    print(f"Total sms: {len(all_sms)}")
    render_from_list(BackupType.SMS, all_sms, args.output_dir, backup_set)
    print("Finished doing sms.")
