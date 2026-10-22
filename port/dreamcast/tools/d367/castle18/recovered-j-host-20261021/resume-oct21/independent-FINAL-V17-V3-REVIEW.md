# Final V17 / watcher-v3 review

No further concrete launch blocker was identified in the inspected controller and supervisor revisions. The previous synchronous-filesystem deadline blocker is resolved: the resource sampler runs on a daemon thread, while the owned process deadline loop consumes the latest snapshot and fails closed if sampling errors or becomes one second stale. Exact PID/path/creation-time verification, exception cleanup, verified exit and runner return-status checks remain present.

Reviewed actual bytes:

- Controller v17: `9e1f3ed9d2f93d3c1f4a5d389a1572d93ad3bf5e6a0261f0b3f8c201ce43511b`.
- Watcher v3: `e87881248adf5796bf361f401a62325853d976fab11c684c6e32271b456c9694`.
- Runner v3: `f841df5bf9d16d686d569826b3d0901d948907bfbb68afd631a10be147927300`.

The runner isolated test records its normalized-LF text SHA `ab0f6f12e8a8e42054a34e03a865a5ac9a38d63b6f4588e17cb40b86fc2477cb`. This matches the current runner text after Python read_text newline normalization; the raw-byte hash differs because of file line endings. Both identities are in `final-v17-v3-reviewed-identities.json`.

The six existing mocked supervisor cases use synthetic handles/PID 0 and cover disk-query failure, missing SDL window, failed WM_CLOSE, ordinary close, absolute stop and a three-second resource-sampler stall starting at process age 44.9. Their recorded termination ages are approximately 5.02, 46.03, 46.03, 47.21 and 45.92 seconds for the cases requiring termination; the ordinary-close case records no termination. All synthetic process states end not alive, the owned handle closes, and recorded termination ages are below 47.5. The timed receipt's watcher hash matches the inspected raw bytes.

The existing extracted-controller test demonstrates tracked left/ready key releases at synthetic age 40.6, active-state clearing, TimeoutError and continued identity-check usability for cleanup. Its controller hash matches. The isolated real runner-finally test waits for supervision with timeout 85 and propagates a nonzero guard status after the synthetic verified-exit receipt; it does not kill the watcher. Its normalized source hash matches the inspected runner text.

This lane read the source/test code and receipts, parsed Python syntax and cross-checked identities. It did not rerun those tests, start a guest, send inputs, terminate any process, change controllers/source, build or stage anything. These are source and mocked-host qualifications. The authorized next bounded Flycast unit still needs its exact starting state, current resource admission, actual guard receipt, closed state and screenshots before any gameplay or timing claim. No full release or physical Dreamcast acceptance is established. Castle21 retains runtime ownership and Claude retains production merge/release ownership.
