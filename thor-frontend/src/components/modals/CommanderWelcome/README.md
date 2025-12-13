# Commander Welcome Modal

A cinematic onboarding modal that introduces users to Thor's “war room” the first time they land on `/app/home` each session.

## Flow

1. `Home.tsx` loads and checks `sessionStorage[HOME_WELCOME_DISMISSED_KEY]`.
2. If the preference is missing or `false`, the modal mounts with `open=true`.
3. The modal cycles through three scenes with animated callouts.
4. The user clicks **Engage**, triggering the final scene before auto-dismiss.
5. `onDismiss` sets the storage flag so reloading the page keeps the modal hidden for the rest of the session.

## Files

- `CommanderWelcomeModal.tsx` — React portal-based component with timed scene logic.
- `CommanderWelcomeModal.css` — Visual treatment, animations, overlays.

Update this README if the onboarding logic or storage key changes.
