# LunaTranslator screenshot algorithm attribution

Blue Star OCR's Windows game capture compatibility path in
\`game_reader/luna_capture.py\` follows the GDI screenshot algorithm of
**LunaTranslator v12.1.3.9**, by **HIllya51 and contributors**.

Original source:
https://github.com/HIllya51/LunaTranslator/blob/v12.1.3.9/src/NativeImpl/NativeUtils/screenshot.cpp

Original license: **GNU General Public License version 3 (GPL-3.0)**.
https://github.com/HIllya51/LunaTranslator/blob/v12.1.3.9/LICENSE

The derived Win32 GDI screenshot implementation is distributed under
GPL-3.0-or-later, with full source kept in this public repository. It performs
the same essential GetDC / BitBlt / screen-to-client / failure-fallback sequence
without modifying the author's original LunaSubprocess64.exe.

The Windows portable release also bundles the exact author source archive
\`UPSTREAM_LUNA_GPL_SOURCE_v12.1.3.9.zip\`, and includes current application
source in a separate source archive.

No user's private \`config..json\`, voice credentials, or Windows text capture
is included in a public release.

Compatibility note: GDI and desktop fallback behavior is implemented, but
capture in a specific 3D game or rendering API requires actual gameplay testing.
