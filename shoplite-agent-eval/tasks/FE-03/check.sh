#!/usr/bin/env bash
# FE-03 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test fe03-role a11y_i18n frontend 'FE03 exposes a modal dialog' "role=dialog, accessible name, aria-modal"
check_test fe03-focus-in a11y_i18n frontend 'FE03 moves focus into the dialog' "Focus moves into the dialog"
check_test fe03-trap a11y_i18n frontend 'FE03 keeps Tab and Shift' "Tab/Shift+Tab trapped"
check_test fe03-escape functional frontend 'FE03 closes on Escape' "Escape closes without ordering, focus restored"
check_test fe03-cancel functional frontend 'FE03 returns focus to Checkout after Cancel' "Cancel restores focus"
check_test fe03-axe a11y_i18n frontend 'FE03 has no detectable accessibility violation' "jest-axe clean with dialog open"
check_test fe03-fr a11y_i18n frontend 'FE03 French dialog name' "French dialog name"
check fe03-contract-untouched contract "contracts/openapi.yaml unchanged" -- file_unchanged contracts/openapi.yaml
check fe03-no-new-dependency code_quality "No dependency added (plan)" -- paths_unchanged frontend/package.json frontend/package-lock.json
check fe03-props-kept code_quality "Component API kept (CartPage untouched or only trivially changed)" -- diff_within 300
check fe03-tests-added tests_quality "Keyboard/a11y tests added" -- pattern_count_grew 'keyboard|tab\(|Escape|toHaveFocus' frontend/tests

finish
