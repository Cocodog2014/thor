# Brokers Account Guard Modal

This modal blocks users from starting a live brokerage session while the banner is still showing a paper trading account. It provides two clear paths:

1. **Select Account** – closes the modal so the user can switch accounts via the banner dropdown.
2. **Go to Setup** – routes the user to `/app/user/brokers` to configure or connect a live brokerage account.

## Flow Overview

1. The top banner exposes a `Start Brokerage Account` button.
2. When the active account in the banner dropdown is tagged as `paper`, clicking that button opens this modal instead of launching a live session.
3. The modal relies on the `BrokersAccountModal` component and its companion CSS file in this folder.
4. Once the user switches to a connected broker account, the button flows through to the normal trading route (`/app/trade`).

## Styling Notes

- `BrokersAccountModal.css` styles the overlay and panel itself.
- The status pill rendered next to the banner account dropdown lives in `components/Banners/GlobalBanner.css` because it is part of the TopRow layout, not the modal. Keeping it there ensures the banner’s spacing/typography stay co-located with their styles.

If future guard states require additional visual cues, update both files accordingly and document the rationale here.

Keep this README updated if the guard logic changes or additional states (e.g., pending approval) are introduced.
