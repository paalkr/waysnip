#!/bin/bash
# Set up WaySnip as the PrintScreen handler on GNOME Wayland.
#
# Usage: ./scripts/setup-keybinding.sh [install|uninstall]

set -euo pipefail

WAYSNIP_BIN=$(command -v waysnip 2>/dev/null || echo "")

if [ -z "$WAYSNIP_BIN" ]; then
    # Try the venv
    SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    if [ -x "$SCRIPT_DIR/.venv/bin/waysnip" ]; then
        WAYSNIP_BIN="$SCRIPT_DIR/.venv/bin/waysnip"
    else
        echo "Error: waysnip not found in PATH or .venv/bin/"
        echo "Install with: pip install -e ."
        exit 1
    fi
fi

CUSTOM_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"

install_keybinding() {
    echo "Setting up WaySnip keybindings..."

    # Disable GNOME's default screenshot handlers
    gsettings set org.gnome.shell.keybindings screenshot "[]"
    gsettings set org.gnome.shell.keybindings screenshot-window "[]"
    gsettings set org.gnome.shell.keybindings show-screenshot-ui "[]"

    # Get existing custom keybindings
    existing=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)

    # Add our keybindings (region on Print, fullscreen on Ctrl+Print)
    bindings=()
    for i in 0 1; do
        slot="${CUSTOM_PATH}/waysnip${i}/"
        if echo "$existing" | grep -q "waysnip${i}"; then
            echo "  Slot waysnip${i} already exists, updating..."
        else
            bindings+=("'${slot}'")
        fi
    done

    if [ ${#bindings[@]} -gt 0 ]; then
        # Append to existing list
        if [ "$existing" = "@as []" ]; then
            new_list="[$(IFS=,; echo "${bindings[*]}")]"
        else
            trimmed="${existing%]}"
            new_list="${trimmed}, $(IFS=,; echo "${bindings[*]}")]"
        fi
        gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$new_list"
    fi

    # PrintScreen → region capture
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:${CUSTOM_PATH}/waysnip0/ name 'WaySnip Region'
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:${CUSTOM_PATH}/waysnip0/ command "$WAYSNIP_BIN region"
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:${CUSTOM_PATH}/waysnip0/ binding 'Print'

    # Ctrl+PrintScreen → fullscreen capture
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:${CUSTOM_PATH}/waysnip1/ name 'WaySnip Fullscreen'
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:${CUSTOM_PATH}/waysnip1/ command "$WAYSNIP_BIN fullscreen"
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:${CUSTOM_PATH}/waysnip1/ binding '<Ctrl>Print'

    echo ""
    echo "Done. Keybindings:"
    echo "  Print        → waysnip region"
    echo "  Ctrl+Print   → waysnip fullscreen"
    echo ""
    echo "Using: $WAYSNIP_BIN"
}

uninstall_keybinding() {
    echo "Removing WaySnip keybindings..."

    # Restore GNOME defaults
    gsettings reset org.gnome.shell.keybindings screenshot
    gsettings reset org.gnome.shell.keybindings screenshot-window
    gsettings reset org.gnome.shell.keybindings show-screenshot-ui

    # Remove our custom keybindings from the list
    existing=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
    # Remove waysnip entries
    cleaned=$(echo "$existing" | sed "s|'${CUSTOM_PATH}/waysnip[0-9]/'[, ]*||g" | sed 's/, *]/]/g' | sed 's/\[, */[/g')
    gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$cleaned"

    echo "Done. GNOME default screenshot keys restored."
}

case "${1:-install}" in
    install)
        install_keybinding
        ;;
    uninstall)
        uninstall_keybinding
        ;;
    *)
        echo "Usage: $0 [install|uninstall]"
        exit 1
        ;;
esac
