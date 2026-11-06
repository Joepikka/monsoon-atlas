# Owner setup: H05 and H06

Use regular Chrome. Google rejected sign-in from the automation-controlled test
browser; account setup is reserved to you by AGENTS.md and amendments A5.
Neither login nor token creation approves public deployment. Keep free plans
without a card. There is no domain purchase or transfer step.

1. Open [Cloudflare API tokens](https://dash.cloudflare.com/profile/api-tokens).
   Create a custom token for this account only. Its account permissions are
   **Workers Scripts: Edit**, **D1: Edit**, **Cloudflare Pages: Edit**, and
   **Account Settings: Read**. Do not grant billing, account-settings edit or
   all-account access. The [official permission catalogue](https://developers.cloudflare.com/fundamentals/api/reference/permissions/)
   lists these permissions; some token interfaces use Write for Edit.
2. Open `D:\monsoon-atlas\.env` in your own editor. Keep its existing data.gov.in
   entry. Add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` using the names in
   `.env.example`. Save the actual token here, not in chat. The file is ignored
   by Git. Account ID is available from your Cloudflare account dashboard.
3. H06 can wait until the archive repository is defined. In [Hugging Face token
   settings](https://huggingface.co/settings/tokens), use a fine-grained write
   token restricted to that repository and save it as `HF_TOKEN` in `.env`.
   [HF's official guidance](https://huggingface.co/docs/hub/security-tokens)
   describes read/write and fine-grained token scopes.
4. Tell the agent only that the values are saved and confirm free/no-card account
   status. The next implementation step can perform a read-only capability
   check; token values must not be printed. A real DB binding, a separate random
   `ATLAS_INGEST_HMAC_KEY`, any service probe that creates a remote resource and
   H11 public-release approval remain separate steps.

These steps do not deploy, create a paid subscription or enable Workers AI.
