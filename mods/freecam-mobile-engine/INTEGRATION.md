# Freecam Mobile — integration status

Target: Horizon Android / Minecraft 26.3 / ARM64.

This folder contains a standalone Rust movement/state controller. It is not yet a loadable .hnmod or APK.

The uploaded FreecamMobile.hmod calls Player.setFreecamEnabled(), Player.setFreecamSpeed() and UI.createButton(). These are not part of the documented Android native-mod ABI. The Android ABI provides key/tick/HUD callbacks and player State, but does not expose an arbitrary camera-position override. A real freecam therefore requires engine-side integration.

## Required engine integration

1. Declare this module in crates/horizon-client/src/game.rs and add a Freecam field to Game.
2. Seed it from the interpolated player eye position, yaw and pitch when activated.
3. Route the Android touch look/movement pads and a toggle button into FreecamInput.
4. In the renderer camera-view calculation, use Freecam position/yaw/pitch while enabled. Never write this position into the player entity or send it to the server.
5. Restore the normal player camera on toggle-off, pause, touch cancellation, disconnect, world unload and app background.
6. Add speed controls and test on a real ARM64 device.

## Tests included

- Disabled camera does not move.
- Forward input moves the camera state.
- Diagonal movement is normalized.
- Speed is clamped.

These tests do not prove engine integration or APK compatibility. Build and device validation remain outstanding.
