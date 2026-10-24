# Executed helper byte archive

The actual coordination-file bytes are archived by SHA256 under the evidence helpers/ directory. Every helper hash recorded in PLAN.json and the six launch receipts was matched to an archived file before sealing.

Source helpers are committed on wip/interior-vis23-20261023 at 94cba06db, c4ff53a40, 015ca6d2d and 601f33bd3. Git normalizes text to LF. The original PowerShell-written coordination file used LF within its here-string and CRLF at the final line; the byte-exact original versions were recovered from the corresponding committed text by replacing its final LF with CRLF. Their SHA256 digests exactly match the already recorded launch hashes. The archive also retains the committed LF and full-CRLF variants, labelled as such in EXECUTED-HELPER-ARCHIVE.json. Only matching recorded digests identify executed versions.

In particular, the original OFF menu checker is retained. Its FALSE receipt is preserved. The separate corrected receipt binds its unchanged log digest and validates the actual source's automated menu branch, exact destination, reset/request/arm and new generation in order, with six negative controls. No guest was rerun for that parser correction.
