from utils.cli_utils.keypress import clear, keypress


def reorder_menu(items):
    """
    Interactive CLI menu for reordering a list using arrow keys.
    The selected item moves directly with arrow keys when in move mode.

    Args:
        items: List of items to reorder

    Returns:
        Reordered list of items, or None if ESC was pressed
    """
    selected_index = 0
    moving_mode = False
    working_items = items.copy()

    while True:
        clear()  # Assuming this is your screen clearing function

        # Print header
        print("=== Mod Load Order ===\n")

        # Print items
        for i, item in enumerate(working_items):
            prefix = ">" if i == selected_index else " "
            if moving_mode and i == selected_index:
                print(f"{prefix} [[ {item} ]]")  # Show currently moving item
            else:
                print(f"{prefix} {item}")

        print(
            "\n\n↑/↓: Move cursor/item | Space: Toggle move mode | Enter: Confirm Order| ESC: Cancel\n"
        )

        key = keypress()  # Assuming this is your key input function

        if key == "esc":
            return None
        elif key == "enter":
            return working_items
        elif key == "space":
            moving_mode = not moving_mode  # Toggle moving mode
        elif key == "up" and selected_index > 0:
            if moving_mode:
                # Swap with the item above
                working_items[selected_index], working_items[selected_index - 1] = (
                    working_items[selected_index - 1],
                    working_items[selected_index],
                )
            selected_index -= 1
        elif key == "down" and selected_index < len(working_items) - 1:
            if moving_mode:
                # Swap with the item below
                working_items[selected_index], working_items[selected_index + 1] = (
                    working_items[selected_index + 1],
                    working_items[selected_index],
                )
            selected_index += 1


if __name__ == "__main__":
    # Example usage:
    mods = ["SkyUI", "Unofficial Patch", "Immersive Armors", "ENB Preset"]
    new_order = reorder_menu(mods)
    if new_order:
        print("New mod order:", new_order)
    else:
        print("Operation cancelled")
